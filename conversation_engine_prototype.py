from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from google import genai


ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

MODEL_NAME = "gemini-3.6-flash"


def get_gemini_api_key() -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set. Add it to your .env file or environment.")
    return api_key

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

APPROVED_FILTER_FIELDS = tuple(FILTER_TEMPLATE.keys())

ALLOWED_CRAVINGS = {
    "spicy",
    "light",
    "sweet",
    "savory",
    "fresh",
    "comforting",
    "rich",
    "hearty",
}

ALLOWED_TEXTURES = {
    "crunchy",
    "crispy",
    "creamy",
    "soft",
    "chewy",
    "light",
}

ALLOWED_DIETARY = {
    "vegan",
    "vegetarian",
    "gluten_free",
    "dairy_free",
    "halal",
    "kosher",
}

ALLOWED_PRICE_LEVELS = {"$", "$$", "$$$", "$$$$"}
EXCLUDED_SYNONYMS = {
    "spicy": {"spicy", "too spicy"},
}


@dataclass(frozen=True)
class TestCase:
    label: str
    message: str
    expected: dict[str, Any]
    expected_behavior: str


TEST_CASES: list[TestCase] = [
    TestCase(
        label="Single restriction",
        message="no pizza",
        expected={"excluded": ["pizza"]},
        expected_behavior='excluded contains "pizza"',
    ),
    TestCase(
        label="Single preference",
        message="something crunchy",
        expected={"texture": "crunchy"},
        expected_behavior='texture is "crunchy"',
    ),
    TestCase(
        label="Multiple restrictions",
        message="no seafood, no dairy, and nothing too spicy",
        expected={"excluded": ["seafood", "dairy", "spicy"]},
        expected_behavior="all restrictions are captured correctly",
    ),
    TestCase(
        label="Cuisine + distance",
        message="Thai food within 2 miles",
        expected={"cuisine": "thai", "distance_miles": 2},
        expected_behavior="cuisine and distance are extracted",
    ),
    TestCase(
        label="Budget",
        message="Mexican under $20",
        expected={"cuisine": "mexican", "budget_max": 20},
        expected_behavior="cuisine and budget are extracted",
    ),
    TestCase(
        label="Vague answer",
        message="whatever is good",
        expected={},
        expected_behavior="the model does not invent filters",
    ),
    TestCase(
        label="Surprise request",
        message="surprise me",
        expected={},
        expected_behavior="the model returns mostly empty filters",
    ),
    TestCase(
        label="Mixed request",
        message="I want Japanese food, not raw fish, something light and crunchy",
        expected={
            "cuisine": "japanese",
            "excluded": ["raw fish"],
            "craving": "light",
            "texture": "crunchy",
        },
        expected_behavior="it captures cuisine, exclusions, and preferences",
    ),
    TestCase(
        label="Contradictory input",
        message="I want sushi but no seafood",
        expected={"cuisine": "sushi", "excluded": ["seafood"]},
        expected_behavior="it preserves both inputs without fixing the request",
    ),
]


def build_prompt(message: str) -> str:
    schema = json.dumps(FILTER_TEMPLATE, indent=2)
    return f"""You are a strict JSON extraction engine for restaurant filters.

Return only valid JSON. Do not wrap the answer in markdown fences.
Do not add explanations, labels, or commentary.
Do not invent values the user did not say.
If the user is vague or says "surprise me", keep the preference fields null or empty.
Preserve contradictions instead of "fixing" the request.

Approved output schema:
{schema}

Field rules:
- cuisine: extract only if the user explicitly names a cuisine or food type.
- excluded: add explicit restrictions such as "no pizza", "no seafood", "not raw fish", or "nothing too spicy".
- craving: use for explicit taste or style words such as "spicy" or "light".
- texture: use for texture words such as "crunchy".
- budget_max: extract only from explicit budget limits such as "under $25".
- distance_miles: extract only from explicit distance limits such as "within 3 miles".
- price_levels: populate only when the user explicitly mentions price symbols like $, $$, $$$, or $$$$.
- dietary: add explicit dietary requirements such as "vegan".
- open_now: set only if the user explicitly mentions that they want places open now.

Special mappings for this prototype:
- "no pizza" -> excluded includes "pizza"
- "no seafood" -> excluded includes "seafood"
- "vegan" -> dietary includes "vegan"
- "crunchy" -> texture = "crunchy"
- "spicy" -> craving = "spicy"
- "under $25" -> budget_max = 25
- "within 3 miles" -> distance_miles = 3
- "surprise me" -> keep preference fields null or empty
- vague requests -> keep unknown fields null or empty

User message:
{message}
"""


