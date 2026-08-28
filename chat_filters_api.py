from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, ConfigDict, Field

app = FastAPI(title="Chat Filter API")

FILTER_TEMPLATE: dict[str, Any] = {
    "cuisine": None,
    "excluded": [],
    "craving": None,
    "texture": None,
    "budget_max": None,
    "distance_miles": None,
    "price_levels": [],
    "dietary": [],
    "open_now": None,
}

CUISINE_KEYWORDS = [
    "thai",
    "japanese",
    "mexican",
    "indian",
    "italian",
    "chinese",
    "sushi",
    "pizza",
    "bbq",
    "american",
    "mediterranean",
]

NEGATED_ITEM_WORDS = {
    "seafood",
    "dairy",
    "cheese",
    "pizza",
    "raw fish",
    "fish",
    "spicy",
    "beef",
    "pork",
    "chicken",
}


class SessionState(BaseModel):
    model_config = ConfigDict(extra="ignore")

    rejected_items: list[str] = Field(default_factory=list)
    chosen_cuisine: str | None = None

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any) -> None:
        setattr(self, key, value)


class ChatFilterRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    message: str
    session_state: SessionState | dict[str, Any] | None = None
    session_id: str | None = None


class ChatFilterResponse(BaseModel):
    filters: dict[str, Any]
    session_state: dict[str, Any]


class InMemorySessionStore:
    def __init__(self) -> None:
        self._state: dict[str, SessionState] = {}

    def get(self, session_id: str) -> SessionState:
        return self._state.get(session_id, SessionState())

    def set(self, session_id: str, state: SessionState | Mapping[str, Any]) -> SessionState:
        populated = SessionState.model_validate(state) if isinstance(state, Mapping) else state
        self._state[session_id] = populated
        return populated

    def update(
        self,
        session_id: str,
        message_or_payload: str | Mapping[str, Any],
        state: SessionState | Mapping[str, Any] | None = None,
    ) -> SessionState:
        current_state = self.get(session_id)

        if isinstance(message_or_payload, Mapping):
            payload = message_or_payload
            message = str(payload.get("message", ""))
            session_payload = payload.get("session_state")
            if session_payload is not None:
                current_state = SessionState.model_validate(session_payload)
        else:
            message = str(message_or_payload)

        if state is not None:
            current_state = SessionState.model_validate(state)

        extracted = extract_filters_from_message(message)
        merged = merge_session_state(current_state, extracted)
        self._state[session_id] = merged
        return merged


store = InMemorySessionStore()


def normalize_text(value: str) -> str:
    return " ".join(value.lower().split())


def to_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value]
    return []


def merge_session_state(current: SessionState, extracted: dict[str, Any]) -> SessionState:
    rejected = list(dict.fromkeys([*current.rejected_items, *to_list(extracted.get("excluded"))]))
    cuisine = extracted.get("cuisine") or current.chosen_cuisine
    return SessionState(rejected_items=rejected, chosen_cuisine=cuisine)


def extract_cuisine(message: str) -> str | None:
    normalized = normalize_text(message)
    for cuisine in CUISINE_KEYWORDS:
        if re.search(rf"\b{re.escape(cuisine)}\b", normalized):
            return cuisine
    return None


def extract_excluded_items(message: str) -> list[str]:
    normalized = normalize_text(message)
    items: list[str] = []
    patterns = [
        r"\b(?:no|not|avoid|without|nothing|never)\s+(?:too\s+)?([a-z][a-z\s-]{0,40})",
        r"\b(?:no|not|avoid|without|nothing|never)\s+(?:too\s+)?([a-z][a-z\s-]{0,40})(?:,|\.|;|$)",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, normalized):
            candidate = match.group(1).strip()
            if not candidate:
                continue
            if candidate in {"thai", "japanese", "mexican", "indian", "italian", "chinese", "sushi", "pizza", "bbq"}:
                continue
            candidate = " ".join(candidate.split())
            if candidate and candidate not in items:
                items.append(candidate)

    for item in sorted(NEGATED_ITEM_WORDS, key=len, reverse=True):
        if re.search(rf"\b(?:no|not|avoid|without|nothing|never)\s+(?:too\s+)?{re.escape(item)}\b", normalized):
            if item not in items:
                items.append(item)
        if item == "raw fish" and "raw fish" in normalized and "no raw fish" not in normalized and "not raw fish" not in normalized:
            if item not in items:
                items.append(item)
    return items


def extract_budget_max(message: str) -> int | None:
    match = re.search(r"(?:under|below|less than|no more than|up to)\s*\$?(\d+)", normalize_text(message))
    if match:
        return int(match.group(1))
    return None


def extract_distance_miles(message: str) -> int | None:
    match = re.search(r"within\s+(\d+)\s*(?:miles?|mi)", normalize_text(message))
    if match:
        return int(match.group(1))
    return None


def extract_price_levels(message: str) -> list[str]:
    levels: list[str] = []
    for symbol in ["$", "$$", "$$$", "$$$$"]:
        if symbol in message:
            levels.append(symbol)
    return levels


def extract_dietary(message: str) -> list[str]:
    dietary = []
    for value in ["vegan", "vegetarian", "gluten free", "dairy free", "halal", "kosher"]:
        if value in normalize_text(message):
            dietary.append(value.replace(" ", "_"))
    return dietary


def extract_filters_from_message(message: str) -> dict[str, Any]:
    text = normalize_text(message)
    filters = {
        "cuisine": extract_cuisine(text),
        "excluded": extract_excluded_items(text),
        "craving": None,
        "texture": None,
        "budget_max": extract_budget_max(text),
        "distance_miles": extract_distance_miles(text),
        "price_levels": extract_price_levels(text),
        "dietary": extract_dietary(text),
        "open_now": None,
    }

    if re.search(r"\b(?:spicy|too spicy)\b", text):
        filters["craving"] = "spicy"
    if re.search(r"\b(?:light|fresh)\b", text):
        filters["craving"] = "light"
    if re.search(r"\bcrunchy\b", text):
        filters["texture"] = "crunchy"
    if re.search(r"\bopen now\b", text):
        filters["open_now"] = True

    return filters


@app.post("/chat/filters", response_model=ChatFilterResponse)
def chat_filters(payload: ChatFilterRequest) -> ChatFilterResponse:
    session_payload = payload.session_state or {}
    base_session = SessionState.model_validate(session_payload)
    session_key = payload.session_id or "default"
    state = store.update(session_key, payload.message, base_session)
    extracted = extract_filters_from_message(payload.message)
    if extracted.get("cuisine"):
        state.chosen_cuisine = extracted["cuisine"]
    if extracted.get("excluded"):
        state.rejected_items = list(dict.fromkeys([*state.rejected_items, *extracted["excluded"]]))
    store.set(session_key, state)

    response_filters: dict[str, Any] = {
        "cuisine": state.chosen_cuisine or extracted.get("cuisine"),
        "excluded": state.rejected_items,
        "craving": extracted.get("craving"),
        "texture": extracted.get("texture"),
        "budget_max": extracted.get("budget_max"),
        "distance_miles": extracted.get("distance_miles"),
        "price_levels": extracted.get("price_levels"),
        "dietary": extracted.get("dietary"),
        "open_now": extracted.get("open_now"),
    }

    return ChatFilterResponse(filters=response_filters, session_state={
        "rejected_items": state.rejected_items,
        "chosen_cuisine": state.chosen_cuisine,
    })


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
