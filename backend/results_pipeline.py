import os
import requests
from dotenv import load_dotenv


load_dotenv()

API_KEY = os.getenv("GEOAPIFY_API_KEY")

GEOCODING_URL = "https://api.geoapify.com/v1/geocode/search"
PLACES_URL = "https://api.geoapify.com/v2/places"
DETAILS_URL = "https://api.geoapify.com/v2/place-details"


# Common cuisines supported directly by Geoapify.
CUISINE_CATEGORIES = {
    "afghan": "catering.restaurant.afghan",
    "african": "catering.restaurant.african",
    "american": "catering.restaurant.american",
    "asian": "catering.restaurant.asian",
    "barbecue": "catering.restaurant.barbecue",
    "bbq": "catering.restaurant.barbecue",
    "brazilian": "catering.restaurant.brazilian",
    "burger": "catering.restaurant.burger",
    "caribbean": "catering.restaurant.caribbean",
    "chinese": "catering.restaurant.chinese",
    "cuban": "catering.restaurant.cuban",
    "ethiopian": "catering.restaurant.ethiopian",
    "filipino": "catering.restaurant.filipino",
    "french": "catering.restaurant.french",
    "german": "catering.restaurant.german",
    "greek": "catering.restaurant.greek",
    "indian": "catering.restaurant.indian",
    "italian": "catering.restaurant.italian",
    "jamaican": "catering.restaurant.jamaican",
    "japanese": "catering.restaurant.japanese",
    "korean": "catering.restaurant.korean",
    "lebanese": "catering.restaurant.lebanese",
    "mediterranean": "catering.restaurant.mediterranean",
    "mexican": "catering.restaurant.mexican",
    "moroccan": "catering.restaurant.moroccan",
    "nepalese": "catering.restaurant.nepalese",
    "pakistani": "catering.restaurant.pakistani",
    "persian": "catering.restaurant.persian",
    "peruvian": "catering.restaurant.peruvian",
    "pizza": "catering.restaurant.pizza",
    "portuguese": "catering.restaurant.portuguese",
    "seafood": "catering.restaurant.seafood",
    "spanish": "catering.restaurant.spanish",
    "steak": "catering.restaurant.steak_house",
    "sushi": "catering.restaurant.sushi",
    "thai": "catering.restaurant.thai",
    "turkish": "catering.restaurant.turkish",
    "vietnamese": "catering.restaurant.vietnamese",
}


def check_api_key():
    """Make sure the Geoapify API key exists."""

    if not API_KEY:
        raise RuntimeError(
            "GEOAPIFY_API_KEY was not found. "
            "Add it to your .env file."
        )


def geocode_location(location):
    """
    Convert a location such as 'Boston, MA'
    into latitude and longitude.
    """

    params = {
        "text": location,
        "format": "json",
        "limit": 1,
        "apiKey": API_KEY,
    }

    response = requests.get(
        GEOCODING_URL,
        params=params,
        timeout=15,
    )

    response.raise_for_status()

    data = response.json()

    results = data.get("results", [])

    if not results:
        return None

    result = results[0]

    return {
        "formatted": result.get("formatted"),
        "latitude": result.get("lat"),
        "longitude": result.get("lon"),
    }


def get_cuisine_category(cuisine):
    """
    Convert user cuisine input into a Geoapify category.

    If Geoapify does not have a direct category,
    fall back to searching all restaurants.
    """

    cuisine = cuisine.strip().lower()

    category = CUISINE_CATEGORIES.get(cuisine)

    if category:
        return category, True

    return "catering.restaurant", False


def search_places(latitude, longitude, cuisine, radius=8000, limit=20):
    """
    Search restaurants around the supplied coordinates.
    """

    category, exact_category = get_cuisine_category(cuisine)

    params = {
        "categories": category,
        "filter": (
            f"circle:{longitude},"
            f"{latitude},"
            f"{radius}"
        ),
        "bias": f"proximity:{longitude},{latitude}",
        "limit": limit,
        "apiKey": API_KEY,
    }

    response = requests.get(
        PLACES_URL,
        params=params,
        timeout=15,
    )

    response.raise_for_status()

    data = response.json()

    return data.get("features", []), exact_category


def get_place_details(place_id):
    """
    Retrieve additional information for one restaurant.
    """

    params = {
        "id": place_id,
        "features": "details",
        "apiKey": API_KEY,
    }

    response = requests.get(
        DETAILS_URL,
        params=params,
        timeout=15,
    )

    response.raise_for_status()

    data = response.json()

    for feature in data.get("features", []):
        properties = feature.get("properties", {})

        if properties.get("feature_type") == "details":
            return properties

    return {}


def cuisine_matches(details, cuisine):
    """
    Used for cuisines that do not have a dedicated
    Geoapify restaurant category.
    """

    catering = details.get("catering", {})

    served_cuisine = catering.get("cuisine", "")

    if isinstance(served_cuisine, list):
        served_cuisine = " ".join(served_cuisine)

    return cuisine.lower() in str(served_cuisine).lower()


def build_restaurant_result(place, cuisine, exact_category):
    """
    Convert the raw Geoapify result into a simple
    dictionary for the rest of the application.
    """

    basic = place.get("properties", {})

    place_id = basic.get("place_id")

    if not place_id:
        return None

    details = get_place_details(place_id)

    if not exact_category:
        if not cuisine_matches(details, cuisine):
            return None

    contact = details.get("contact", {})
    catering = details.get("catering", {})
    media = details.get("wiki_and_media", {})

    return {
        "name": details.get("name") or basic.get("name"),
        "address": (
            details.get("formatted")
            or basic.get("formatted")
        ),
        "latitude": (
            details.get("lat")
            or basic.get("lat")
        ),
        "longitude": (
            details.get("lon")
            or basic.get("lon")
        ),
        "cuisine": catering.get(
            "cuisine",
            cuisine.title(),
        ),
        "hours": details.get(
            "opening_hours",
            "Not available",
        ),
        "phone": contact.get(
            "phone",
            "Not available",
        ),
        "website": details.get(
            "website",
            "Not available",
        ),
        "photo_url": media.get(
            "image",
            "Not available",
        ),

        # Geoapify / OSM generally does not provide
        # consumer-review ratings or Google/Yelp-style
        # price levels.
        "rating": "Not available",
        "price": "Not available",

        "place_id": place_id,
    }


def search_restaurants(
    cuisine,
    location,
    radius=8000,
    max_results=10,
):
    """
    Main function for the restaurant results pipeline.

    Input:
        cuisine = "Italian"
        location = "Boston, MA"

    Output:
        list of restaurant dictionaries
    """

    check_api_key()

    location_data = geocode_location(location)

    if not location_data:
        raise ValueError(
            f"Could not find location: {location}"
        )

    latitude = location_data["latitude"]
    longitude = location_data["longitude"]

    places, exact_category = search_places(
        latitude,
        longitude,
        cuisine,
    )

    restaurants = []

    for place in places:
        try:
            restaurant = build_restaurant_result(
                place,
                cuisine,
                exact_category,
            )

            if restaurant:
                restaurants.append(restaurant)

        except requests.RequestException:
            # Do not stop the entire search if
            # one restaurant detail request fails.
            continue

        if len(restaurants) >= max_results:
            break

    return {
        "search_location": location_data,
        "cuisine": cuisine,
        "count": len(restaurants),
        "restaurants": restaurants,
    }