def build_batch_prompt(cases: list[TestCase]) -> str:
        case_block = json.dumps(
                [{"label": case.label, "message": case.message} for case in cases],
                indent=2,
        )
        schema = json.dumps(FILTER_TEMPLATE, indent=2)
        return f"""You are a strict JSON extraction engine for restaurant filters.

Process each input independently and preserve contradictions instead of fixing them.
Return only valid JSON. Do not wrap the answer in markdown fences.
Do not add explanations, labels, or commentary outside the JSON array.
Do not invent values the user did not say.

Return a JSON array with the same length and order as the input list.
Each array item must be an object with exactly these keys:
{{
    "label": "...",
    "message": "...",
    "filters": {schema}
}}

Field rules:
- cuisine: extract only if the user explicitly names a cuisine or food type.
- excluded: add explicit restrictions such as "no pizza", "no seafood", "not raw fish", or "nothing too spicy".
- craving: use for explicit taste or style words such as "spicy" or "light".
- texture: use for texture words such as "crunchy".
- budget_max: extract only from explicit budget limits such as "under $25".
- distance_miles: extract only from explicit distance limits such as "within 3 miles".
- price_levels: populate only when the user explicitly mentions price symbols like $, $$, $$$, or $$$$.
- dietary: add explicit dietary requirements such as "vegan".
- open_now: set only if the user explicitly mentions that they want places open now.

Special mappings for this prototype:
- "no pizza" -> excluded includes "pizza"
- "no seafood" -> excluded includes "seafood"
- "vegan" -> dietary includes "vegan"
- "crunchy" -> texture = "crunchy"
- "spicy" -> craving = "spicy"
- "under $25" -> budget_max = 25
- "within 3 miles" -> distance_miles = 3
- "surprise me" -> keep preference fields null or empty
- vague requests -> keep unknown fields null or empty

Input list:
{case_block}
"""


