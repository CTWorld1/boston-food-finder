from fastapi.testclient import TestClient

from chat_filters_api import app


client = TestClient(app)


def test_extracts_filters_and_updates_session_state():
    payload = {
        "message": "I want Thai food but no seafood",
        "session_state": {"rejected_items": [], "chosen_cuisine": None},
    }

    response = client.post("/chat/filters", json=payload)
    assert response.status_code == 200, response.text

    body = response.json()
    assert body["filters"]["cuisine"] == "thai"
    assert body["filters"]["excluded"] == ["seafood"]
    assert body["session_state"]["rejected_items"] == ["seafood"]
    assert body["session_state"]["chosen_cuisine"] == "thai"


def test_session_state_persists_across_turns_and_keeps_rejections():
    first = client.post(
        "/chat/filters",
        json={
            "message": "I want pizza but not cheese",
            "session_state": {"rejected_items": [], "chosen_cuisine": None},
        },
    )
    assert first.status_code == 200, first.text

    second = client.post(
        "/chat/filters",
        json={
            "message": "Actually, I want Japanese food and still no cheese",
            "session_state": first.json()["session_state"],
        },
    )
    assert second.status_code == 200, second.text

    body = second.json()
    assert body["filters"]["cuisine"] == "japanese"
    assert body["filters"]["excluded"] == ["cheese"]
    assert body["session_state"]["rejected_items"] == ["cheese"]
    assert body["session_state"]["chosen_cuisine"] == "japanese"


def test_session_store_tracks_rejections_and_cuisine_in_memory():
    from chat_filters_api import InMemorySessionStore

    store = InMemorySessionStore()
    store.set("sess-1", {"rejected_items": [], "chosen_cuisine": None})

    updated = store.update(
        "sess-1",
        {"message": "I want Indian food but no dairy", "session_state": {"rejected_items": [], "chosen_cuisine": None}},
    )

    assert updated["rejected_items"] == ["dairy"]
    assert updated["chosen_cuisine"] == "indian"
    assert store.get("sess-1")["chosen_cuisine"] == "indian"
