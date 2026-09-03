import re
from app.extraction.compliance_fields import extract_compliance_fields

# ================================================================
# SETTINGS
# ================================================================

HIGH_CONFIDENCE = 0.80


# ================================================================
# HELPERS
# ================================================================

def make_field(value=None, confidence=0.0):

    if value is None:
        status = "NOT_DETECTED"

    elif confidence >= HIGH_CONFIDENCE:
        status = "DETECTED"

    else:
        status = "UNCERTAIN"

    return {
        "value": value,
        "confidence": round(float(confidence), 3),
        "status": status
    }


def normalize_text(text):

    return re.sub(
        r"[^a-z0-9]",
        "",
        text.lower()
    )


def get_center_y(box):

    return (
        box[1] + box[3]
    ) / 2


def get_center_x(box):

    return (
        box[0] + box[2]
    ) / 2


def clean_spaces(text):

    return re.sub(
        r"\s+",
        " ",
        text
    ).strip()
def split_ingredients(text):

    parts = []
    current = []
    depth = 0

    for char in text:

        if char == "(":
            depth += 1

        elif char == ")" and depth > 0:
            depth -= 1

        # Split only when comma/semicolon is OUTSIDE parentheses
        if char in [",", ";"] and depth == 0:

            part = "".join(current).strip()

            if part:
                parts.append(part)

            current = []

        else:
            current.append(char)

    # Add final part
    final_part = "".join(current).strip()

    if final_part:
        parts.append(final_part)

    return parts


# ================================================================
# PRODUCT NAME
# ================================================================

def extract_product_name(ocr_results):

    """
    Generic product-name/brand heuristic.

    Looks for large, high-confidence, short text rather than
    hardcoding Parle-G, Lay's, Head & Shoulders, etc.
    """

    excluded_words = [
        "ingredient",
        "nutrition",
        "manufacturer",
        "manufactured",
        "marketed",
        "consumer",
        "address",
        "private",
        "limited",
        "pvt",
        "ltd",
        "net qty",
        "net weight",
        "net volume",
        "mrp",
        "batch",
        "use before",
        "best before",
        "directions",
        "caution",
        "allergen",
        "energy",
        "protein",
        "carbohydrate",
        "sodium",
        "shampoo - surfactant",
        "proprietary food"
    ]

    candidates = []

    for item in ocr_results:

        text = clean_spaces(
            item["text"]
        )

        confidence = float(
            item["confidence"]
        )

        box = item["box"]

        if confidence < 0.75:
            continue

        if len(text) < 3 or len(text) > 45:
            continue

        lowered = text.lower()

        if any(
            word in lowered
            for word in excluded_words
        ):
            continue

        # Needs actual alphabetic characters
        if not re.search(
            r"[A-Za-z]",
            text
        ):
            continue

        height = max(
            1,
            box[3] - box[1]
        )

        width = max(
            1,
            box[2] - box[0]
        )

        # Large text is usually product/brand text.
        score = (
            height * 3
            + min(width, 500) * 0.05
            + confidence * 50
        )

        candidates.append(
            (
                score,
                item
            )
        )

    if not candidates:
        return make_field()

    candidates.sort(
        key=lambda x: x[0],
        reverse=True
    )

    selected = candidates[0][1]

    return make_field(
        clean_spaces(
            selected["text"]
        ),
        selected["confidence"]
    )


# ================================================================
# NET QUANTITY
# ================================================================

