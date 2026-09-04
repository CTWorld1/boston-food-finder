from results_pipeline import search_restaurants


def main():
    print()
    print("================================")
    print("      Boston Food Finder")
    print("================================")
    print()

    cuisine = input("Enter cuisine: ").strip()
    location = input(
        "Enter location (example: Boston, MA): "
    ).strip()

    print()
    print(
        f"Searching for {cuisine} restaurants "
        f"near {location}..."
    )
    print()

    try:
        results = search_restaurants(
            cuisine=cuisine,
            location=location,
        )

    except Exception as error:
        print("Error:", error)
        return

    restaurants = results["restaurants"]

    if not restaurants:
        print("No matching restaurants found.")
        return

    print(
        f"Found {len(restaurants)} "
        f"{cuisine} restaurant(s)."
    )

    for number, restaurant in enumerate(
        restaurants,
        start=1,
    ):
        print()
        print("=" * 60)
        print(f"Restaurant #{number}")
        print("=" * 60)

        print("Name:", restaurant["name"])
        print("Address:", restaurant["address"])
        print("Cuisine:", restaurant["cuisine"])
        print("Hours:", restaurant["hours"])
        print("Phone:", restaurant["phone"])
        print("Website:", restaurant["website"])
        print("Photo:", restaurant["photo_url"])
        print("Rating:", restaurant["rating"])
        print("Price:", restaurant["price"])

        print(
            "Coordinates:",
            restaurant["latitude"],
            restaurant["longitude"],
        )


if __name__ == "__main__":
    main()