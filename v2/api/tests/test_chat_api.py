from fastapi.testclient import TestClient

from app.core.config import get_settings
from tests.test_rounds_api import create_committed_round
from tests.test_uploads_api import register


def test_chat_deterministic_answer_includes_evidence(client: TestClient) -> None:
    register(client)
    create_committed_round(client)

    thread_response = client.post("/api/v1/chat/threads", json={"title": "Round questions"})
    assert thread_response.status_code == 201
    thread_id = thread_response.json()["data"]["id"]

    message_response = client.post(
        f"/api/v1/chat/threads/{thread_id}/messages",
        json={"content": "최근 10라운드 평균 스코어는?"},
    )

    assert message_response.status_code == 201
    data = message_response.json()["data"]
    assistant = data["assistant_message"]
    assert "라운드" in assistant["content"]
    assert assistant["evidence"]["round_count"] == 1
    assert assistant["evidence"]["shot_count"] > 0
    assert assistant["evidence"]["filters"]["window"] == 10

    detail_response = client.get(f"/api/v1/chat/threads/{thread_id}")
    assert detail_response.status_code == 200
    assert len(detail_response.json()["data"]["messages"]) == 2


def test_chat_supports_club_and_category_filters(client: TestClient) -> None:
    register(client)
    create_committed_round(client)
    thread_id = client.post("/api/v1/chat/threads", json={}).json()["data"]["id"]

    club_response = client.post(
        f"/api/v1/chat/threads/{thread_id}/messages",
        json={"content": "드라이버 페널티율 알려줘"},
    )
    assert club_response.status_code == 201
    club_evidence = club_response.json()["data"]["assistant_message"]["evidence"]
    assert club_evidence["intent"] == "penalty"
    assert club_evidence["filters"]["club"] == "D"

    category_response = client.post(
        f"/api/v1/chat/threads/{thread_id}/messages",
        json={"content": "어프로치 카테고리 요약해줘"},
    )
    assert category_response.status_code == 201
    category_evidence = category_response.json()["data"]["assistant_message"]["evidence"]
    assert category_evidence["filters"]["category"] == "approach"


def test_chat_is_owner_scoped(client: TestClient) -> None:
    register(client, "a@example.com")
    create_committed_round(client)
    a_thread_id = client.post("/api/v1/chat/threads", json={}).json()["data"]["id"]
    client.post("/api/v1/auth/logout")

    register(client, "b@example.com")
    b_thread_id = client.post("/api/v1/chat/threads", json={}).json()["data"]["id"]

    denied_response = client.get(f"/api/v1/chat/threads/{a_thread_id}")
    assert denied_response.status_code == 404

    answer_response = client.post(
        f"/api/v1/chat/threads/{b_thread_id}/messages",
        json={"content": "최근 10라운드 평균 스코어는?"},
    )
    assert answer_response.status_code == 201
    evidence = answer_response.json()["data"]["assistant_message"]["evidence"]
    assert evidence["round_count"] == 0
    assert evidence["shot_count"] == 0


def test_chat_ollama_enabled_does_not_break_deterministic_answer(client: TestClient) -> None:
    settings = get_settings()
    original = settings.ollama_enabled
    settings.ollama_enabled = True
    try:
        register(client)
        create_committed_round(client)
        thread_id = client.post("/api/v1/chat/threads", json={}).json()["data"]["id"]
        response = client.post(
            f"/api/v1/chat/threads/{thread_id}/messages",
            json={"content": "최근 라운드 퍼팅은 어땠어?"},
        )
    finally:
        settings.ollama_enabled = original

    assert response.status_code == 201
    assistant = response.json()["data"]["assistant_message"]
    assert "평균 퍼트" in assistant["content"]
    assert assistant["evidence"]["ollama"]["used"] is False