def extract_net_quantity(ocr_results):

    result = {
        "value": None,
        "unit": None,
        "label_detected": False,
        "confidence": 0.0,
        "status": "NOT_DETECTED"
    }

    label_pattern = re.compile(
        r"\b("
        r"NET\s*WEIGHT|"
        r"NET\s*WT|"
        r"NET\s*QTY|"
        r"NETQTY|"
        r"NET\s*VOLUME|"
        r"NET\s*CONTENT"
        r")\b",
        re.IGNORECASE
    )

    quantity_pattern = re.compile(
        r"(\d+(?:\.\d+)?)\s*"
        r"(kg|g|ml|l)\b",
        re.IGNORECASE
    )

    # First: check value on same line
    for item in ocr_results:

        text = clean_spaces(item["text"])

        if not label_pattern.search(text):
            continue

        confidence = float(item["confidence"])

        # Label exists
        result["label_detected"] = True
        result["confidence"] = round(confidence, 3)
        result["status"] = "VALUE_NOT_DETECTED"

        # Example:
        # NET WEIGHT: 55g + 10g EXTRA = 65g
        final_match = re.search(
            r"=\s*(\d+(?:\.\d+)?)\s*(kg|g|ml|l)\b",
            text,
            re.IGNORECASE
        )

        if final_match:

            return {
                "value": float(final_match.group(1)),
                "unit": final_match.group(2).lower(),
                "label_detected": True,
                "confidence": round(confidence, 3),
                "status": (
                    "DETECTED"
                    if confidence >= HIGH_CONFIDENCE
                    else "UNCERTAIN"
                )
            }

        matches = quantity_pattern.findall(text)

        if matches:

            value, unit = matches[-1]

            return {
                "value": float(value),
                "unit": unit.lower(),
                "label_detected": True,
                "confidence": round(confidence, 3),
                "status": (
                    "DETECTED"
                    if confidence >= HIGH_CONFIDENCE
                    else "UNCERTAIN"
                )
            }

    # Second: find quantity near the label
    for label_item in ocr_results:

        label_text = clean_spaces(label_item["text"])

        if not label_pattern.search(label_text):
            continue

        label_box = label_item["box"]
        label_y = get_center_y(label_box)

        candidates = []

        for item in ocr_results:

            if item is label_item:
                continue

            text = clean_spaces(item["text"])

            match = quantity_pattern.search(text)

            if not match:
                continue

            box = item["box"]

            y_distance = abs(
                get_center_y(box) - label_y
            )

            if y_distance > 100:
                continue

            x_distance = abs(
                box[0] - label_box[2]
            )

            score = (
                y_distance * 3
                + x_distance
            )

            candidates.append(
                (
                    score,
                    item,
                    match
                )
            )

        if candidates:

            candidates.sort(
                key=lambda x: x[0]
            )

            _, selected, match = candidates[0]

            confidence = float(
                selected["confidence"]
            )

            return {
                "value": float(match.group(1)),
                "unit": match.group(2).lower(),
                "label_detected": True,
                "confidence": round(confidence, 3),
                "status": (
                    "DETECTED"
                    if confidence >= HIGH_CONFIDENCE
                    else "UNCERTAIN"
                )
            }

    return result

# ================================================================
# COMPANY DETECTION
# ================================================================

def is_company_text(text):

    company_pattern = re.compile(
        r"\b("
        r"PVT\.?\s*LTD\.?|"
        r"PRIVATE\s+LIMITED|"
        r"LIMITED|"
        r"LTD\.?|"
        r"PRODUCTS|"
        r"HOLDINGS|"
        r"INDUSTRIES|"
        r"FOODS|"
        r"ENTERPRISES|"
        r"CORPORATION|"
        r"COMPANY"
        r")\b",
        re.IGNORECASE
    )

    return bool(
        company_pattern.search(text)
    )


def extract_company_candidates(ocr_results):

    candidates = []

    seen = set()

    for item in ocr_results:

        text = clean_spaces(
            item["text"]
        )

        if not is_company_text(text):
            continue

        key = normalize_text(text)

        if key in seen:
            continue

        seen.add(key)

        candidates.append(
            make_field(
                text,
                item["confidence"]
            )
        )

    return candidates


# ================================================================
# COMPANY ROLES
# ================================================================

