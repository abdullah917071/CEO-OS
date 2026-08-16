from __future__ import annotations

import builtins
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    inspect,
    or_,
    select,
    text,
    update,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from core.contracts import StepStatus, TaskControl, TaskStatus, ToolResult


class Base(DeclarativeBase):
    pass


class TaskRecord(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    message: Mapped[str] = mapped_column(Text)
    objective: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), index=True)
    plan: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    control: Mapped[str] = mapped_column(String(16), default=TaskControl.RUN)
    lease_owner: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class TaskStepRecord(Base):
    __tablename__ = "task_steps"
    __table_args__ = (UniqueConstraint("task_id", "step_index"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), index=True)
    step_index: Mapped[int] = mapped_column(Integer)
    capability: Mapped[str] = mapped_column(String(255))
    idempotency_key: Mapped[str] = mapped_column(String(64), unique=True)
    status: Mapped[str] = mapped_column(String(16))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    arguments: Mapped[dict[str, Any]] = mapped_column(JSON)
    output: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSON, nullable=True)
    evidence: Mapped[list[str]] = mapped_column(JSON, default=list)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class TaskRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = session_factory

    async def create(
        self, message: str, idempotency_key: str | None = None
    ) -> tuple[TaskRecord, bool]:
        now = datetime.now(UTC)
        async with self._sessions() as session:
            if idempotency_key:
                existing = await session.scalar(
                    select(TaskRecord).where(TaskRecord.idempotency_key == idempotency_key)
                )
                if existing is not None:
                    return existing, False
            record = TaskRecord(
                id=str(uuid4()),
                message=message,
                objective=message,
                status=TaskStatus.QUEUED,
                plan={},
                idempotency_key=idempotency_key,
                control=TaskControl.RUN,
                created_at=now,
                updated_at=now,
            )
            session.add(record)
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
                if idempotency_key:
                    existing = await session.scalar(
                        select(TaskRecord).where(TaskRecord.idempotency_key == idempotency_key)
                    )
                    if existing is not None:
                        return existing, False
                raise
            await session.refresh(record)
        return record, True

    async def update(self, task_id: UUID, **changes: Any) -> TaskRecord:
        async with self._sessions() as session:
            record = await session.get(TaskRecord, str(task_id))
            if record is None:
                raise KeyError(str(task_id))
            for key, value in changes.items():
                setattr(record, key, value)
            record.updated_at = datetime.now(UTC)
            await session.commit()
            await session.refresh(record)
            return record

    async def get(self, task_id: UUID) -> TaskRecord | None:
        async with self._sessions() as session:
            return await session.get(TaskRecord, str(task_id))

    async def list(self, limit: int = 50) -> list[TaskRecord]:
        async with self._sessions() as session:
            result = await session.scalars(
                select(TaskRecord).order_by(TaskRecord.created_at.desc()).limit(limit)
            )
            return list(result)

    async def set_control(self, task_id: UUID, control: TaskControl) -> TaskRecord:
        return await self.update(task_id, control=control)

    async def acquire_lease(self, task_id: UUID, owner: str, ttl_seconds: int) -> bool:
        now = datetime.now(UTC)
        async with self._sessions() as session:
            result = await session.execute(
                update(TaskRecord)
                .where(TaskRecord.id == str(task_id))
                .where(or_(TaskRecord.lease_owner.is_(None), TaskRecord.lease_expires_at < now))
                .values(lease_owner=owner, lease_expires_at=now + timedelta(seconds=ttl_seconds))
            )
            await session.commit()
            return bool(getattr(result, "rowcount", 0))

    async def renew_lease(self, task_id: UUID, owner: str, ttl_seconds: int) -> bool:
        now = datetime.now(UTC)
        async with self._sessions() as session:
            result = await session.execute(
                update(TaskRecord)
                .where(TaskRecord.id == str(task_id), TaskRecord.lease_owner == owner)
                .values(lease_expires_at=now + timedelta(seconds=ttl_seconds))
            )
            await session.commit()
            return bool(getattr(result, "rowcount", 0))

    async def release_lease(self, task_id: UUID, owner: str) -> None:
        async with self._sessions() as session:
            await session.execute(
                update(TaskRecord)
                .where(TaskRecord.id == str(task_id), TaskRecord.lease_owner == owner)
                .values(lease_owner=None, lease_expires_at=None)
            )
            await session.commit()

    async def recoverable(self) -> builtins.list[TaskRecord]:
        terminal = [
            TaskStatus.SUCCESS,
            TaskStatus.PARTIAL_SUCCESS,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        ]
        now = datetime.now(UTC)
        async with self._sessions() as session:
            rows = await session.scalars(
                select(TaskRecord).where(
                    TaskRecord.status.not_in(terminal),
                    or_(TaskRecord.lease_owner.is_(None), TaskRecord.lease_expires_at < now),
                )
            )
            return list(rows)

    async def begin_step(
        self, task_id: UUID, index: int, capability: str, arguments: dict[str, Any], key: str
    ) -> TaskStepRecord:
        now = datetime.now(UTC)
        async with self._sessions() as session:
            existing = await session.scalar(
                select(TaskStepRecord).where(
                    TaskStepRecord.task_id == str(task_id), TaskStepRecord.step_index == index
                )
            )
            if existing is not None:
                existing.attempts += 1
                existing.status = StepStatus.RUNNING
                existing.updated_at = now
                await session.commit()
                await session.refresh(existing)
                return existing
            record = TaskStepRecord(
                id=str(uuid4()),
                task_id=str(task_id),
                step_index=index,
                capability=capability,
                idempotency_key=key,
                status=StepStatus.RUNNING,
                attempts=1,
                arguments=arguments,
                created_at=now,
                updated_at=now,
            )
            session.add(record)
            await session.commit()
            await session.refresh(record)
            return record

    async def get_step(self, task_id: UUID, index: int) -> TaskStepRecord | None:
        async with self._sessions() as session:
            return cast(
                TaskStepRecord | None,
                await session.scalar(
                    select(TaskStepRecord).where(
                        TaskStepRecord.task_id == str(task_id),
                        TaskStepRecord.step_index == index,
                    )
                ),
            )

    async def complete_step(self, step_id: str, result: ToolResult) -> None:
        async with self._sessions() as session:
            record = await session.get(TaskStepRecord, step_id)
            if record is None:
                raise KeyError(step_id)
            record.status, record.output, record.evidence = (
                StepStatus.SUCCESS,
                result.output,
                result.evidence,
            )
            record.error, record.updated_at = None, datetime.now(UTC)
            await session.commit()

    async def fail_step(self, step_id: str, error: str) -> None:
        async with self._sessions() as session:
            record = await session.get(TaskStepRecord, step_id)
            if record is not None:
                record.status, record.error = StepStatus.FAILED, error
                record.updated_at = datetime.now(UTC)
                await session.commit()


def create_database(url: str) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(url, pool_pre_ping=True)
    return engine, async_sessionmaker(engine, expire_on_commit=False)


async def initialize_schema(engine: AsyncEngine) -> None:
    """Create the current schema and add Phase 2 columns to Phase 1 local databases."""
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        columns = await connection.run_sync(
            lambda sync_connection: {
                item["name"] for item in inspect(sync_connection).get_columns("tasks")
            }
        )
        timestamp_type = (
            "TIMESTAMP WITH TIME ZONE" if connection.dialect.name == "postgresql" else "DATETIME"
        )
        additions = {
            "idempotency_key": "VARCHAR(255)",
            "control": "VARCHAR(16) NOT NULL DEFAULT 'run'",
            "lease_owner": "VARCHAR(64)",
            "lease_expires_at": timestamp_type,
        }
        for name, definition in additions.items():
            if name not in columns:
                await connection.execute(text(f"ALTER TABLE tasks ADD COLUMN {name} {definition}"))
        await connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_tasks_idempotency_key "
                "ON tasks (idempotency_key)"
            )
        )
