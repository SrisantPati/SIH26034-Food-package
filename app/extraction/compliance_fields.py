import re


# ---------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------

def clean_text(text):
    if not text:
        return ""

    text = text.strip()

    # Normalize repeated spaces
    text = re.sub(r"\s+", " ", text)

    return text


def sort_ocr_results(ocr_results):
    """
    Sort OCR boxes from top -> bottom, then left -> right.
    """
    return sorted(
        ocr_results,
        key=lambda item: (
            item["box"][1],
            item["box"][0]
        )
    )


def combine_ocr_text(ocr_results):
    """
    Creates one searchable OCR string.
    """
    sorted_items = sort_ocr_results(ocr_results)

    return "\n".join(
        clean_text(item["text"])
        for item in sorted_items
        if item.get("text")
    )


# ---------------------------------------------------------
# MRP EXTRACTION
# ---------------------------------------------------------

def extract_mrp(ocr_results):

    patterns = [
        r"\bMRP\b",
        r"\bM\.?\s*R\.?\s*P\.?\b",
        r"MAX(?:IMUM)?\s+RETAIL\s+PRICE",
        r"RETAIL\s+SALE\s+PRICE",
    ]

    sorted_items = sort_ocr_results(ocr_results)

    for i, item in enumerate(sorted_items):

        text = clean_text(item["text"])

        if not any(
            re.search(pattern, text, re.IGNORECASE)
            for pattern in patterns
        ):
            continue

        # First try price from same OCR box
        price = find_price(text)

        if price is not None:
            return {
                "value": price,
                "currency": "INR",
                "raw_text": text,
                "confidence": item.get("confidence")
            }

        # Search nearby OCR lines
        nearby_items = sorted_items[i:i + 4]

        for nearby in nearby_items:

            nearby_text = clean_text(nearby["text"])

            price = find_price(nearby_text)

            if price is not None:
                return {
                    "value": price,
                    "currency": "INR",
                    "raw_text": nearby_text,
                    "confidence": nearby.get("confidence")
                }

    return None


