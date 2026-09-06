import re
from difflib import SequenceMatcher


MATCH = "MATCH"
PARTIAL_MATCH = "PARTIAL_MATCH"
MISMATCH = "MISMATCH"

OCR_ONLY = "OCR_ONLY"
DATABASE_ONLY = "DATABASE_ONLY"

NOT_AVAILABLE = "NOT_AVAILABLE"


def normalize_text(text):

    if text is None:
        return ""

    text = str(text).lower()

    text = re.sub(
        r"[^a-z0-9]+",
        " ",
        text
    )

    return " ".join(
        text.split()
    )


def similarity(
    first,
    second
):

    first = normalize_text(
        first
    )

    second = normalize_text(
        second
    )

    if not first or not second:
        return 0.0

    return SequenceMatcher(
        None,
        first,
        second
    ).ratio()


def compare_text_field(
    ocr_value,
    database_value
):

    if (
        not ocr_value
        and
        not database_value
    ):
        return {
            "status": NOT_AVAILABLE,
            "similarity": None
        }

    if (
        ocr_value
        and
        not database_value
    ):
        return {
            "status": OCR_ONLY,
            "similarity": None
        }

    if (
        database_value
        and
        not ocr_value
    ):
        return {
            "status": DATABASE_ONLY,
            "similarity": None
        }

    score = similarity(
        ocr_value,
        database_value
    )

    if score >= 0.80:
        status = MATCH

    elif score >= 0.50:
        status = PARTIAL_MATCH

    else:
        status = MISMATCH

    return {
        "status": status,
        "similarity": round(
            score,
            3
        )
    }


def field_value(field):

    if not isinstance(
        field,
        dict
    ):
        return None

    return field.get(
        "value"
    )


def format_net_quantity(field):

    if not isinstance(
        field,
        dict
    ):
        return None

    value = field.get(
        "value"
    )

    unit = field.get(
        "unit"
    )

    if value is None:
        return None

    if unit:
        return f"{value} {unit}"

    return str(value)


def compare_product_data(
    ocr_product,
    database_product
):

    database_found = (
        database_product.get(
            "status"
        )
        ==
        "FOUND"
    )

    if not database_found:

        return {
            "status":
                "DATABASE_UNAVAILABLE",

            "brand": None,
            "food_name": None,
            "net_quantity": None
        }

    ocr_brand = field_value(
        ocr_product.get(
            "brand_name"
        )
    )

    ocr_food_name = field_value(
        ocr_product.get(
            "food_name"
        )
    )

    ocr_quantity = format_net_quantity(
        ocr_product.get(
            "net_weight"
        )
    )

    database_brand = (
        database_product.get(
            "brand_name"
        )
    )

    database_name = (
        database_product.get(
            "product_name"
        )
    )

    database_quantity = (
        database_product.get(
            "quantity"
        )
    )


    brand_check = compare_text_field(
        ocr_brand,
        database_brand
    )

    food_check = compare_text_field(
        ocr_food_name,
        database_name
    )

    quantity_check = compare_text_field(
        ocr_quantity,
        database_quantity
    )


    return {

        "status":
            "COMPARED",

        "brand": {
            "ocr": ocr_brand,
            "database":
                database_brand,
            **brand_check
        },

        "food_name": {
            "ocr": ocr_food_name,
            "database":
                database_name,
            **food_check
        },

        "net_quantity": {
            "ocr":
                ocr_quantity,
            "database":
                database_quantity,
            **quantity_check
        }
    }