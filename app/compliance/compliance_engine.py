COMPLIANT = "COMPLIANT"
NON_COMPLIANT = "NON_COMPLIANT"
REVIEW_REQUIRED = "REVIEW_REQUIRED"
CANNOT_DETERMINE = "CANNOT_DETERMINE"
NOT_APPLICABLE = "NOT_APPLICABLE"


# =========================================================
# GENERIC FIELD CHECK
# =========================================================

def check_required_field(field, field_name):

    if field is None:
        return {
            "field": field_name,
            "status": CANNOT_DETERMINE,
            "reason": "No extraction result available."
        }

    # Standard extractor field
    if isinstance(field, dict):

        extraction_status = field.get("status")
        value = field.get("value")

        if (
            extraction_status == "DETECTED"
            and value is not None
        ):
            return {
                "field": field_name,
                "status": COMPLIANT,
                "reason": "Required declaration detected."
            }

        if extraction_status == "UNCERTAIN":
            return {
                "field": field_name,
                "status": REVIEW_REQUIRED,
                "reason":
                    "Declaration detected with low OCR confidence."
            }

        if extraction_status in [
            "VALUE_NOT_DETECTED",
            "NOT_DETECTED"
        ]:
            return {
                "field": field_name,
                "status": CANNOT_DETERMINE,
                "reason":
                    "Declaration could not be reliably verified from the image."
            }

    # Raw text fallback
    if isinstance(field, str) and field.strip():

        return {
            "field": field_name,
            "status": COMPLIANT,
            "reason": "Required declaration detected."
        }

    return {
        "field": field_name,
        "status": CANNOT_DETERMINE,
        "reason":
            "Declaration could not be reliably verified from the image."
    }


# =========================================================
# FSSAI
# =========================================================

def check_fssai_numbers(product):

    numbers = product.get(
        "fssai_numbers",
        []
    )

    if not numbers:
        return {
            "field": "FSSAI Licence Number",
            "status": CANNOT_DETERMINE,
            "reason":
                "No FSSAI licence number could be detected."
        }

    detected = [
        item
        for item in numbers
        if isinstance(item, dict)
        and item.get("status") == "DETECTED"
    ]

    uncertain = [
        item
        for item in numbers
        if isinstance(item, dict)
        and item.get("status") == "UNCERTAIN"
    ]

    if detected:
        return {
            "field": "FSSAI Licence Number",
            "status": COMPLIANT,
            "reason":
                f"{len(detected)} FSSAI number(s) detected."
        }

    if uncertain:
        return {
            "field": "FSSAI Licence Number",
            "status": REVIEW_REQUIRED,
            "reason":
                "Possible FSSAI licence number detected with low OCR confidence."
        }

    return {
        "field": "FSSAI Licence Number",
        "status": CANNOT_DETERMINE,
        "reason":
            "FSSAI licence number could not be reliably verified."
    }


# =========================================================
# INGREDIENTS
# =========================================================

def check_ingredients(product):

    ingredients = product.get(
        "ingredients"
    )

    if not ingredients:
        return {
            "field": "Ingredients",
            "status": CANNOT_DETERMINE,
            "reason":
                "Ingredients declaration could not be detected."
        }

    # If extractor returns one normal field
    if isinstance(ingredients, dict):

        return check_required_field(
            ingredients,
            "Ingredients"
        )

    # If extractor returns a list
    if isinstance(ingredients, list):

        detected = 0
        uncertain = 0

        for item in ingredients:

            if isinstance(item, str):

                if item.strip():
                    detected += 1

            elif isinstance(item, dict):

                value = item.get("value")

                # Some ingredient extractor objects may
                # use text instead of value.
                if value is None:
                    value = item.get("text")

                if not value:
                    continue

                if item.get("status") == "UNCERTAIN":
                    uncertain += 1
                else:
                    detected += 1

        if detected > 0:
            return {
                "field": "Ingredients",
                "status": COMPLIANT,
                "reason":
                    "Ingredients declaration detected."
            }

        if uncertain > 0:
            return {
                "field": "Ingredients",
                "status": REVIEW_REQUIRED,
                "reason":
                    "Possible ingredients declaration detected with low confidence."
            }

    if isinstance(ingredients, str):

        if ingredients.strip():
            return {
                "field": "Ingredients",
                "status": COMPLIANT,
                "reason":
                    "Ingredients declaration detected."
            }

    return {
        "field": "Ingredients",
        "status": CANNOT_DETERMINE,
        "reason":
            "Ingredients declaration could not be reliably verified."
    }


# =========================================================
# NUTRITION
# =========================================================

