from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from apps.api.src.ceo_os_api.database import Base, TaskRepository
from apps.api.src.ceo_os_api.events import EventHub
from apps.api.src.ceo_os_api.planner import DeterministicProvider
from apps.api.src.ceo_os_api.runtime import CeoRuntime
from core.capabilities import CapabilityRegistry
from core.contracts import TaskStatus
from core.model_router import ModelRouter
from memory.embedding import EMBEDDING_DIMENSIONS, FeatureHashEmbeddingProvider
from memory.models import MemoryRecord
from memory.service import MemoryService, Provenance, initialize_memory_schema
from memory.tools import memory_tools


async def memory_fixture(path: Path) -> tuple[MemoryService, object, object]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{path}")
    await initialize_memory_schema(engine)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    service = MemoryService(sessions, "sqlite", FeatureHashEmbeddingProvider())
    return service, sessions, engine


@pytest.mark.asyncio
async def test_embedding_is_stable_normalized_and_has_declared_dimensions() -> None:
    embedder = FeatureHashEmbeddingProvider()
    first = await embedder.embed("Meta campaign budget")
    second = await embedder.embed("Meta campaign budget")
    assert first == second
    assert len(first) == EMBEDDING_DIMENSIONS
    assert math.isclose(math.sqrt(sum(value * value for value in first)), 1.0)


@pytest.mark.asyncio
async def test_semantic_search_ranks_relevant_memory_and_preserves_provenance(
    tmp_path: Path,
) -> None:
    service, sessions, engine = await memory_fixture(tmp_path / "memory.db")
    relevant = await service.create(
        memory_type="semantic",
        content="The owner decided Meta advertising budgets require review above fifteen percent.",
        subject_key="policy:meta-budget",
        provenance=Provenance(source_type="owner_message", source_uri="chat://decision-1"),
        importance=0.9,
    )
    await service.create(
        memory_type="semantic",
        content="The preferred restaurant has outdoor seating.",
        provenance=Provenance(source_type="owner_message"),
    )

    matches = await service.search("What was the Meta budget decision?", limit=2)
    assert matches[0].id == relevant.id
    assert matches[0].provenance[0].source_uri == "chat://decision-1"

    restarted = MemoryService(sessions, "sqlite", FeatureHashEmbeddingProvider())
    persisted = await restarted.get(relevant.id)
    assert persisted is not None and persisted.content == relevant.content
    await engine.dispose()


@pytest.mark.asyncio
async def test_correction_supersedes_instead_of_overwriting(tmp_path: Path) -> None:
    service, _, engine = await memory_fixture(tmp_path / "correction.db")
    original = await service.create(
        memory_type="semantic",
        content="Supplier X is active.",
        subject_key="supplier:x",
        provenance=Provenance(source_type="import", source_uri="crm://supplier-x"),
    )
    corrected = await service.correct(
        original.id,
        content="Supplier X is inactive.",
        provenance=Provenance(source_type="owner_correction", detail="Contract ended"),
    )

    old = await service.get(original.id)
    assert old is not None and old.status == "superseded"
    assert corrected.supersedes_id == original.id
    assert corrected.provenance[0].source_type == "owner_correction"
    matches = await service.search("Supplier X status", limit=10)
    assert corrected.id in {item.id for item in matches}
    assert original.id not in {item.id for item in matches}
    await engine.dispose()


@pytest.mark.asyncio
async def test_deleted_and_expired_memories_are_not_retrieved(tmp_path: Path) -> None:
    service, _, engine = await memory_fixture(tmp_path / "validity.db")
    deleted = await service.create(
        memory_type="semantic",
        content="The temporary office is in Mumbai.",
        provenance=Provenance(source_type="owner_message"),
    )
    await service.delete(deleted.id)
    await service.create(
        memory_type="semantic",
        content="The expired temporary office is in Pune.",
        valid_until=datetime.now(UTC) - timedelta(days=1),
        provenance=Provenance(source_type="owner_message"),
    )
    assert await service.search("temporary office", limit=10) == []
    await engine.dispose()


@pytest.mark.asyncio
async def test_task_episode_is_idempotent(tmp_path: Path) -> None:
    service, sessions, engine = await memory_fixture(tmp_path / "episode.db")
    task_id = UUID("12345678-1234-5678-1234-567812345678")
    await service.record_task_episode(task_id, "Read the clock", {"evidence": ["Clock read"]})
    await service.record_task_episode(task_id, "Read the clock", {"evidence": ["Clock read"]})
    async with sessions() as session:
        count = await session.scalar(select(func.count()).select_from(MemoryRecord))
    assert count == 1
    await engine.dispose()


@pytest.mark.asyncio
async def test_remember_then_recall_survives_runtime_recreation(tmp_path: Path) -> None:
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'runtime-memory.db'}"
    engine = create_async_engine(database_url)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    await initialize_memory_schema(engine)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    service = MemoryService(sessions, "sqlite", FeatureHashEmbeddingProvider())

    def build_runtime() -> CeoRuntime:
        provider = DeterministicProvider()
        return CeoRuntime(
            TaskRepository(sessions),
            CapabilityRegistry(memory_tools(service)),
            ModelRouter({provider.name: provider}, provider.name),
            EventHub(),
            InMemorySaver(),
            service,
        )

    runtime = build_runtime()
    stored, _ = await runtime.create("Remember that Project Atlas launches in November")
    assert (await runtime.execute(UUID(stored.id))).status == TaskStatus.SUCCESS

    restarted = build_runtime()
    recalled, _ = await restarted.create("What do you remember about Project Atlas?")
    result = await restarted.execute(UUID(recalled.id))
    assert result.status == TaskStatus.SUCCESS
    assert result.result is not None
    assert "Project Atlas launches in November" in result.result["message"]
    await engine.dispose()