def find_price(text):

    # ₹20, Rs 20, Rs.20, INR 20
    patterns = [
        r"₹\s*(\d+(?:\.\d{1,2})?)",
        r"\bRS\.?\s*(\d+(?:\.\d{1,2})?)",
        r"\bINR\s*(\d+(?:\.\d{1,2})?)",
        r"\bMRP\s*[:\-]?\s*(\d+(?:\.\d{1,2})?)",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass

    return None


# ---------------------------------------------------------
# BATCH / LOT / CODE EXTRACTION
# ---------------------------------------------------------

def extract_batch_number(ocr_results):

    patterns = [
        r"\bBATCH\s*(?:NO\.?|NUMBER)?\s*[:\-]?\s*([A-Z0-9\-\/]+)",
        r"\bLOT\s*(?:NO\.?|NUMBER)?\s*[:\-]?\s*([A-Z0-9\-\/]+)",
        r"\bB\.?\s*NO\.?\s*[:\-]?\s*([A-Z0-9\-\/]+)",
        r"\bBATCH\s*CODE\s*[:\-]?\s*([A-Z0-9\-\/]+)",
    ]

    sorted_items = sort_ocr_results(ocr_results)

    for i, item in enumerate(sorted_items):

        text = clean_text(item["text"])

        for pattern in patterns:

            match = re.search(
                pattern,
                text,
                re.IGNORECASE
            )

            if match:

                value = match.group(1).strip()

                # Prevent false values such as "NO"
                if len(value) >= 2:

                    return {
                        "value": value,
                        "raw_text": text,
                        "confidence": item.get("confidence")
                    }

        # Handle OCR split:
        #
        # Batch No:
        # A12345

        if re.search(
            r"\b(BATCH|LOT|B\.?\s*NO)\b",
            text,
            re.IGNORECASE
        ):

            if i + 1 < len(sorted_items):

                next_item = sorted_items[i + 1]

                candidate = clean_text(
                    next_item["text"]
                )

                if re.fullmatch(
                    r"[A-Z0-9\-\/]{2,30}",
                    candidate,
                    re.IGNORECASE
                ):

                    return {
                        "value": candidate,
                        "raw_text": text + " " + candidate,
                        "confidence": next_item.get("confidence")
                    }

    return None


# ---------------------------------------------------------
# DATE EXTRACTION
# ---------------------------------------------------------

DATE_VALUE_PATTERN = (
    r"(?:"
    r"\d{1,2}[\/\-.]\d{1,2}[\/\-.]\d{2,4}"
    r"|"
    r"\d{1,2}[\/\-.]\d{2,4}"
    r"|"
    r"(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|SEPT|OCT|NOV|DEC)"
    r"[A-Z]*[\s\-\/]*\d{2,4}"
    r"|"
    r"\d{1,2}\s+"
    r"(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|SEPT|OCT|NOV|DEC)"
    r"[A-Z]*\s+\d{2,4}"
    r")"
)


def extract_date_after_label(
    ocr_results,
    label_patterns
):

    sorted_items = sort_ocr_results(ocr_results)

    for i, item in enumerate(sorted_items):

        text = clean_text(item["text"])

        if not any(
            re.search(
                pattern,
                text,
                re.IGNORECASE
            )
            for pattern in label_patterns
        ):
            continue

        # Try same OCR line
        match = re.search(
            DATE_VALUE_PATTERN,
            text,
            re.IGNORECASE
        )

        if match:

            return {
                "value": match.group(0),
                "raw_text": text,
                "confidence": item.get("confidence")
            }

        # Try next 3 OCR blocks
        for nearby in sorted_items[
            i + 1:i + 4
        ]:

            nearby_text = clean_text(
                nearby["text"]
            )

            match = re.search(
                DATE_VALUE_PATTERN,
                nearby_text,
                re.IGNORECASE
            )

            if match:

                return {
                    "value": match.group(0),
                    "raw_text": (
                        text + " " + nearby_text
                    ),
                    "confidence": nearby.get(
                        "confidence"
                    )
                }

    return None


def extract_manufacture_date(ocr_results):

    patterns = [
        r"\bMFD\b",
        r"\bMFG\b",
        r"\bMANUFACTURED\s*(?:ON)?\b",
        r"\bDATE\s+OF\s+MANUFACTURE\b",
        r"\bPACKED\s*(?:ON)?\b",
        r"\bPKD\b",
        r"\bPACKING\s+DATE\b",
    ]

    return extract_date_after_label(
        ocr_results,
        patterns
    )


def extract_expiry_date(ocr_results):

    patterns = [
        r"\bEXP\b",
        r"\bEXPIRY\b",
        r"\bEXPIRATION\b",
        r"\bUSE\s*BY\b",
    ]

    return extract_date_after_label(
        ocr_results,
        patterns
    )


def extract_best_before(ocr_results):

    patterns = [
        r"\bBEST\s+BEFORE\b",
        r"\bBBE\b",
    ]

    sorted_items = sort_ocr_results(
        ocr_results
    )

    for i, item in enumerate(sorted_items):

        text = clean_text(item["text"])

        if not any(
            re.search(
                pattern,
                text,
                re.IGNORECASE
            )
            for pattern in patterns
        ):
            continue

        # First check if an actual date exists
        date_match = re.search(
            DATE_VALUE_PATTERN,
            text,
            re.IGNORECASE
        )

        if date_match:

            return {
                "value": date_match.group(0),
                "type": "date",
                "raw_text": text,
                "confidence": item.get(
                    "confidence"
                )
            }

        # Handle:
        # BEST BEFORE 4 MONTHS FROM PACKAGING
        duration_match = re.search(
            r"BEST\s+BEFORE\s+"
            r"(\d+|ONE|TWO|THREE|FOUR|FIVE|SIX|"
            r"SEVEN|EIGHT|NINE|TEN|ELEVEN|TWELVE)"
            r"\s+"
            r"(DAY|DAYS|MONTH|MONTHS|YEAR|YEARS)",
            text,
            re.IGNORECASE
        )

        if duration_match:

            return {
                "value": duration_match.group(0),
                "type": "duration",
                "raw_text": text,
                "confidence": item.get(
                    "confidence"
                )
            }

        # Check next lines too
        combined = text

        for nearby in sorted_items[
            i + 1:i + 3
        ]:

            combined += " " + clean_text(
                nearby["text"]
            )

        duration_match = re.search(
            r"BEST\s+BEFORE\s+"
            r"(\d+|ONE|TWO|THREE|FOUR|FIVE|SIX|"
            r"SEVEN|EIGHT|NINE|TEN|ELEVEN|TWELVE)"
            r"\s+"
            r"(DAY|DAYS|MONTH|MONTHS|YEAR|YEARS)",
            combined,
            re.IGNORECASE
        )

        if duration_match:

            return {
                "value": duration_match.group(0),
                "type": "duration",
                "raw_text": combined,
                "confidence": item.get(
                    "confidence"
                )
            }

    return None


# ---------------------------------------------------------
# CONSUMER CARE
# ---------------------------------------------------------

def extract_consumer_care(ocr_results):

    full_text = combine_ocr_text(
        ocr_results
    )

    result = {
        "phone": None,
        "email": None
    }

    # Email
    email_match = re.search(
        r"\b[A-Z0-9._%+\-]+"
        r"@[A-Z0-9.\-]+"
        r"\.[A-Z]{2,}\b",
        full_text,
        re.IGNORECASE
    )

    if email_match:
        result["email"] = email_match.group(0)

    # Indian phone / toll free patterns
    phone_patterns = [
        r"\b1800[\s\-]?\d{3}[\s\-]?\d{4}\b",
        r"\b1860[\s\-]?\d{3}[\s\-]?\d{4}\b",
        r"\b\d{10}\b",
        r"\+91[\s\-]?\d{10}\b",
    ]

    for pattern in phone_patterns:

        match = re.search(
            pattern,
            full_text
        )

        if match:

            result["phone"] = match.group(0)

            break

    if (
        result["phone"] is None
        and result["email"] is None
    ):
        return None

    return result


# ---------------------------------------------------------
# MANUFACTURER / PACKER
# ---------------------------------------------------------

def extract_business_details(ocr_results):

    sorted_items = sort_ocr_results(
        ocr_results
    )

    labels = {
        "manufacturer": [
            r"\bMANUFACTURED\s+BY\b",
            r"\bMFD\.?\s+BY\b",
        ],

        "packer": [
            r"\bPACKED\s+BY\b",
            r"\bPKD\.?\s+BY\b",
        ],

        "marketer": [
            r"\bMARKETED\s+BY\b",
            r"\bMKT\.?\s+BY\b",
        ],

        "importer": [
            r"\bIMPORTED\s+BY\b",
            r"\bIMPORTER\b",
        ]
    }

    result = {
        "manufacturer": None,
        "packer": None,
        "marketer": None,
        "importer": None
    }

    for business_type, patterns in labels.items():

        for i, item in enumerate(
            sorted_items
        ):

            text = clean_text(
                item["text"]
            )

            if not any(
                re.search(
                    pattern,
                    text,
                    re.IGNORECASE
                )
                for pattern in patterns
            ):
                continue

            collected = [text]

            # Collect next few OCR lines
            for nearby in sorted_items[
                i + 1:i + 5
            ]:

                collected.append(
                    clean_text(
                        nearby["text"]
                    )
                )

            result[business_type] = {
                "raw_text": " ".join(
                    collected
                ),
                "confidence": item.get(
                    "confidence"
                )
            }

            break

    return result


# ---------------------------------------------------------
# MASTER FUNCTION
# ---------------------------------------------------------

def extract_compliance_fields(
    ocr_results
):

    return {

        "mrp":
            extract_mrp(
                ocr_results
            ),

        "batch":
            extract_batch_number(
                ocr_results
            ),

        "dates": {

            "manufacture_or_packaging":
                extract_manufacture_date(
                    ocr_results
                ),

            "expiry_or_use_by":
                extract_expiry_date(
                    ocr_results
                ),

            "best_before":
                extract_best_before(
                    ocr_results
                ),
        },

        "consumer_care":
            extract_consumer_care(
                ocr_results
            ),

        "business_details":
            extract_business_details(
                ocr_results
            )
    }