def extract_company_roles(ocr_results):

    results = []

    role_patterns = {

        "manufacturer": [
            r"MANUFACTURED\s*BY",
            r"MFD\.?\s*BY",
            r"MFG\.?\s*BY",

            # OCR variants such as:
            # Mtg. & MkL by
            r"MTG\.?\s*&\s*MKL\.?\s*BY",

            r"MFG\.?\s*&\s*MKT\.?\s*BY"
        ],

        "manufactured_for": [
            r"MANUFACTURED\s*FOR"
        ],

        "packer": [
            r"PACKED\s*BY",
            r"PACKER"
        ],

        "importer": [
            r"IMPORTED\s*BY",
            r"IMPORTER"
        ],

        "marketer": [
            r"MARKETED\s*BY",
            r"MKT\.?\s*BY"
        ]
    }

    used = set()

    for role, patterns in role_patterns.items():

        for anchor in ocr_results:

            text = clean_spaces(
                anchor["text"]
            )

            matched_pattern = None

            for pattern in patterns:

                if re.search(
                    pattern,
                    text,
                    re.IGNORECASE
                ):

                    matched_pattern = pattern
                    break

            if matched_pattern is None:
                continue

            # ------------------------------------------------
            # Try company name on same OCR line
            # ------------------------------------------------

            split = re.split(
                matched_pattern,
                text,
                maxsplit=1,
                flags=re.IGNORECASE
            )

            if len(split) > 1:

                inline_value = clean_spaces(
                    split[1].lstrip(" :.-")
                )

                if (
                    len(inline_value) >= 4
                    and is_company_text(inline_value)
                ):

                    key = (
                        role,
                        normalize_text(
                            inline_value
                        )
                    )

                    if key not in used:

                        used.add(key)

                        results.append({
                            "role": role,
                            "value": inline_value,
                            "confidence": round(
                                float(
                                    anchor[
                                        "confidence"
                                    ]
                                ),
                                3
                            ),
                            "status": (
                                "DETECTED"
                                if float(
                                    anchor[
                                        "confidence"
                                    ]
                                ) >= HIGH_CONFIDENCE
                                else "UNCERTAIN"
                            )
                        })

                    continue

            # ------------------------------------------------
            # Otherwise find nearest company line
            # ------------------------------------------------

            anchor_box = anchor["box"]

            anchor_y = get_center_y(
                anchor_box
            )

            anchor_x = get_center_x(
                anchor_box
            )

            candidates = []

            for item in ocr_results:

                if item is anchor:
                    continue

                candidate_text = clean_spaces(
                    item["text"]
                )

                if not is_company_text(
                    candidate_text
                ):
                    continue

                box = item["box"]

                vertical_distance = abs(
                    get_center_y(box)
                    - anchor_y
                )

                if vertical_distance > 180:
                    continue

                horizontal_distance = abs(
                    get_center_x(box)
                    - anchor_x
                )

                # Slight preference for text below anchor.
                below_penalty = (
                    0
                    if box[1] >= anchor_box[1]
                    else 50
                )

                score = (
                    vertical_distance * 2
                    + horizontal_distance
                    + below_penalty
                )

                candidates.append(
                    (
                        score,
                        item
                    )
                )

            if not candidates:
                continue

            candidates.sort(
                key=lambda x: x[0]
            )

            selected = candidates[0][1]

            value = clean_spaces(
                selected["text"]
            )

            key = (
                role,
                normalize_text(value)
            )

            if key in used:
                continue

            used.add(key)

            confidence = float(
                selected["confidence"]
            )

            results.append({
                "role": role,
                "value": value,
                "confidence": round(
                    confidence,
                    3
                ),
                "status": (
                    "DETECTED"
                    if confidence >= HIGH_CONFIDENCE
                    else "UNCERTAIN"
                )
            })

    return results


# ================================================================
# FSSAI
# ================================================================

def extract_fssai_numbers(ocr_results):

    results = []

    seen = set()

    # OCR can misread:
    #
    # Lic.No.
    # Lc.No.
    # Uc.No.
    #
    # Require the licence-style marker AND a 14-digit number.

    marker_pattern = re.compile(
        r"(?:"
        r"LIC|"
        r"LC|"
        r"UC"
        r")\.?\s*NO\.?",
        re.IGNORECASE
    )

    for item in ocr_results:

        text = clean_spaces(
            item["text"]
        )

        if not marker_pattern.search(text):
            continue

        numbers = re.findall(
            r"(?<!\d)(\d{14})(?!\d)",
            text
        )

        for number in numbers:

            if number in seen:
                continue

            seen.add(number)

            confidence = float(
                item["confidence"]
            )

            results.append({
                "value": number,
                "confidence": round(
                    confidence,
                    3
                ),
                "status": (
                    "DETECTED"
                    if confidence >= HIGH_CONFIDENCE
                    else "UNCERTAIN"
                )
            })

    return results


# ================================================================
# INGREDIENT BLOCK
# ================================================================

