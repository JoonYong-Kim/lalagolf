import logging

from fastapi.testclient import TestClient

from app.core.config import get_settings
from tests.test_uploads_api import register


def test_request_id_header_is_preserved(client: TestClient) -> None:
    response = client.get("/api/v1/health", headers={"X-Request-ID": "req-test-123"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "req-test-123"


def test_ollama_enabled_path_logs_deterministic_fallback(
    client: TestClient,
    caplog,
) -> None:
    settings = get_settings()
    previous_enabled = settings.ollama_enabled
    settings.ollama_enabled = True

    try:
        register(client)
        thread_response = client.post("/api/v1/chat/threads", json={"title": "Ops"})
        assert thread_response.status_code == 201
        thread_id = thread_response.json()["data"]["id"]

        caplog.set_level(logging.WARNING, logger="lalagolf.api.chat")
        response = client.post(
            f"/api/v1/chat/threads/{thread_id}/messages",
            json={"content": "최근 10라운드 평균 스코어는?"},
        )
    finally:
        settings.ollama_enabled = previous_enabled

    assert response.status_code == 201
    evidence = response.json()["data"]["assistant_message"]["evidence"]
    assert evidence["ollama"]["timeout_seconds"] == settings.ollama_timeout_seconds
    assert any("ollama wording skipped" in record.message for record in caplog.records)
