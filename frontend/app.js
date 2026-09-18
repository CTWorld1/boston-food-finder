const API_URL =
    "http://127.0.0.1:8000";


const searchButton =
    document.getElementById(
        "searchButton"
    );


const cuisineInput =
    document.getElementById(
        "cuisineInput"
    );


const locationInput =
    document.getElementById(
        "locationInput"
    );


const milesInput =
    document.getElementById(
        "milesInput"
    );


const limitInput =
    document.getElementById(
        "limitInput"
    );


const statusContainer =
    document.getElementById(
        "statusContainer"
    );


const statusText =
    document.getElementById(
        "status"
    );


const statusIcon =
    document.getElementById(
        "statusIcon"
    );


const resultsContainer =
    document.getElementById(
        "results"
    );


const loading =
    document.getElementById(
        "loading"
    );


/* ======================================
   EVENTS
====================================== */

searchButton.addEventListener(
    "click",
    handleSearch
);


cuisineInput.addEventListener(
    "keydown",
    handleEnter
);


locationInput.addEventListener(
    "keydown",
    handleEnter
);


milesInput.addEventListener(
    "keydown",
    handleEnter
);


limitInput.addEventListener(
    "keydown",
    handleEnter
);


function handleEnter(event) {

    if (event.key === "Enter") {

        handleSearch();

    }

}


/* ======================================
   HANDLE SEARCH
====================================== */

async function handleSearch() {

    const cuisine =
        cuisineInput.value.trim();


    const location =
        locationInput.value.trim();


    const miles =
        parseFloat(
            milesInput.value
        );


    const limit =
        parseInt(
            limitInput.value,
            10
        );


    if (!cuisine) {

        showStatus(
            "Please enter a cuisine.",
            false
        );

        return;

    }


    if (!location) {

        showStatus(
            "Please enter a location.",
            false
        );

        return;

    }


    if (
        !Number.isFinite(miles) ||
        miles <= 0
    ) {

        showStatus(
            "Please enter a valid distance in miles.",
            false
        );

        return;

    }


    if (miles > 50) {

        showStatus(
            "Search distance cannot be greater than 50 miles.",
            false
        );

        return;

    }


    if (
        !Number.isInteger(limit) ||
        limit < 1
    ) {

        showStatus(
            "Please enter a valid result limit.",
            false
        );

        return;

    }


    if (limit > 20) {

        showStatus(
            "Maximum result limit is 20.",
            false
        );

        return;

    }


    await loadRestaurantResults(
        cuisine,
        location,
        miles,
        limit
    );

}


/* ======================================
   LOAD RESTAURANTS
====================================== */

async function loadRestaurantResults(
    cuisine,
    location,
    miles = 5,
    limit = 10
) {

    resultsContainer.innerHTML = "";


    statusContainer.classList.add(
        "hidden"
    );


    loading.classList.remove(
        "hidden"
    );


    searchButton.disabled =
        true;


    const url =
        `${API_URL}/restaurants` +
        `?cuisine=${encodeURIComponent(cuisine)}` +
        `&location=${encodeURIComponent(location)}` +
        `&miles=${encodeURIComponent(miles)}` +
        `&limit=${encodeURIComponent(limit)}`;


    try {

        const response =
            await fetch(url);


        if (!response.ok) {

            let message =
                "Restaurant search failed.";


            try {

                const errorData =
                    await response.json();


                if (errorData.detail) {

                    message =
                        errorData.detail;

                }

            }

            catch {

                // Keep default error message

            }


            throw new Error(
                message
            );

        }


        const data =
            await response.json();


        displayRestaurants(
            data.restaurants
        );


        showStatus(
            `Found ${data.count} ${data.cuisine} restaurant(s) within ${miles} miles of ${location}.`,
            true
        );

    }

    catch (error) {

        console.error(
            "Restaurant search error:",
            error
        );


        showStatus(
            error.message,
            false
        );


        displayNoResults();

    }

    finally {

        loading.classList.add(
            "hidden"
        );


        searchButton.disabled =
            false;

    }

}


/* ======================================
   DISPLAY RESTAURANTS
====================================== */

function displayRestaurants(
    restaurants
) {

    resultsContainer.innerHTML = "";


    if (
        !restaurants ||
        restaurants.length === 0
    ) {

        displayNoResults();

        return;

    }


    restaurants.forEach(
        restaurant => {

            const card =
                createRestaurantCard(
                    restaurant
                );


            resultsContainer.appendChild(
                card
            );

        }
    );

}


/* ======================================
   CREATE RESTAURANT CARD
====================================== */

