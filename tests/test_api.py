from uuid import uuid4

from fastapi.testclient import TestClient

from apps.api.src.ceo_os_api.main import app


def test_liveness() -> None:
    with TestClient(app) as client:
        response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["service"] == "ceo-os-api"


def test_dashboard_read_models_are_bounded_and_truthful() -> None:
    unique = str(uuid4())
    with TestClient(app) as client:
        created = client.post(
            "/api/v1/memories",
            json={
                "memory_type": "semantic",
                "content": f"Dashboard memory {unique}",
                "provenance": {"source_type": "dashboard_api_test"},
            },
        )
        assert created.status_code == 201
        recent = client.get("/api/v1/memories", params={"limit": 1})
        assert recent.status_code == 200
        assert len(recent.json()) == 1
        assert recent.json()[0]["id"] == created.json()["id"]

        activity = client.get("/api/v1/activity", params={"limit": 10})
        assert activity.status_code == 200
        assert isinstance(activity.json(), list)
        assert client.get("/api/v1/activity", params={"limit": 0}).status_code == 422
        assert client.get("/api/v1/memories", params={"limit": 51}).status_code == 422


def test_agent_api_lifecycle_messages_and_parallel_delegation() -> None:
    with TestClient(app) as client:
        agents = client.get("/api/v1/agents")
        assert agents.status_code == 200
        ceo = next(item for item in agents.json() if item["name"] == "CEO")
        director = next(item for item in agents.json() if item["name"] == "Research Director")
        assert director["parent_id"] == ceo["id"]

        created = client.post(
            "/api/v1/agents",
            json={
                "name": "API Researcher",
                "template_name": "researcher",
                "parent_id": director["id"],
                "max_cost_units": 20,
            },
        )
        assert created.status_code == 201
        agent_id = created.json()["id"]
        assert client.post(f"/api/v1/agents/{agent_id}/pause").json()["status"] == "paused"
        assert client.post(f"/api/v1/agents/{agent_id}/resume").json()["status"] == "active"
        clone = client.post(
            f"/api/v1/agents/{agent_id}/clone", json={"name": "API Researcher Clone"}
        )
        assert clone.status_code == 201

        message = client.post(
            "/api/v1/agent-messages",
            json={
                "sender_id": agent_id,
                "recipient_id": director["id"],
                "message_type": "status",
                "payload": {"state": "ready"},
            },
        )
        assert message.status_code == 201
        inbox = client.get(f"/api/v1/agents/{director['id']}/messages")
        assert message.json()["id"] in {item["id"] for item in inbox.json()}

        delegated = client.post(
            "/api/v1/delegations",
            json={
                "objective": "Compare ten fixtures",
                "items": [f"Competitor {index}" for index in range(1, 11)],
                "worker_count": 4,
            },
        )
        assert delegated.status_code == 200
        assert delegated.json()["status"] == "success"
        assert len(delegated.json()["comparisons"]) == 10
        assert delegated.json()["data_classification"] == "simulation"
        assert client.get("/api/v1/agent-assignments").status_code == 200
        assert client.post(f"/api/v1/agents/{agent_id}/terminate").json()["status"] == "terminated"


def test_ceo_delegates_top_ten_competitor_simulation() -> None:
    with TestClient(app) as client:
        submitted = client.post(
            "/api/v1/chat/messages",
            json={
                "message": (
                    "Research the top ten competitors and compare pricing, features and "
                    "advertising."
                ),
                "idempotency_key": f"agent-acceptance-{uuid4()}",
            },
        )
        task_id = submitted.json()["id"]
        for _ in range(200):
            task = client.get(f"/api/v1/tasks/{task_id}").json()
            if task["status"] in {"success", "failed"}:
                break
        assert task["status"] == "success"
        output = task["result"]["outputs"][0]
        assert output["capability"] == "agents.delegate.research"
        assert len(output["output"]["comparisons"]) == 10
        assert output["output"]["data_classification"] == "simulation"
        assert len(task["result"]["evidence"]) == 10


def test_chat_submission_is_idempotent_and_eventually_terminal() -> None:
    key = f"api-test-{uuid4()}"
    with TestClient(app) as client:
        first = client.post(
            "/api/v1/chat/messages",
            json={"message": "What time is it?", "idempotency_key": key},
        )
        second = client.post(
            "/api/v1/chat/messages",
            json={"message": "This must not replace the original", "idempotency_key": key},
        )
        assert first.status_code == 202
        assert second.status_code == 202
        assert first.json()["id"] == second.json()["id"]

        task_id = first.json()["id"]
        for _ in range(100):
            current = client.get(f"/api/v1/tasks/{task_id}")
            if current.json()["status"] in {"success", "failed"}:
                break
        assert current.json()["status"] == "success"
        assert client.post(f"/api/v1/tasks/{task_id}/pause").status_code == 409