def strip_code_fences(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def parse_json_response(text: str) -> dict[str, Any]:
    cleaned = strip_code_fences(text)
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    payload_text = match.group(0) if match else cleaned
    payload = json.loads(payload_text)
    if not isinstance(payload, dict):
        raise ValueError("Gemini response was not a JSON object")
    return payload


def parse_json_array_response(text: str) -> list[dict[str, Any]]:
    cleaned = strip_code_fences(text)
    match = re.search(r"\[.*\]", cleaned, flags=re.DOTALL)
    payload_text = match.group(0) if match else cleaned
    payload = json.loads(payload_text)
    if isinstance(payload, dict) and isinstance(payload.get("results"), list):
        payload = payload["results"]
    if not isinstance(payload, list):
        raise ValueError("Gemini batch response was not a JSON array")
    for item in payload:
        if not isinstance(item, dict):
            raise ValueError("Gemini batch response contained a non-object item")
    return payload


def normalize_value(value: Any) -> Any:
    if isinstance(value, str):
        return " ".join(value.strip().lower().split())
    return value


def is_empty(value: Any) -> bool:
    return value is None or value == []


def value_in_message(value: str, message: str) -> bool:
    normalized_message = normalize_value(message)
    normalized_value = normalize_value(value)
    return isinstance(normalized_value, str) and normalized_value in normalized_message


def validate_payload(payload: dict[str, Any], message: str) -> list[str]:
    issues: list[str] = []
    message_lower = normalize_value(message)

    if set(payload.keys()) != set(APPROVED_FILTER_FIELDS):
        issues.append(
            f"unexpected keys: {sorted(set(payload.keys()) ^ set(APPROVED_FILTER_FIELDS))}"
        )

    cuisine = payload.get("cuisine")
    if cuisine is not None:
        if not isinstance(cuisine, str):
            issues.append("cuisine must be a string or null")
        elif not value_in_message(cuisine, message_lower):
            issues.append(f'cuisine "{cuisine}" is not justified by the message')

    excluded = payload.get("excluded")
    if not isinstance(excluded, list):
        issues.append("excluded must be a list")
    else:
        for item in excluded:
            if not isinstance(item, str):
                issues.append("excluded must contain strings only")
                continue
            if not value_in_message(item, message_lower):
                issues.append(f'excluded value "{item}" is not justified by the message')

    craving = payload.get("craving")
    if craving is not None:
        if not isinstance(craving, str):
            issues.append("craving must be a string or null")
        elif normalize_value(craving) not in ALLOWED_CRAVINGS:
            issues.append(f'craving "{craving}" is not in the allowed set')
        elif not value_in_message(craving, message_lower):
            issues.append(f'craving "{craving}" is not justified by the message')

    texture = payload.get("texture")
    if texture is not None:
        if not isinstance(texture, str):
            issues.append("texture must be a string or null")
        elif normalize_value(texture) not in ALLOWED_TEXTURES:
            issues.append(f'texture "{texture}" is not in the allowed set')
        elif not value_in_message(texture, message_lower):
            issues.append(f'texture "{texture}" is not justified by the message')

    budget_max = payload.get("budget_max")
    if budget_max is not None:
        if not isinstance(budget_max, (int, float)):
            issues.append("budget_max must be numeric or null")
        elif not re.search(r"(?:under|below|less than|no more than|up to)\s*\$?" + re.escape(str(int(budget_max))), message_lower):
            issues.append(f"budget_max {budget_max} is not justified by the message")

    distance_miles = payload.get("distance_miles")
    if distance_miles is not None:
        if not isinstance(distance_miles, (int, float)):
            issues.append("distance_miles must be numeric or null")
        elif not re.search(r"within\s*" + re.escape(str(int(distance_miles))) + r"\s*miles?", message_lower):
            issues.append(f"distance_miles {distance_miles} is not justified by the message")

    price_levels = payload.get("price_levels")
    if not isinstance(price_levels, list):
        issues.append("price_levels must be a list")
    else:
        for item in price_levels:
            if not isinstance(item, str):
                issues.append("price_levels must contain strings only")
                continue
            if item not in ALLOWED_PRICE_LEVELS:
                issues.append(f'price_levels value "{item}" is not allowed')

    dietary = payload.get("dietary")
    if not isinstance(dietary, list):
        issues.append("dietary must be a list")
    else:
        for item in dietary:
            if not isinstance(item, str):
                issues.append("dietary must contain strings only")
                continue
            normalized = normalize_value(item)
            if normalized not in ALLOWED_DIETARY:
                issues.append(f'dietary value "{item}" is not allowed')
            elif not value_in_message(normalized, message_lower):
                issues.append(f'dietary value "{item}" is not justified by the message')

    open_now = payload.get("open_now")
    if open_now is not None and not isinstance(open_now, bool):
        issues.append("open_now must be a boolean or null")

    return issues


def compare_expected(payload: dict[str, Any], expected: dict[str, Any]) -> list[str]:
    issues: list[str] = []

    for field in APPROVED_FILTER_FIELDS:
        actual = payload.get(field)
        if field not in expected:
            if not is_empty(actual):
                issues.append(f"{field} should be empty")
            continue

        wanted = expected[field]
        if isinstance(wanted, list):
            if not isinstance(actual, list):
                issues.append(f"{field} should be a list")
                continue
            actual_norm = {normalize_value(item) for item in actual if isinstance(item, str)}
            missing = []
            for item in wanted:
                normalized_item = normalize_value(item)
                synonyms = EXCLUDED_SYNONYMS.get(normalized_item, {normalized_item})
                if not any(synonym in actual_norm for synonym in synonyms):
                    missing.append(item)
            if missing:
                issues.append(f"{field} is missing {missing}")
        elif isinstance(wanted, (int, float)):
            if actual != wanted:
                issues.append(f"{field} should be {wanted!r} but was {actual!r}")
        else:
            if normalize_value(actual) != normalize_value(wanted):
                issues.append(f"{field} should be {wanted!r} but was {actual!r}")

    return issues


def summarize_payload(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def ask_gemini(message: str) -> tuple[dict[str, Any], str]:
    client = genai.Client(api_key=get_gemini_api_key())
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=build_prompt(message),
        config={
            "temperature": 0,
            "response_mime_type": "application/json",
            "max_output_tokens": 512,
        },
    )
    response_text = response.text or ""
    payload = parse_json_response(response_text)
    return payload, response_text


def ask_gemini_batch(cases: list[TestCase]) -> tuple[list[dict[str, Any]], str]:
    client = genai.Client(api_key=get_gemini_api_key())
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=build_batch_prompt(cases),
        config={
            "temperature": 0,
            "response_mime_type": "application/json",
            "max_output_tokens": 4096,
        },
    )
    response_text = response.text or ""
    payload = parse_json_array_response(response_text)
    return payload, response_text


def extract_filters(message: str) -> dict[str, Any]:
    payload, _ = ask_gemini(message)
    return payload