def check_nutrition(product):

    nutrition = product.get(
        "nutrition"
    )

    if not nutrition:
        return {
            "field": "Nutrition Information",
            "status": CANNOT_DETERMINE,
            "reason":
                "Nutrition information could not be detected."
        }

    detected_fields = []
    uncertain_fields = []

    for nutrient_name, nutrient in nutrition.items():

        if not isinstance(
            nutrient,
            dict
        ):
            continue

        value = nutrient.get(
            "value"
        )

        if value is None:
            continue

        status = nutrient.get(
            "status"
        )

        if status == "UNCERTAIN":

            uncertain_fields.append(
                nutrient_name
            )

        else:

            detected_fields.append(
                nutrient_name
            )

    # Require several nutrition values so one random
    # number is not enough to mark the section verified.
    if len(detected_fields) >= 3:

        return {
            "field": "Nutrition Information",
            "status": COMPLIANT,
            "reason":
                f"{len(detected_fields)} nutrition values detected."
        }

    if (
        detected_fields
        or uncertain_fields
    ):

        return {
            "field": "Nutrition Information",
            "status": REVIEW_REQUIRED,
            "reason":
                "Only part of the nutrition declaration could be reliably detected."
        }

    return {
        "field": "Nutrition Information",
        "status": CANNOT_DETERMINE,
        "reason":
            "Nutrition declaration could not be reliably verified."
    }


# =========================================================
# CONSUMER CARE
# =========================================================

def count_extracted_values(data):
    """
    Recursively count detected and uncertain values.

    Works even if consumer_care has nested objects.
    """

    detected = 0
    uncertain = 0

    if data is None:
        return detected, uncertain

    if isinstance(data, str):

        if data.strip():
            detected += 1

        return detected, uncertain

    if isinstance(data, list):

        for item in data:

            d, u = count_extracted_values(
                item
            )

            detected += d
            uncertain += u

        return detected, uncertain

    if isinstance(data, dict):

        # Standard extracted field
        if "value" in data:

            value = data.get(
                "value"
            )

            if value not in [
                None,
                ""
            ]:

                if (
                    data.get("status")
                    == "UNCERTAIN"
                ):
                    uncertain += 1

                else:
                    detected += 1

            return detected, uncertain

        # Nested dictionary
        for value in data.values():

            d, u = count_extracted_values(
                value
            )

            detected += d
            uncertain += u

    return detected, uncertain


def check_consumer_care(product):

    consumer_care = product.get(
        "consumer_care"
    )

    if not consumer_care:

        return {
            "field": "Consumer Care Details",
            "status": CANNOT_DETERMINE,
            "reason":
                "Consumer care information could not be detected."
        }

    detected, uncertain = (
        count_extracted_values(
            consumer_care
        )
    )

    if detected >= 1:

        return {
            "field": "Consumer Care Details",
            "status": COMPLIANT,
            "reason":
                "Consumer contact information detected."
        }

    if uncertain >= 1:

        return {
            "field": "Consumer Care Details",
            "status": REVIEW_REQUIRED,
            "reason":
                "Possible consumer contact information detected but requires review."
        }

    return {
        "field": "Consumer Care Details",
        "status": CANNOT_DETERMINE,
        "reason":
            "Consumer care information could not be reliably verified."
    }


# =========================================================
# RESPONSIBLE BUSINESS
# =========================================================

def check_responsible_business(product):

    manufacturer = product.get(
        "manufacturer"
    )

    result = check_required_field(
        manufacturer,
        "Manufacturer / Responsible Business"
    )

    if result["status"] in [
        COMPLIANT,
        REVIEW_REQUIRED
    ]:
        return result

    # Manufacturer may have been detected under
    # another company role.
    company_roles = product.get(
        "company_roles",
        {}
    )

    detected, uncertain = (
        count_extracted_values(
            company_roles
        )
    )

    if detected:

        return {
            "field":
                "Manufacturer / Responsible Business",

            "status":
                COMPLIANT,

            "reason":
                "Responsible business information detected from company-role declaration."
        }

    # Candidates are not strong enough for automatic
    # compliance, but are useful for manual review.
    candidates = product.get(
        "manufacturer_candidates",
        []
    )

    candidate_detected, candidate_uncertain = (
        count_extracted_values(
            candidates
        )
    )

    if (
        candidate_detected
        or candidate_uncertain
    ):

        return {
            "field":
                "Manufacturer / Responsible Business",

            "status":
                REVIEW_REQUIRED,

            "reason":
                "Possible responsible business detected but the company role requires verification."
        }

    return result