function createRestaurantCard(
    restaurant
) {

    const card =
        document.createElement(
            "article"
        );


    card.className =
        "restaurant-card";


    const safeName =
        escapeHTML(
            restaurant.name ||
            "Restaurant"
        );


    const safeAddress =
        escapeHTML(
            restaurant.address ||
            "Address unavailable"
        );


    const distance =
        restaurant.distance_miles != null

            ? `${restaurant.distance_miles} mi`

            : "Distance unavailable";


    const price =
        restaurant.price &&
        restaurant.price !== "Not available"

            ? escapeHTML(
                restaurant.price
            )

            : "Price unavailable";


    const photoHTML =
        createPhotoHTML(
            restaurant,
            safeName
        );


    card.innerHTML = `

        ${photoHTML}


        <div class="card-content">


            <h2>
                ${safeName}
            </h2>


            <div class="address-row">

                <span class="address-icon">
                    📍
                </span>

                <p class="address">
                    ${safeAddress}
                </p>

            </div>


            <div class="card-details">


                <div class="detail-item">

                    <span class="detail-icon">
                        ↔
                    </span>

                    <span>
                        ${distance}
                    </span>

                </div>


                <div class="detail-item">

                    <span class="detail-icon">
                        $
                    </span>

                    <span>
                        ${price}
                    </span>

                </div>


            </div>


            <button
                class="map-button"
                type="button"
            >

                🗺️ View on Map

            </button>


        </div>

    `;


    const mapButton =
        card.querySelector(
            ".map-button"
        );


    mapButton.addEventListener(
        "click",
        () => {

            openRestaurantMap(
                restaurant
            );

        }
    );


    return card;

}


/* ======================================
   PHOTO
====================================== */

function createPhotoHTML(
    restaurant,
    safeName
) {

    const photo =
        restaurant.photo_url;


    if (
        photo &&
        photo !== "Not available" &&
        isValidHttpUrl(photo)
    ) {

        return `

            <img
                class="restaurant-photo"
                src="${photo}"
                alt="${safeName}"
                loading="lazy"
            >

        `;

    }


    /*
        Geoapify / OpenStreetMap often
        does not provide photos.

        This placeholder is intentionally
        shown instead.
    */

    return `

        <div class="no-photo">

            <div class="no-photo-icon">
                🍽️
            </div>

            <span>
                Restaurant
            </span>

        </div>

    `;

}


/* ======================================
   OPEN MAP
====================================== */

function openRestaurantMap(
    restaurant
) {

    const latitude =
        Number(
            restaurant.latitude
        );


    const longitude =
        Number(
            restaurant.longitude
        );


    if (
        !Number.isFinite(latitude) ||
        !Number.isFinite(longitude)
    ) {

        alert(
            "Map location is unavailable for this restaurant."
        );

        return;

    }


    const mapUrl =
        `https://www.openstreetmap.org/` +
        `?mlat=${latitude}` +
        `&mlon=${longitude}` +
        `#map=17/${latitude}/${longitude}`;


    window.open(
        mapUrl,
        "_blank",
        "noopener,noreferrer"
    );

}


/* ======================================
   STATUS
====================================== */

function showStatus(
    message,
    success
) {

    statusText.textContent =
        message;


    statusContainer.classList.remove(
        "hidden"
    );


    if (success) {

        statusIcon.textContent =
            "✓";


        statusContainer.style.background =
            "linear-gradient(90deg, #e3f2ea, #edf6f2)";


        statusContainer.style.color =
            "#173d32";


        statusIcon.style.background =
            "#3f8c70";

    }

    else {

        statusIcon.textContent =
            "!";


        statusContainer.style.background =
            "#fde9e6";


        statusContainer.style.color =
            "#842f29";


        statusIcon.style.background =
            "#d8554d";

    }

}


/* ======================================
   NO RESULTS
====================================== */

function displayNoResults() {

    resultsContainer.innerHTML = `

        <div class="no-results">

            <div class="no-results-icon">
                🍽️
            </div>

            <h2>
                No restaurants found
            </h2>

            <p>
                Try another cuisine,
                location, or search radius.
            </p>

        </div>

    `;

}


/* ======================================
   SAFETY HELPERS
====================================== */

function escapeHTML(value) {

    return String(value)

        .replaceAll(
            "&",
            "&amp;"
        )

        .replaceAll(
            "<",
            "&lt;"
        )

        .replaceAll(
            ">",
            "&gt;"
        )

        .replaceAll(
            '"',
            "&quot;"
        )

        .replaceAll(
            "'",
            "&#039;"
        );

}


function isValidHttpUrl(value) {

    try {

        const url =
            new URL(value);


        return (
            url.protocol === "http:" ||
            url.protocol === "https:"
        );

    }

    catch {

        return false;

    }

}