from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import Mapped, mapped_column

from agents.contracts import AgentKind, AgentStatus, AssignmentStatus
from apps.api.src.ceo_os_api.database import Base


class AgentRecord(Base):
    __tablename__ = "agents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(120))
    kind: Mapped[str] = mapped_column(String(20), index=True)
    status: Mapped[str] = mapped_column(String(20), index=True)
    template_name: Mapped[str] = mapped_column(String(80))
    template_version: Mapped[int] = mapped_column(Integer)
    parent_id: Mapped[str | None] = mapped_column(
        ForeignKey("agents.id"), nullable=True, index=True
    )
    allowed_capabilities: Mapped[list[str]] = mapped_column(JSON, default=list)
    data_scope: Mapped[list[str]] = mapped_column(JSON, default=list)
    model_class: Mapped[str] = mapped_column(String(80))
    can_spawn_agents: Mapped[bool] = mapped_column(Boolean, default=False)
    max_runtime_seconds: Mapped[int] = mapped_column(Integer)
    max_cost_units: Mapped[int] = mapped_column(Integer)
    max_concurrency: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    terminated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AgentAssignmentRecord(Base):
    __tablename__ = "agent_assignments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    delegation_id: Mapped[str] = mapped_column(String(36), index=True)
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id"), index=True)
    objective: Mapped[str] = mapped_column(Text)
    items: Mapped[list[str]] = mapped_column(JSON, default=list)
    context: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(20), index=True)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    evidence: Mapped[list[str]] = mapped_column(JSON, default=list)
    confidence: Mapped[float | None] = mapped_column(nullable=True)
    uncertainty: Mapped[list[str]] = mapped_column(JSON, default=list)
    cost_units: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AgentMessageRecord(Base):
    __tablename__ = "agent_messages"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    sender_id: Mapped[str] = mapped_column(ForeignKey("agents.id"), index=True)
    recipient_id: Mapped[str] = mapped_column(ForeignKey("agents.id"), index=True)
    assignment_id: Mapped[str | None] = mapped_column(
        ForeignKey("agent_assignments.id"), nullable=True, index=True
    )
    message_type: Mapped[str] = mapped_column(String(60))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AgentRepository:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self.sessions = sessions

    async def create_agent(self, **values: Any) -> AgentRecord:
        now = datetime.now(UTC)
        record = AgentRecord(id=str(uuid4()), created_at=now, updated_at=now, **values)
        async with self.sessions() as session:
            session.add(record)
            await session.commit()
            await session.refresh(record)
        return record

    async def get_agent(self, agent_id: str) -> AgentRecord | None:
        async with self.sessions() as session:
            return await session.get(AgentRecord, agent_id)

    async def list_agents(self) -> list[AgentRecord]:
        async with self.sessions() as session:
            return list(await session.scalars(select(AgentRecord).order_by(AgentRecord.created_at)))

    async def update_agent(self, agent_id: str, **values: Any) -> AgentRecord:
        async with self.sessions() as session:
            record = await session.get(AgentRecord, agent_id)
            if record is None:
                raise KeyError(agent_id)
            for key, value in values.items():
                setattr(record, key, value)
            record.updated_at = datetime.now(UTC)
            await session.commit()
            await session.refresh(record)
            return record

    async def ensure_permanent(self, name: str, role: str) -> AgentRecord:
        async with self.sessions() as session:
            record = await session.scalar(
                select(AgentRecord).where(
                    AgentRecord.name == name, AgentRecord.kind == AgentKind.PERMANENT
                )
            )
            if record is not None:
                return record
        return await self.create_agent(
            name=name,
            role=role,
            kind=AgentKind.PERMANENT,
            status=AgentStatus.ACTIVE,
            template_name="permanent",
            template_version=1,
            parent_id=None,
            allowed_capabilities=[],
            data_scope=["owner"],
            model_class="strategic",
            can_spawn_agents=True,
            max_runtime_seconds=86_400,
            max_cost_units=10_000,
            max_concurrency=10,
            terminated_at=None,
        )

    async def create_assignment(
        self,
        delegation_id: str,
        agent_id: str,
        objective: str,
        items: list[str],
        context: dict[str, Any],
    ) -> AgentAssignmentRecord:
        record = AgentAssignmentRecord(
            id=str(uuid4()),
            delegation_id=delegation_id,
            agent_id=agent_id,
            objective=objective,
            items=items,
            context=context,
            status=AssignmentStatus.QUEUED,
            result=None,
            evidence=[],
            confidence=None,
            uncertainty=[],
            cost_units=0,
            error=None,
            created_at=datetime.now(UTC),
            started_at=None,
            finished_at=None,
        )
        async with self.sessions() as session:
            session.add(record)
            await session.commit()
            await session.refresh(record)
        return record

    async def update_assignment(self, assignment_id: str, **values: Any) -> AgentAssignmentRecord:
        async with self.sessions() as session:
            record = await session.get(AgentAssignmentRecord, assignment_id)
            if record is None:
                raise KeyError(assignment_id)
            for key, value in values.items():
                setattr(record, key, value)
            await session.commit()
            await session.refresh(record)
            return record

    async def list_assignments(self, limit: int = 100) -> list[AgentAssignmentRecord]:
        async with self.sessions() as session:
            return list(
                await session.scalars(
                    select(AgentAssignmentRecord)
                    .order_by(AgentAssignmentRecord.created_at.desc())
                    .limit(limit)
                )
            )

    async def create_message(
        self,
        sender_id: str,
        recipient_id: str,
        message_type: str,
        payload: dict[str, Any],
        assignment_id: str | None = None,
    ) -> AgentMessageRecord:
        record = AgentMessageRecord(
            id=str(uuid4()),
            sender_id=sender_id,
            recipient_id=recipient_id,
            assignment_id=assignment_id,
            message_type=message_type,
            payload=payload,
            created_at=datetime.now(UTC),
        )
        async with self.sessions() as session:
            session.add(record)
            await session.commit()
            await session.refresh(record)
            return record

    async def inbox(self, recipient_id: str, limit: int = 100) -> list[AgentMessageRecord]:
        async with self.sessions() as session:
            return list(
                await session.scalars(
                    select(AgentMessageRecord)
                    .where(AgentMessageRecord.recipient_id == recipient_id)
                    .order_by(AgentMessageRecord.created_at.desc())
                    .limit(limit)
                )
            )