def assess_case(case: TestCase, payload: dict[str, Any], raw_response: str) -> dict[str, Any]:
    validation_issues = validate_payload(payload, case.message)
    expectation_issues = compare_expected(payload, case.expected)
    all_issues = validation_issues + expectation_issues
    json_valid = not validation_issues
    justified = not validation_issues
    passed = json_valid and not expectation_issues

    return {
        "label": case.label,
        "message": case.message,
        "expected_behavior": case.expected_behavior,
        "raw_response": raw_response,
        "parsed": payload,
        "json_valid": json_valid,
        "justified": justified,
        "pass": passed,
        "notes": "; ".join(all_issues) if all_issues else "OK",
    }


def run_test_case(case: TestCase) -> dict[str, Any]:
    raw_response = ""
    parsed: dict[str, Any] | None = None
    parse_issues: list[str] = []

    try:
        parsed, raw_response = ask_gemini(case.message)
    except Exception as exc:  # pragma: no cover - network/model failures are surfaced in output
        parse_issues = [f"request failed: {exc}"]

    if parsed is None:
        return {
            "label": case.label,
            "message": case.message,
            "expected_behavior": case.expected_behavior,
            "raw_response": raw_response,
            "parsed": None,
            "json_valid": False,
            "justified": False,
            "pass": False,
            "notes": "; ".join(parse_issues),
        }

    return assess_case(case, parsed, raw_response)


def run_test_suite() -> list[dict[str, Any]]:
    batch_payloads, raw_response = ask_gemini_batch(TEST_CASES)
    if len(batch_payloads) != len(TEST_CASES):
        mismatch_note = f"batch response length {len(batch_payloads)} did not match test count {len(TEST_CASES)}"
        return [
            {
                "label": case.label,
                "message": case.message,
                "expected_behavior": case.expected_behavior,
                "raw_response": raw_response,
                "parsed": None,
                "json_valid": False,
                "justified": False,
                "pass": False,
                "notes": mismatch_note,
            }
            for case in TEST_CASES
        ]

    rows: list[dict[str, Any]] = []
    for case, item in zip(TEST_CASES, batch_payloads, strict=True):
        filters = item.get("filters") if isinstance(item.get("filters"), dict) else item
        if not isinstance(filters, dict):
            rows.append(
                {
                    "label": case.label,
                    "message": case.message,
                    "expected_behavior": case.expected_behavior,
                    "raw_response": raw_response,
                    "parsed": None,
                    "json_valid": False,
                    "justified": False,
                    "pass": False,
                    "notes": "batch item did not contain a filters object",
                }
            )
            continue

        rows.append(assess_case(case, filters, raw_response))

    return rows


def render_markdown_table(rows: list[dict[str, Any]]) -> str:
    lines = [
        "# Person B Prototype Results",
        "",
        f"Model: `{MODEL_NAME}`",
        "",
        "| Input | Expected behavior | Actual result | Valid JSON? | Every populated field justified? | Pass? | Notes |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]

    for row in rows:
        actual_result = summarize_payload(row["parsed"]) if row["parsed"] is not None else row["notes"]
        lines.append(
            "| "
            + " | ".join(
                [
                    escape_markdown(row["message"]),
                    escape_markdown(row["expected_behavior"]),
                    escape_markdown(actual_result),
                    "Yes" if row["json_valid"] else "No",
                    "Yes" if row["justified"] else "No",
                    "Yes" if row["pass"] else "No",
                    escape_markdown(row["notes"]),
                ]
            )
            + " |"
        )

    return "\n".join(lines) + "\n"


def escape_markdown(text: str) -> str:
    return text.replace("|", r"\|").replace("\n", " ")


def main() -> None:
    if len(sys.argv) > 1:
        message = " ".join(sys.argv[1:])
        row = run_test_case(
            TestCase(
                label="Ad hoc request",
                message=message,
                expected={},
                expected_behavior="single-message prototype run",
            )
        )
        print(summarize_payload(row["parsed"]) if row["parsed"] is not None else row["notes"])
        if not row["pass"]:
            print(f"\n{row['notes']}")
            sys.exit(1)
        return

    rows = run_test_suite()
    results_path = ROOT / "person_b_results.md"
    results_path.write_text(render_markdown_table(rows), encoding="utf-8")

    print(render_markdown_table(rows))
    failing = [row for row in rows if not row["pass"]]
    if failing:
        print("\nFailures:")
        for row in failing:
            print(f"- {row['label']}: {row['notes']}")
        sys.exit(1)


if __name__ == "__main__":
    main()