def extract_ingredients(ocr_results):

    heading_item = None

    sorted_items = sorted(
        ocr_results,
        key=lambda item: (
            item["box"][1],
            item["box"][0]
        )
    )

    # Find INGREDIENTS heading
    for item in sorted_items:

        if re.search(
            r"\bINGREDIENTS?\b",
            item["text"],
            re.IGNORECASE
        ):
            heading_item = item
            break

    if heading_item is None:
        return []

    start_y = heading_item["box"][1]

    # Define approximate ingredient column
    heading_box = heading_item["box"]

    column_left = heading_box[0] - 50
    column_right = heading_box[2] + 150

    section_stop_patterns = [
        r"\bNUTRITION",
        r"\bALLERGEN",
        r"\bCAUTION",
        r"\bDIRECTIONS",
        r"\bWARNING",
        r"\bMANUFACTURED",
        r"\bMFD\b",
        r"\bMRP\b",
        r"\bNET\s*(?:QTY|WEIGHT|VOLUME)"
    ]

    fragments = []
    confidences = []

    for item in sorted_items:

        box = item["box"]

        item_center_x = (
            box[0] + box[2]
        ) / 2

        # Ignore unrelated columns
        if not (
            column_left
            <= item_center_x
            <= column_right
        ):
            continue

        if box[1] < start_y:
            continue

        # Don't let ingredient section grow forever
        if box[1] - start_y > 350:
            break

        text = clean_spaces(
            item["text"]
        )

        # Stop when a new section begins
        if (
            item is not heading_item
            and any(
                re.search(
                    pattern,
                    text,
                    re.IGNORECASE
                )
                for pattern in section_stop_patterns
            )
        ):
            break

        # Remove the INGREDIENTS label itself
        if item is heading_item:

            text = re.sub(
                r"^.*?\bINGREDIENTS?\s*:?",
                "",
                text,
                flags=re.IGNORECASE
            ).strip()

        if text:

            fragments.append(text)

            confidences.append(
                float(item["confidence"])
            )

    if not fragments:
        return []

    combined = " ".join(
        fragments
    )
    parts = [
    clean_spaces(part)
    for part in split_ingredients(combined)
    if clean_spaces(part)
    ]

    if not parts:
        parts = [combined]

    average_confidence = (
        sum(confidences) / len(confidences)
        if confidences
        else 0.0
    )

    return [
        make_field(
            part,
            average_confidence
        )
        for part in parts
    ]
def extract_best_before(ocr_results):

    # More specific patterns first
    label_patterns = [
        r"MFD\.?\s*&\s*USE\s*BY",
        r"MFG\.?\s*&\s*USE\s*BY",
        r"BEST\s*BEFORE",
        r"USE\s*BEFORE",
        r"USE\s*BY",
        r"EXPIRY",
        r"EXP\.?\s*DATE"
    ]

    result = {
        "value": None,
        "label_detected": False,
        "confidence": 0.0,
        "status": "NOT_DETECTED"
    }

    for item in ocr_results:

        text = clean_spaces(
            item["text"]
        )

        matched_pattern = None

        for pattern in label_patterns:

            if re.search(
                pattern,
                text,
                re.IGNORECASE
            ):
                matched_pattern = pattern
                break

        if matched_pattern is None:
            continue

        confidence = float(
            item["confidence"]
        )

        # Label exists, but value may still be missing
        result = {
            "value": None,
            "label_detected": True,
            "confidence": round(confidence, 3),
            "status": "VALUE_NOT_DETECTED"
        }

        # Remove declaration label
        remaining_text = re.sub(
            matched_pattern,
            "",
            text,
            count=1,
            flags=re.IGNORECASE
        )

        remaining_text = remaining_text.strip(
            " :-./"
        )

        # Only mark DETECTED if meaningful shelf-life/date
        # information remains after the label
        if (
            remaining_text
            and re.search(
                r"\d|MONTH|YEAR|DAY|FROM",
                remaining_text,
                re.IGNORECASE
            )
        ):

            return {
                "value": text,
                "label_detected": True,
                "confidence": round(confidence, 3),
                "status": (
                    "DETECTED"
                    if confidence >= HIGH_CONFIDENCE
                    else "UNCERTAIN"
                )
            }

    return result


# ================================================================
# MRP
# ================================================================

def extract_mrp(ocr_results):

    result = {
        "value": None,
        "currency": "INR",
        "confidence": 0.0,
        "status": "NOT_DETECTED"
    }

    for item in ocr_results:

        text = clean_spaces(
            item["text"]
        )

        if not re.search(
            r"\bMRP\b",
            text,
            re.IGNORECASE
        ):
            continue

        # Don't mistake:
        # "#MRP INCL. OF ALL TAXES: SEE PACKAGE."
        # for an actual numeric price.

        match = re.search(
            r"(?:₹|RS\.?|INR)\s*"
            r"(\d+(?:\.\d{1,2})?)",
            text,
            re.IGNORECASE
        )

        if match:

            confidence = float(
                item["confidence"]
            )

            return {
                "value": float(
                    match.group(1)
                ),
                "currency": "INR",
                "confidence": round(
                    confidence,
                    3
                ),
                "status": (
                    "DETECTED"
                    if confidence >= HIGH_CONFIDENCE
                    else "UNCERTAIN"
                )
            }

    return result


