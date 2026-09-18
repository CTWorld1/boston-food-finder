
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from results_pipeline import search_restaurants


app = FastAPI(
    title="Boston Food Finder API",
    description="Restaurant results API",
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def home():
    return {
        "message": "Boston Food Finder API is running"
    }


@app.get("/health")
def health():
    return {
        "status": "ok"
    }


@app.get("/restaurants")
def restaurants(
    cuisine: str,
    location: str,
    miles: float = 5,
    limit: int = 10,
):
    """
    Search for restaurants by:

    - cuisine
    - location
    - distance in miles
    - maximum number of results

    Example:
    /restaurants?cuisine=Chinese&location=Boston& miles=5&limit=10
    """

    cuisine = cuisine.strip()
    location = location.strip()

    if not cuisine:
        raise HTTPException(
            status_code=400,
            detail="Cuisine is required",
        )

    if not location:
        raise HTTPException(
            status_code=400,
            detail="Location is required",
        )

    if miles <= 0:
        raise HTTPException(
            status_code=400,
            detail="Miles must be greater than 0",
        )

    if miles > 50:
        raise HTTPException(
            status_code=400,
            detail="Maximum search distance is 50 miles",
        )

    if limit < 1:
        raise HTTPException(
            status_code=400,
            detail="Limit must be at least 1",
        )

    if limit > 20:
        limit = 20

    # Convert miles to meters because Geoapify
    # expects the radius in meters.
    radius_meters = int(
        miles * 1609.344
    )

    try:
        results = search_restaurants(
            cuisine=cuisine,
            location=location,
            radius=radius_meters,
            max_results=limit,
        )

        # Add search settings to the response
        results["search_radius_miles"] = miles
        results["result_limit"] = limit

        return results

    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        )

    except Exception as error:
        print(
            "Restaurant search error:",
            error,
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to search restaurants",
        )