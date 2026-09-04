COMPLIANT = "COMPLIANT"
NON_COMPLIANT = "NON_COMPLIANT"
REVIEW_REQUIRED = "REVIEW_REQUIRED"
CANNOT_DETERMINE = "CANNOT_DETERMINE"
NOT_APPLICABLE = "NOT_APPLICABLE"


def check_required_field(
    field,
    field_name
):
    """
    Convert a normal extracted field into a compliance result.
    """

    if field is None:
        return {
            "field": field_name,
            "status": CANNOT_DETERMINE,
            "reason": "No extraction result available."
        }

    extraction_status = field.get(
        "status"
    )

    value = field.get(
        "value"
    )

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
            "reason": "Declaration detected with low OCR confidence."
        }

    if extraction_status in [
        "VALUE_NOT_DETECTED",
        "NOT_DETECTED"
    ]:
        return {
            "field": field_name,
            "status": CANNOT_DETERMINE,
            "reason": (
                "Declaration could not be reliably "
                "verified from the image."
            )
        }

    return {
        "field": field_name,
        "status": REVIEW_REQUIRED,
        "reason": "Unable to verify automatically."
    }


def check_fssai_numbers(product):
    """
    Check whether at least one FSSAI licence /
    registration number was detected.
    """

    numbers = product.get(
        "fssai_numbers",
        []
    )

    if not numbers:
        return {
            "field": "FSSAI Licence Number",
            "status": CANNOT_DETERMINE,
            "reason": (
                "No FSSAI licence number "
                "could be detected."
            )
        }

    detected = [
        item
        for item in numbers
        if item.get("status") == "DETECTED"
    ]

    uncertain = [
        item
        for item in numbers
        if item.get("status") == "UNCERTAIN"
    ]

    if detected:
        return {
            "field": "FSSAI Licence Number",
            "status": COMPLIANT,
            "reason": (
                f"{len(detected)} FSSAI number(s) detected."
            )
        }

    if uncertain:
        return {
            "field": "FSSAI Licence Number",
            "status": REVIEW_REQUIRED,
            "reason": (
                "Possible FSSAI licence number detected "
                "with low OCR confidence."
            )
        }

    return {
        "field": "FSSAI Licence Number",
        "status": CANNOT_DETERMINE,
        "reason": (
            "FSSAI licence number could not "
            "be reliably verified."
        )
    }


def evaluate_basic_compliance(product):
    """
    Run the first basic compliance checks.

    This is NOT yet the final Legal Metrology +
    FSSAI compliance engine.
    """

    checks = []

    checks.append(
        check_required_field(
            product.get("food_name"),
            "Food Name"
        )
    )

    checks.append(
        check_required_field(
            product.get("net_weight"),
            "Net Quantity"
        )
    )

    checks.append(
        check_required_field(
            product.get("mrp"),
            "MRP"
        )
    )

    checks.append(
        check_required_field(
            product.get("manufacturer"),
            "Manufacturer / Responsible Business"
        )
    )

    checks.append(
        check_fssai_numbers(
            product
        )
    )

    return checks


def calculate_compliance_summary(checks):
    """
    Create a simple overall summary of the checks.
    """

    summary = {
        "total_checks": len(checks),
        "compliant": 0,
        "non_compliant": 0,
        "review_required": 0,
        "cannot_determine": 0,
        "not_applicable": 0,
    }

    for check in checks:

        status = check.get(
            "status"
        )

        if status == COMPLIANT:
            summary["compliant"] += 1

        elif status == NON_COMPLIANT:
            summary["non_compliant"] += 1

        elif status == REVIEW_REQUIRED:
            summary["review_required"] += 1

        elif status == CANNOT_DETERMINE:
            summary["cannot_determine"] += 1

        elif status == NOT_APPLICABLE:
            summary["not_applicable"] += 1

    return summary


def run_compliance_checks(product):
    """
    Main entry point for compliance checking.
    """

    checks = evaluate_basic_compliance(
        product
    )

    summary = calculate_compliance_summary(
        checks
    )

    return {
        "checks": checks,
        "summary": summary
    }