# ================================================================
# MANUFACTURING / PACKING DATE
# ================================================================

def extract_date_field(
    ocr_results,
    label_patterns
):

    date_pattern = re.compile(
        r"("
        r"\d{1,2}[/-]\d{4}"
        r"|"
        r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}"
        r"|"
        r"(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)"
        r"[A-Z]*[\s-]+\d{2,4}"
        r")",
        re.IGNORECASE
    )

    for item in ocr_results:

        text = clean_spaces(
            item["text"]
        )

        if not any(
            re.search(
                pattern,
                text,
                re.IGNORECASE
            )
            for pattern in label_patterns
        ):
            continue

        date_match = date_pattern.search(
            text
        )

        if date_match:

            return make_field(
                date_match.group(1),
                item["confidence"]
            )

    return make_field()


# ================================================================
# CONSUMER CARE
# ================================================================

def extract_consumer_care(ocr_results):

    result = {
        "phone": [],
        "email": [],
        "website": []
    }

    seen_phone = set()
    seen_email = set()
    seen_website = set()

    for item in ocr_results:

        text = clean_spaces(
            item["text"]
        )

        confidence = float(
            item["confidence"]
        )

        # ------------------------------------------------
        # PHONE
        # ------------------------------------------------

        phone_patterns = [
            # Toll-free:
            # 1800-202-1364
            r"(?<!\d)"
            r"1800[\s-]*\d{2,3}[\s-]*\d{4}"
            r"(?!\d)"
        ]

        for pattern in phone_patterns:

            for match in re.findall(
                pattern,
                text
            ):

                cleaned = re.sub(
                    r"\s+",
                    "",
                    match
                )

                if cleaned in seen_phone:
                    continue

                seen_phone.add(
                    cleaned
                )

                result["phone"].append(
                    make_field(
                        cleaned,
                        confidence
                    )
                )

        # ------------------------------------------------
        # EMAIL
        # ------------------------------------------------

        emails = re.findall(
            r"[A-Z0-9._%+-]+"
            r"@[A-Z0-9.-]+"
            r"\.[A-Z]{2,}",
            text,
            re.IGNORECASE
        )

        email_ranges = []

        for email_match in re.finditer(
            r"[A-Z0-9._%+-]+"
            r"@[A-Z0-9.-]+"
            r"\.[A-Z]{2,}",
            text,
            re.IGNORECASE
        ):

            email_ranges.append(
                email_match.span()
            )

        for email in emails:

            email = email.lower()

            if email in seen_email:
                continue

            seen_email.add(
                email
            )

            result["email"].append(
                make_field(
                    email,
                    confidence
                )
            )

        # ------------------------------------------------
        # WEBSITE
        # ------------------------------------------------

        # Remove email addresses before searching for domains.
        website_text = re.sub(
            r"[A-Z0-9._%+-]+"
            r"@[A-Z0-9.-]+"
            r"\.[A-Z]{2,}",
            " ",
            text,
            flags=re.IGNORECASE
        )

        websites = re.findall(
            r"(?:https?://)?"
            r"(?:www\.)?"
            r"[A-Z0-9-]+"
            r"(?:\.[A-Z0-9-]+)+"
            r"\.(?:com|in|org|net)",
            website_text,
            re.IGNORECASE
        )

        for website in websites:

            website = website.lower()

            if website in seen_website:
                continue

            seen_website.add(
                website
            )

            result["website"].append(
                make_field(
                    website,
                    confidence
                )
            )

    return result


# ================================================================
# NUTRITION
# ================================================================

