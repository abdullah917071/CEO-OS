from uuid import uuid4

import pytest

from apps.api.src.ceo_os_api.events import EventHub
from core.contracts import RuntimeEvent


@pytest.mark.asyncio
async def test_event_history_is_bounded_and_newest_first() -> None:
    hub = EventHub(history_limit=2)
    for index in range(3):
        await hub.publish(RuntimeEvent(f"task.event.{index}", uuid4(), {"index": index}))

    recent = await hub.recent(10)
    assert [item["event_type"] for item in recent] == ["task.event.2", "task.event.1"]
    assert all(isinstance(item["task_id"], str) for item in recent)


@pytest.mark.asyncio
async def test_event_history_rejects_invalid_bounds() -> None:
    with pytest.raises(ValueError, match="positive"):
        EventHub(history_limit=0)
    with pytest.raises(ValueError, match="positive"):
        await EventHub().recent(0)
