import importlib


def test_validate_geoapify_parse_record_handles_sample_feature():
    validate_geoapify = importlib.import_module("validate_geoapify")

    feature = {
        "properties": {
            "name": "Crispy Crêpes Café",
            "lat": 42.3496,
            "lon": -71.1056,
            "formatted": "714 Commonwealth Avenue, Boston, MA 02215",
            "categories": ["catering", "catering.restaurant"],
            "datasource": {
                "raw": {
                    "opening_hours": "Mo-Su 08:00-21:00",
                    "cuisine": "crepe",
                    "price_range": "$$"
                }
            }
        }
    }

    record = validate_geoapify.parse_record(feature, "Allston/BU")

    assert record["neighborhood"] == "Allston/BU"
    assert record["name"] == "Crispy Crêpes Café"
    assert record["has_cuisine_tag"] is True
    assert record["has_opening_hours"] is True
    assert record["has_price_signal"] is True
    assert record["price_signal_raw"] == "$$"


def test_conversation_engine_allows_import_without_runtime_keys():
    conversation = importlib.import_module("conversation_engine_prototype")

    payload = {
        "cuisine": "thai",
        "excluded": ["seafood"],
        "craving": None,
        "texture": "crunchy",
        "budget_max": None,
        "distance_miles": None,
        "price_levels": [],
        "dietary": [],
        "open_now": None,
    }

    expected = {
        "cuisine": "thai",
        "excluded": ["seafood"],
        "texture": "crunchy",
    }

    issues = conversation.compare_expected(payload, expected)
    assert issues == []
    assert "Thai food within 2 miles" in conversation.build_prompt("Thai food within 2 miles")


def test_unified_entrypoint_combines_geoapify_and_conversation_features():
    app = importlib.import_module("boston_food_finder")

    assert hasattr(app, "collect_geoapify_sample")
    assert hasattr(app, "extract_filters")
    assert callable(app.collect_geoapify_sample)
    assert callable(app.extract_filters)
