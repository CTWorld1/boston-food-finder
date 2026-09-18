"""
Boston Food Finder - Phase 1 Data Validation Script
Queries Geoapify Places API across multiple Boston-area neighborhoods
and computes field coverage stats for cuisine, opening_hours, and price signals.
"""

import os
import time
import json
import csv
from dotenv import load_dotenv
import requests

load_dotenv()
API_KEY = os.getenv("GEOAPIFY_API_KEY")


def get_geoapify_api_key() -> str:
    api_key = os.getenv("GEOAPIFY_API_KEY")
    if not api_key:
        raise RuntimeError("GEOAPIFY_API_KEY is not set. Add it to your .env file or environment.")
    return api_key

# Neighborhood center points: (name, lon, lat)
CENTERS = [
    ("Allston/BU", -71.1054, 42.3505),
    ("Back Bay", -71.0808, 42.3503),
    ("Fenway", -71.0972, 42.3467),
    ("Cambridge/Harvard Sq", -71.1189, 42.3736),
    ("South End", -71.0731, 42.3396),
]

RADIUS_METERS = 3000  # ~1.9 miles per neighborhood, avoids heavy overlap
LIMIT = 20            # Geoapify free-tier friendly batch size per request

BASE_URL = "https://api.geoapify.com/v2/places"


def fetch_restaurants(lon, lat, radius, limit, api_key):
    params = {
        "categories": "catering.restaurant",
        "filter": f"circle:{lon},{lat},{radius}",
        "bias": f"proximity:{lon},{lat}",
        "limit": limit,
        "apiKey": api_key,
    }
    resp = requests.get(BASE_URL, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json().get("features", [])


def parse_record(feature, neighborhood):
    props = feature.get("properties", {})
    raw = props.get("datasource", {}).get("raw", {})

    name = props.get("name")
    categories = props.get("categories", [])
    opening_hours = raw.get("opening_hours")
    cuisine = raw.get("cuisine")

    price_signal = None
    for key in ("price_range", "price", "cost"):
        if key in raw:
            price_signal = raw[key]
            break

    return {
        "neighborhood": neighborhood,
        "name": name,
        "lat": props.get("lat"),
        "lon": props.get("lon"),
        "address": props.get("formatted"),
        "categories": ";".join(categories) if categories else "",
        "has_cuisine_tag": bool(cuisine),
        "cuisine_raw": cuisine or "",
        "has_opening_hours": bool(opening_hours),
        "opening_hours_raw": opening_hours or "",
        "has_price_signal": bool(price_signal),
        "price_signal_raw": price_signal or "",
    }


def main():
    api_key = get_geoapify_api_key()
    all_records = []
    seen_names_coords = set()

    for neighborhood, lon, lat in CENTERS:
        print(f"Querying {neighborhood}...")
        try:
            features = fetch_restaurants(lon, lat, RADIUS_METERS, LIMIT, api_key)
        except requests.RequestException as e:
            print(f"  ERROR fetching {neighborhood}: {e}")
            continue

        for feature in features:
            record = parse_record(feature, neighborhood)
            dedup_key = (record["name"], round(record["lat"] or 0, 4), round(record["lon"] or 0, 4))
            if dedup_key in seen_names_coords:
                continue
            seen_names_coords.add(dedup_key)
            all_records.append(record)

        time.sleep(1)  # be polite to the free tier rate limit

    if not all_records:
        print("No records fetched. Check your API key and network connection.")
        return

    # Write raw data CSV
    fieldnames = list(all_records[0].keys())
    with open("geoapify_boston_sample.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_records)

    # Compute coverage stats
    total = len(all_records)
    cuisine_count = sum(1 for r in all_records if r["has_cuisine_tag"])
    hours_count = sum(1 for r in all_records if r["has_opening_hours"])
    price_count = sum(1 for r in all_records if r["has_price_signal"])

    stats = {
        "total_unique_restaurants": total,
        "cuisine_coverage_pct": round(100 * cuisine_count / total, 1),
        "opening_hours_coverage_pct": round(100 * hours_count / total, 1),
        "price_signal_coverage_pct": round(100 * price_count / total, 1),
    }

    with open("field_coverage_report.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

    print("\n--- Field Coverage Report ---")
    for k, v in stats.items():
        print(f"{k}: {v}")
    print("\nRaw data saved to geoapify_boston_sample.csv")
    print("Coverage stats saved to field_coverage_report.json")


if __name__ == "__main__":
    main()
