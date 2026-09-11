import requests


OPEN_FOOD_FACTS_URL = (
    "https://world.openfoodfacts.org"
    "/api/v3/product/{barcode}"
)


def empty_lookup(
    barcode=None,
    status="NOT_FOUND"
):
    return {
        "barcode": barcode,
        "status": status,
        "source": "Open Food Facts",
        "brand_name": None,
        "product_name": None,
        "quantity": None,
        "ingredients": None,
        "nutrition": {},
        "image_url": None,
    }


def lookup_product(barcode):
    """
    Lookup product information using barcode.

    Barcode database data is used only as
    reference/cross-check information.
    """

    if not barcode:
        return empty_lookup(
            status="NO_BARCODE"
        )

    fields = ",".join([
        "code",
        "product_name",
        "brands",
        "quantity",
        "product_quantity",
        "product_quantity_unit",
        "ingredients_text",
        "nutriments",
        "image_front_url",
    ])

    headers = {
        "User-Agent": (
            "PackCheck/1.0 "
            "(SIH26034 compliance prototype)"
        )
    }

    url = OPEN_FOOD_FACTS_URL.format(
        barcode=barcode
    )

    try:
        response = requests.get(
            url,
            params={
                "fields": fields,
                "lc": "en",
                "cc": "in",
            },
            headers=headers,
            timeout=3
        )

    except requests.RequestException as error:

        print(
            "Product lookup error:",
            error
        )

        return empty_lookup(
            barcode,
            "LOOKUP_ERROR"
        )

    if response.status_code == 404:

        return empty_lookup(
            barcode,
            "NOT_FOUND"
        )

    if not response.ok:

        print(
            "Open Food Facts HTTP error:",
            response.status_code
        )

        return empty_lookup(
            barcode,
            "LOOKUP_ERROR"
        )

    try:
        data = response.json()

    except ValueError:

        return empty_lookup(
            barcode,
            "LOOKUP_ERROR"
        )

    product = data.get(
        "product"
    )

    if not product:

        return empty_lookup(
            barcode,
            "NOT_FOUND"
        )

    nutriments = product.get(
        "nutriments",
        {}
    )

    nutrition = {
        "energy_kcal": get_nutrient(
            nutriments,
            "energy-kcal"
        ),

        "protein": get_nutrient(
            nutriments,
            "proteins"
        ),

        "carbohydrate": get_nutrient(
            nutriments,
            "carbohydrates"
        ),

        "total_sugars": get_nutrient(
            nutriments,
            "sugars"
        ),

        "total_fat": get_nutrient(
            nutriments,
            "fat"
        ),

        "saturated_fat": get_nutrient(
            nutriments,
            "saturated-fat"
        ),

        "sodium": get_nutrient(
            nutriments,
            "sodium"
        ),
    }

    # Remove completely empty nutrient entries
    nutrition = {
        key: value
        for key, value
        in nutrition.items()
        if value is not None
    }

    return {
        "barcode": barcode,

        "status": "FOUND",

        "source":
            "Open Food Facts",

        "brand_name":
            product.get(
                "brands"
            ),

        "product_name":
            product.get(
                "product_name"
            ),

        "quantity":
            product.get(
                "quantity"
            ),

        "product_quantity":
            product.get(
                "product_quantity"
            ),

        "product_quantity_unit":
            product.get(
                "product_quantity_unit"
            ),

        "ingredients":
            product.get(
                "ingredients_text"
            ),

        "nutrition":
            nutrition,

        "image_url":
            product.get(
                "image_front_url"
            ),
    }


def get_nutrient(
    nutriments,
    nutrient
):
    """
    Read the per-100g nutrient value from OFF.
    """

    value = nutriments.get(
        f"{nutrient}_100g"
    )

    if value is None:
        return None

    unit = nutriments.get(
        f"{nutrient}_unit"
    )

    return {
        "value": value,
        "unit": unit
    }