def test_memory_api_create_search_correct_and_delete() -> None:
    unique = str(uuid4())
    with TestClient(app) as client:
        created = client.post(
            "/api/v1/memories",
            json={
                "memory_type": "semantic",
                "content": f"Project {unique} launches in December",
                "subject_key": f"project:{unique}",
                "importance": 0.9,
                "provenance": {
                    "source_type": "api_test",
                    "source_uri": f"test://{unique}",
                },
                "idempotency_key": f"memory-api-{unique}",
            },
        )
        assert created.status_code == 201
        memory_id = created.json()["id"]
        assert created.json()["provenance"][0]["source_uri"] == f"test://{unique}"

        search = client.get(
            "/api/v1/memories/search", params={"query": f"Project {unique}", "limit": 10}
        )
        assert search.status_code == 200
        assert memory_id in {item["id"] for item in search.json()}

        corrected = client.post(
            f"/api/v1/memories/{memory_id}/correct",
            json={
                "content": f"Project {unique} launches in January",
                "provenance": {"source_type": "owner_correction"},
            },
        )
        assert corrected.status_code == 200
        replacement_id = corrected.json()["id"]
        assert corrected.json()["supersedes_id"] == memory_id
        assert client.get(f"/api/v1/memories/{memory_id}").json()["status"] == "superseded"

        deleted = client.delete(f"/api/v1/memories/{replacement_id}")
        assert deleted.status_code == 200
        assert deleted.json()["status"] == "deleted"


def test_computer_status_and_owner_stop_resume_are_direct() -> None:
    with TestClient(app) as client:
        status = client.get("/api/v1/computer/status")
        assert status.status_code == 200
        assert "supported" in status.json()
        assert status.json()["policy"]["effects_enabled"] is False

        stopped = client.post("/api/v1/computer/stop")
        assert stopped.status_code == 200
        assert stopped.json()["stopped"] is True
        generation = stopped.json()["generation"]

        resumed = client.post("/api/v1/computer/resume")
        assert resumed.status_code == 200
        assert resumed.json()["stopped"] is False
        assert resumed.json()["generation"] == generation + 1


def test_browser_status_and_owner_stop_resume_are_direct() -> None:
    with TestClient(app) as client:
        status = client.get("/api/v1/browser/status")
        assert status.status_code == 200
        assert status.json()["enabled"] is False
        assert status.json()["available"] is False
        assert status.json()["effects_enabled"] is False

        stopped = client.post("/api/v1/browser/stop")
        assert stopped.status_code == 200
        assert stopped.json()["stopped"] is True
        generation = stopped.json()["generation"]

        resumed = client.post("/api/v1/browser/resume")
        assert resumed.status_code == 200
        assert resumed.json()["stopped"] is False
        assert resumed.json()["generation"] == generation + 1


def test_vision_status_and_owner_stop_resume_are_direct() -> None:
    with TestClient(app) as client:
        status = client.get("/api/v1/vision/status")
        assert status.status_code == 200
        assert status.json()["enabled"] is False
        assert status.json()["available"] is False
        assert status.json()["policy"]["effects_enabled"] is False
        assert status.json()["policy"]["capture_scope"] == "window"

        stopped = client.post("/api/v1/vision/stop")
        assert stopped.status_code == 200
        assert stopped.json()["state"]["stopped"] is True
        generation = stopped.json()["state"]["generation"]

        resumed = client.post("/api/v1/vision/resume")
        assert resumed.status_code == 200
        assert resumed.json()["state"]["stopped"] is False
        assert resumed.json()["state"]["generation"] == generation + 1


def test_voice_status_and_disabled_websocket_are_truthful() -> None:
    with TestClient(app) as client:
        status = client.get("/api/v1/voice/status")
        assert status.status_code == 200
        assert status.json()["enabled"] is False
        assert status.json()["available"] is False
        assert status.json()["retention"] == "none"

        with client.websocket_connect("/ws/voice") as websocket:
            assert websocket.receive_json()["type"] == "voice.unavailable"