# =========================================================
# BASIC COMPLIANCE CHECKS
# =========================================================

def check_allergens(product):

    allergens = product.get(
        "allergens"
    )

    if not allergens:

        return {
            "field":
                "Allergen Declaration",

            "status":
                CANNOT_DETERMINE,

            "reason":
                "Allergen declaration could not be verified from the image."
        }

    if isinstance(
        allergens,
        dict
    ):

        value = allergens.get(
            "value"
        )

        extraction_status = (
            allergens.get(
                "status"
            )
        )

        if (
            extraction_status
            == "DETECTED"
            and value
        ):

            return {
                "field":
                    "Allergen Declaration",

                "status":
                    COMPLIANT,

                "reason":
                    "Allergen declaration detected on the package."
            }

        if (
            extraction_status
            == "UNCERTAIN"
            and value
        ):

            return {
                "field":
                    "Allergen Declaration",

                "status":
                    REVIEW_REQUIRED,

                "reason":
                    "Possible allergen declaration detected with low OCR confidence."
            }

    return {
        "field":
            "Allergen Declaration",

        "status":
            CANNOT_DETERMINE,

        "reason":
            "Allergen declaration could not be reliably verified."
    }

def check_date_declaration(product):

    date_fields = [
        (
            "Manufacturing Date",
            product.get(
                "manufacturing_date"
            )
        ),

        (
            "Packing Date",
            product.get(
                "packing_date"
            )
        ),

        (
            "Best Before",
            product.get(
                "best_before"
            )
        )
    ]

    detected = []
    uncertain = []

    for name, field in date_fields:

        if not isinstance(
            field,
            dict
        ):
            continue

        value = field.get(
            "value"
        )

        if value is None:
            continue

        status = field.get(
            "status"
        )

        if status == "DETECTED":

            detected.append(
                name
            )

        elif status == "UNCERTAIN":

            uncertain.append(
                name
            )

    if detected:

        return {
            "field":
                "Date Declaration",

            "status":
                COMPLIANT,

            "reason":
                "Detected: "
                + ", ".join(
                    detected
                )
                + "."
        }

    if uncertain:

        return {
            "field":
                "Date Declaration",

            "status":
                REVIEW_REQUIRED,

            "reason":
                "Possible date declaration detected: "
                + ", ".join(
                    uncertain
                )
                + "."
        }

    return {
        "field":
            "Date Declaration",

        "status":
            CANNOT_DETERMINE,

        "reason":
            "Manufacturing, packing or best-before declaration could not be reliably verified."
    }

def evaluate_basic_compliance(product):

    checks = []

    # 1
    checks.append(
        check_required_field(
            product.get("food_name"),
            "Food Name"
        )
    )

    # 2
    checks.append(
        check_required_field(
            product.get("net_weight"),
            "Net Quantity"
        )
    )

    # 3
    checks.append(
        check_required_field(
            product.get("mrp"),
            "MRP"
        )
    )

    # 4
    checks.append(
        check_responsible_business(
            product
        )
    )

    # 5
    checks.append(
        check_fssai_numbers(
            product
        )
    )

    # 6
    checks.append(
        check_ingredients(
            product
        )
    )

    # 7
    checks.append(
        check_nutrition(
            product
        )
    )

    # 8
    checks.append(
        check_consumer_care(
            product
        )
    )
        # 9
    checks.append(
        check_date_declaration(
            product
        )
    )

    # 10
    checks.append(
        check_allergens(
            product
        )
    )
    return checks


# =========================================================
# SUMMARY
# =========================================================

def calculate_compliance_summary(
    checks
):

    summary = {
        "total_checks":
            len(checks),

        "compliant":
            0,

        "non_compliant":
            0,

        "review_required":
            0,

        "cannot_determine":
            0,

        "not_applicable":
            0
    }

    for check in checks:

        status = check.get(
            "status"
        )

        if status == COMPLIANT:

            summary[
                "compliant"
            ] += 1

        elif status == NON_COMPLIANT:

            summary[
                "non_compliant"
            ] += 1

        elif status == REVIEW_REQUIRED:

            summary[
                "review_required"
            ] += 1

        elif status == CANNOT_DETERMINE:

            summary[
                "cannot_determine"
            ] += 1

        elif status == NOT_APPLICABLE:

            summary[
                "not_applicable"
            ] += 1

    return summary


# =========================================================
# MAIN ENTRY POINT
# =========================================================

def run_compliance_checks(
    product
):

    checks = evaluate_basic_compliance(
        product
    )

    summary = calculate_compliance_summary(
        checks
    )

    return {
        "checks":
            checks,

        "summary":
            summary
    }