def extract_nutrition(ocr_results):

    nutrition = {}

    heading_item = None

    for item in ocr_results:

        if re.search(
            r"NUTRITION",
            item["text"],
            re.IGNORECASE
        ):

            heading_item = item
            break

    if heading_item is None:
        return nutrition

    start_y = heading_item["box"][1]

    nutrition_items = [
        item
        for item in ocr_results
        if (
            item["box"][1] >= start_y
            and item["box"][1] <= start_y + 500
        )
    ]

    labels = {

        "energy": [
            r"\bENERGY\b"
        ],

        "protein": [
            r"\bPROTEIN\b",
            r"\bPROTEN\b"
        ],

        "carbohydrate": [
            r"\bCARBOHYDRATE\b"
        ],

        "total_sugars": [
            r"TOTAL\s*SUGAR",
            r"TOTAR\s*SUGER"
        ],

        "added_sugars": [
            r"ADDED\s*SUGAR"
        ],

        "total_fat": [
            r"TOTAL\s*FAT"
        ],

        "saturated_fat": [
            r"SATURATED\s*FAT"
        ],

        "trans_fat": [
            r"TRANS\s*FAT",
            r"TRANS\s*FAL"
        ],

        "sodium": [
            r"\bSODIUM\b"
        ]
    }

    used_items = set()

    value_pattern = re.compile(
        r"(\d+(?:\.\d+)?)\s*"
        r"(kcal|kj|mg|mcg|g|%)?",
        re.IGNORECASE
    )

    for field, patterns in labels.items():

        label_item = None

        for item in nutrition_items:

            text = clean_spaces(
                item["text"]
            )

            if any(
                re.search(
                    pattern,
                    text,
                    re.IGNORECASE
                )
                for pattern in patterns
            ):

                label_item = item
                break

        if label_item is None:
            continue

        label_box = label_item["box"]

        label_y = get_center_y(
            label_box
        )

        candidates = []

        for index, item in enumerate(
            nutrition_items
        ):

            if index in used_items:
                continue

            if item is label_item:
                continue

            text = clean_spaces(
                item["text"]
            )

            match = value_pattern.fullmatch(
                text
            )

            if not match:
                continue

            box = item["box"]

            # Value should normally be to the right.
            if box[0] < label_box[2]:
                continue

            vertical_distance = abs(
                get_center_y(box)
                - label_y
            )

            if vertical_distance > 25:
                continue

            horizontal_distance = (
                box[0]
                - label_box[2]
            )

            score = (
                vertical_distance * 4
                + horizontal_distance
            )

            candidates.append(
                (
                    score,
                    index,
                    item,
                    match
                )
            )

        if not candidates:
            continue

        candidates.sort(
            key=lambda x: x[0]
        )

        _, selected_index, selected_item, match = (
            candidates[0]
        )

        used_items.add(
            selected_index
        )

        confidence = float(
            selected_item["confidence"]
        )

        value = float(
            match.group(1)
        )

        unit = match.group(2)

        nutrition[field] = {
            "value": value,
            "unit": (
                unit.lower()
                if unit
                else None
            ),
            "confidence": round(
                confidence,
                3
            ),
            "status": (
                "DETECTED"
                if confidence >= HIGH_CONFIDENCE
                else "UNCERTAIN"
            )
        }

    return nutrition


# ================================================================
# MAIN EXTRACTOR
# ================================================================

def extract_fields(ocr_results):

    company_roles = extract_company_roles(
        ocr_results
    )

    manufacturer = make_field()

    for role in company_roles:

        if role["role"] == "manufacturer":

            manufacturer = make_field(
                role["value"],
                role["confidence"]
            )

            break

    product = {

        "product_name":
            extract_product_name(
                ocr_results
            ),

        "net_weight":
            extract_net_quantity(
                ocr_results
            ),

        "manufacturer":
            manufacturer,

        "manufacturer_candidates":
            extract_company_candidates(
                ocr_results
            ),

        "company_roles":
            company_roles,

        "fssai_numbers":
            extract_fssai_numbers(
                ocr_results
            ),

        "ingredients":
            extract_ingredients(
                ocr_results
            ),

        "best_before":
            extract_best_before(
                ocr_results
            ),

        "mrp":
            extract_mrp(
                ocr_results
            ),

        "manufacturing_date":
            extract_date_field(
                ocr_results,
                [
                    r"MFG\.?\s*DATE",
                    r"MFD\.?\s*DATE",
                    r"MANUFACTURING\s*DATE",
                    r"MANUFACTURED\s*ON"
                ]
            ),

        "packing_date":
            extract_date_field(
                ocr_results,
                [
                    r"PACKING\s*DATE",
                    r"PACKED\s*ON",
                    r"PKD\.?\s*DATE"
                ]
            ),

        "consumer_care":
            extract_consumer_care(
                ocr_results
            ),

        "nutrition":
            extract_nutrition(
                ocr_results
            )
    }

    compliance_fields = extract_compliance_fields(
    ocr_results
)

    return product