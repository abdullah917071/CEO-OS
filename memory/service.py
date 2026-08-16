from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from memory.embedding import EmbeddingProvider, cosine_similarity
from memory.models import MemoryBase, MemoryProvenanceRecord, MemoryRecord


@dataclass(frozen=True, slots=True)
class Provenance:
    source_type: str
    source_uri: str | None = None
    source_task_id: str | None = None
    detail: str | None = None
    observed_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class MemoryView:
    id: str
    memory_type: str
    content: str
    subject_key: str | None
    status: str
    confidence: float
    importance: float
    sensitivity: str
    observed_at: datetime
    valid_from: datetime
    valid_until: datetime | None
    supersedes_id: str | None
    attributes: dict[str, Any]
    access_count: int
    provenance: list[Provenance]
    score: float | None = None

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        for field_name in ("observed_at", "valid_from", "valid_until"):
            field_value = value[field_name]
            value[field_name] = field_value.isoformat() if field_value is not None else None
        for source in value["provenance"]:
            observed_at = source["observed_at"]
            source["observed_at"] = observed_at.isoformat() if observed_at is not None else None
        return value


class MemoryService:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        dialect_name: str,
        embedder: EmbeddingProvider,
    ) -> None:
        self.sessions = sessions
        self.dialect_name = dialect_name
        self.embedder = embedder

    async def create(
        self,
        *,
        memory_type: str,
        content: str,
        provenance: Provenance,
        subject_key: str | None = None,
        confidence: float = 1.0,
        importance: float = 0.5,
        sensitivity: str = "normal",
        observed_at: datetime | None = None,
        valid_from: datetime | None = None,
        valid_until: datetime | None = None,
        attributes: dict[str, Any] | None = None,
        dedupe_key: str | None = None,
        supersedes_id: str | None = None,
    ) -> MemoryView:
        if memory_type not in {"semantic", "episodic"}:
            raise ValueError("memory_type must be semantic or episodic")
        if not content.strip():
            raise ValueError("memory content cannot be empty")
        if not 0 <= confidence <= 1 or not 0 <= importance <= 1:
            raise ValueError("confidence and importance must be between 0 and 1")
        now = datetime.now(UTC)
        record = MemoryRecord(
            id=str(uuid4()),
            memory_type=memory_type,
            content=content.strip(),
            subject_key=subject_key,
            status="active",
            confidence=confidence,
            importance=importance,
            sensitivity=sensitivity,
            observed_at=observed_at or now,
            valid_from=valid_from or now,
            valid_until=valid_until,
            supersedes_id=supersedes_id,
            embedding=await self.embedder.embed(content),
            embedding_provider=self.embedder.name,
            attributes=attributes or {},
            dedupe_key=dedupe_key,
            access_count=0,
            created_at=now,
            updated_at=now,
        )
        async with self.sessions() as session:
            if dedupe_key:
                existing = await session.scalar(
                    select(MemoryRecord).where(MemoryRecord.dedupe_key == dedupe_key)
                )
                if existing is not None:
                    return await self._view(session, existing)
            session.add(record)
            session.add(self._provenance_record(record.id, provenance, now))
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
                if dedupe_key:
                    existing = await session.scalar(
                        select(MemoryRecord).where(MemoryRecord.dedupe_key == dedupe_key)
                    )
                    if existing is not None:
                        return await self._view(session, existing)
                raise
            return await self._view(session, record)

    async def get(self, memory_id: UUID | str) -> MemoryView | None:
        async with self.sessions() as session:
            record = await session.get(MemoryRecord, str(memory_id))
            return await self._view(session, record) if record is not None else None

    async def recent(self, limit: int = 20) -> list[MemoryView]:
        if limit < 1 or limit > 50:
            raise ValueError("limit must be between 1 and 50")
        now = datetime.now(UTC)
        async with self.sessions() as session:
            records = list(
                (
                    await session.scalars(
                        select(MemoryRecord)
                        .where(
                            MemoryRecord.status == "active",
                            MemoryRecord.valid_from <= now,
                            or_(MemoryRecord.valid_until.is_(None), MemoryRecord.valid_until > now),
                        )
                        .order_by(MemoryRecord.updated_at.desc())
                        .limit(limit)
                    )
                ).all()
            )
            return [await self._view(session, record) for record in records]

    async def search(
        self, query: str, *, memory_type: str | None = None, limit: int = 5
    ) -> list[MemoryView]:
        if not query.strip():
            raise ValueError("query cannot be empty")
        if limit < 1 or limit > 50:
            raise ValueError("limit must be between 1 and 50")
        vector = await self.embedder.embed(query)
        now = datetime.now(UTC)
        filters = [
            MemoryRecord.status == "active",
            MemoryRecord.valid_from <= now,
            or_(MemoryRecord.valid_until.is_(None), MemoryRecord.valid_until > now),
        ]
        if memory_type:
            filters.append(MemoryRecord.memory_type == memory_type)
        async with self.sessions() as session:
            if self.dialect_name == "postgresql":
                distance = MemoryRecord.embedding.cosine_distance(vector).label("distance")
                rows = (
                    await session.execute(
                        select(MemoryRecord, distance)
                        .where(*filters)
                        .order_by(distance)
                        .limit(max(limit * 4, 20))
                    )
                ).all()
                candidates = [
                    (record, max(0.0, 1.0 - float(distance_value)))
                    for record, distance_value in rows
                ]
            else:
                records = list((await session.scalars(select(MemoryRecord).where(*filters))).all())
                candidates = [
                    (
                        record,
                        max(0.0, cosine_similarity(vector, record.embedding)),
                    )
                    for record in records
                ]
            scored = sorted(
                ((record, self._score(record, semantic, now)) for record, semantic in candidates),
                key=lambda item: item[1],
                reverse=True,
            )[:limit]
            views: list[MemoryView] = []
            for record, score in scored:
                record.access_count += 1
                record.last_accessed_at = now
                views.append(await self._view(session, record, score))
            await session.commit()
            return views

    async def correct(
        self,
        memory_id: UUID | str,
        *,
        content: str,
        provenance: Provenance,
        confidence: float | None = None,
    ) -> MemoryView:
        if not content.strip():
            raise ValueError("memory content cannot be empty")
        if confidence is not None and not 0 <= confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        now = datetime.now(UTC)
        async with self.sessions() as session:
            old = await session.get(MemoryRecord, str(memory_id), with_for_update=True)
            if old is None:
                raise KeyError(str(memory_id))
            if old.status != "active":
                raise ValueError("only active memories can be corrected")
            old.status, old.valid_until, old.updated_at = "superseded", now, now
            replacement = MemoryRecord(
                id=str(uuid4()),
                memory_type=old.memory_type,
                content=content.strip(),
                subject_key=old.subject_key,
                status="active",
                confidence=confidence if confidence is not None else old.confidence,
                importance=old.importance,
                sensitivity=old.sensitivity,
                observed_at=now,
                valid_from=now,
                valid_until=None,
                supersedes_id=old.id,
                embedding=await self.embedder.embed(content),
                embedding_provider=self.embedder.name,
                attributes=old.attributes,
                dedupe_key=None,
                access_count=0,
                created_at=now,
                updated_at=now,
            )
            session.add(replacement)
            session.add(self._provenance_record(replacement.id, provenance, now))
            await session.commit()
            return await self._view(session, replacement)

    async def delete(self, memory_id: UUID | str) -> MemoryView:
        now = datetime.now(UTC)
        async with self.sessions() as session:
            record = await session.get(MemoryRecord, str(memory_id), with_for_update=True)
            if record is None:
                raise KeyError(str(memory_id))
            record.status, record.valid_until, record.updated_at = "deleted", now, now
            await session.commit()
            return await self._view(session, record)

    async def record_task_episode(
        self, task_id: UUID, objective: str, result: dict[str, Any]
    ) -> None:
        evidence = result.get("evidence", [])
        await self.create(
            memory_type="episodic",
            content=f"Completed task: {objective}",
            importance=0.5,
            confidence=1.0,
            provenance=Provenance(
                source_type="task",
                source_task_id=str(task_id),
                detail="; ".join(str(item) for item in evidence) or "Task completed",
            ),
            attributes={"result": result},
            dedupe_key=f"task:{task_id}:success",
        )

    async def _view(
        self, session: AsyncSession, record: MemoryRecord, score: float | None = None
    ) -> MemoryView:
        sources = list(
            (
                await session.scalars(
                    select(MemoryProvenanceRecord).where(
                        MemoryProvenanceRecord.memory_id == record.id
                    )
                )
            ).all()
        )
        return MemoryView(
            id=record.id,
            memory_type=record.memory_type,
            content=record.content,
            subject_key=record.subject_key,
            status=record.status,
            confidence=record.confidence,
            importance=record.importance,
            sensitivity=record.sensitivity,
            observed_at=record.observed_at,
            valid_from=record.valid_from,
            valid_until=record.valid_until,
            supersedes_id=record.supersedes_id,
            attributes=record.attributes,
            access_count=record.access_count,
            provenance=[
                Provenance(
                    source_type=item.source_type,
                    source_uri=item.source_uri,
                    source_task_id=item.source_task_id,
                    detail=item.detail,
                    observed_at=item.observed_at,
                )
                for item in sources
            ],
            score=score,
        )

    @staticmethod
    def _provenance_record(
        memory_id: str, source: Provenance, now: datetime
    ) -> MemoryProvenanceRecord:
        return MemoryProvenanceRecord(
            id=str(uuid4()),
            memory_id=memory_id,
            source_type=source.source_type,
            source_uri=source.source_uri,
            source_task_id=source.source_task_id,
            detail=source.detail,
            observed_at=source.observed_at or now,
            created_at=now,
        )

    @staticmethod
    def _score(record: MemoryRecord, semantic: float, now: datetime) -> float:
        observed = record.observed_at
        if observed.tzinfo is None:
            observed = observed.replace(tzinfo=UTC)
        age_days = max(0.0, (now - observed).total_seconds() / 86400)
        recency = math.exp(-age_days / 180)
        return semantic * 0.8 + record.importance * 0.15 + recency * 0.05


async def initialize_memory_schema(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        if connection.dialect.name == "postgresql":
            await connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await connection.run_sync(MemoryBase.metadata.create_all)
