from __future__ import annotations

from typing import Any

from conversation_engine_prototype import extract_filters
from validate_geoapify import fetch_restaurants, get_geoapify_api_key, parse_record


def collect_geoapify_sample() -> list[dict[str, Any]]:
    api_key = get_geoapify_api_key()
    all_records: list[dict[str, Any]] = []
    seen_names_coords: set[tuple[str, float, float]] = set()

    for neighborhood, lon, lat in [
        ("Allston/BU", -71.1054, 42.3505),
        ("Back Bay", -71.0808, 42.3503),
        ("Fenway", -71.0972, 42.3467),
        ("Cambridge/Harvard Sq", -71.1189, 42.3736),
        ("South End", -71.0731, 42.3396),
    ]:
        features = fetch_restaurants(lon, lat, 3000, 20, api_key)
        for feature in features:
            record = parse_record(feature, neighborhood)
            dedup_key = (
                record["name"],
                round(record["lat"] or 0, 4),
                round(record["lon"] or 0, 4),
            )
            if dedup_key in seen_names_coords:
                continue
            seen_names_coords.add(dedup_key)
            all_records.append(record)

    return all_records


def extract_filters_from_message(message: str) -> dict[str, Any]:
    return extract_filters(message)


__all__ = ["collect_geoapify_sample", "extract_filters_from_message", "extract_filters"]
