import os
import re
import cv2
import tempfile

from difflib import SequenceMatcher
from paddleocr import PaddleOCR


# ================================================================
# PADDLE OCR
# ================================================================

ocr = PaddleOCR(
    lang="en",

    text_detection_model_name="PP-OCRv5_mobile_det",
    text_recognition_model_name="PP-OCRv5_mobile_rec",

    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=False,

    enable_mkldnn=False,
)

# ================================================================
# SETTINGS
# ================================================================

MIN_OCR_CONFIDENCE = 0.30

# Whole image second pass
FULL_IMAGE_SCALE = 1.25

# Crop/region OCR scale
TILE_SCALE = 2.0

# Only perform tiled OCR on reasonably large images
TILE_MIN_SIZE = 99999


# ================================================================
# IMAGE ENHANCEMENT
# ================================================================

def enhance_image(image, scale=1.0):
    """
    Upscale and enhance an image without converting it to
    black/white.

    Keeping colour information is useful for product packaging.
    """

    processed = image.copy()

    # ------------------------------------------------
    # UPSCALE
    # ------------------------------------------------

    if scale != 1.0:

        processed = cv2.resize(
            processed,
            None,
            fx=scale,
            fy=scale,
            interpolation=cv2.INTER_CUBIC
        )

    # ------------------------------------------------
    # CONTRAST ENHANCEMENT USING CLAHE
    # ------------------------------------------------

    lab = cv2.cvtColor(
        processed,
        cv2.COLOR_BGR2LAB
    )

    l_channel, a_channel, b_channel = cv2.split(lab)

    clahe = cv2.createCLAHE(
        clipLimit=2.0,
        tileGridSize=(8, 8)
    )

    l_channel = clahe.apply(l_channel)

    enhanced_lab = cv2.merge(
        (
            l_channel,
            a_channel,
            b_channel
        )
    )

    processed = cv2.cvtColor(
        enhanced_lab,
        cv2.COLOR_LAB2BGR
    )

    # ------------------------------------------------
    # LIGHT SHARPENING
    # ------------------------------------------------

    blurred = cv2.GaussianBlur(
        processed,
        (0, 0),
        1.2
    )

    processed = cv2.addWeighted(
        processed,
        1.5,
        blurred,
        -0.5,
        0
    )

    return processed


# ================================================================
# SAVE TEMPORARY IMAGE
# ================================================================

def save_temp_image(image):

    temp_file = tempfile.NamedTemporaryFile(
        suffix=".png",
        delete=False
    )

    temp_path = temp_file.name

    temp_file.close()

    cv2.imwrite(
        temp_path,
        image
    )

    return temp_path


# ================================================================
# RUN ONE OCR PASS
# ================================================================

def run_ocr_pass(
    image,
    source,
    scale=1.0,
    x_offset=0,
    y_offset=0
):

    temp_path = save_temp_image(image)

    extracted = []

    try:

        result = ocr.predict(
            temp_path
        )

        for page in result:

            data = page.json

            res = data.get(
                "res",
                {}
            )

            texts = res.get(
                "rec_texts",
                []
            )

            scores = res.get(
                "rec_scores",
                []
            )

            boxes = res.get(
                "rec_boxes",
                []
            )

            for text, score, box in zip(
                texts,
                scores,
                boxes
            ):

                text = str(text).strip()

                confidence = float(score)

                if not text:
                    continue

                if confidence < MIN_OCR_CONFIDENCE:
                    continue

                # PaddleOCR versions may return either
                # NumPy arrays or normal lists.
                if hasattr(box, "tolist"):
                    box = box.tolist()
                else:
                    box = list(box)

                if len(box) != 4:
                    continue

                # ------------------------------------------------
                # MAP BOX BACK TO ORIGINAL IMAGE
                # ------------------------------------------------

                x1 = int(
                    round(
                        box[0] / scale
                    )
                ) + x_offset

                y1 = int(
                    round(
                        box[1] / scale
                    )
                ) + y_offset

                x2 = int(
                    round(
                        box[2] / scale
                    )
                ) + x_offset

                y2 = int(
                    round(
                        box[3] / scale
                    )
                ) + y_offset

                extracted.append({
                    "text": text,

                    "confidence": round(
                        confidence,
                        3
                    ),

                    "box": [
                        x1,
                        y1,
                        x2,
                        y2
                    ],

                    "source": source
                })

    finally:

        if os.path.exists(temp_path):

            os.remove(
                temp_path
            )

    return extracted


# ================================================================
# TEXT NORMALIZATION
# ================================================================

def normalize_text(text):

    return re.sub(
        r"[^a-z0-9]",
        "",
        text.lower()
    )


# ================================================================
# BOX IOU
# ================================================================

def calculate_iou(box1, box2):

    x_left = max(
        box1[0],
        box2[0]
    )

    y_top = max(
        box1[1],
        box2[1]
    )

    x_right = min(
        box1[2],
        box2[2]
    )

    y_bottom = min(
        box1[3],
        box2[3]
    )

    if (
        x_right <= x_left
        or y_bottom <= y_top
    ):
        return 0.0

    intersection = (
        (x_right - x_left)
        * (y_bottom - y_top)
    )

    area1 = (
        (box1[2] - box1[0])
        * (box1[3] - box1[1])
    )

    area2 = (
        (box2[2] - box2[0])
        * (box2[3] - box2[1])
    )

    union = (
        area1
        + area2
        - intersection
    )

    if union <= 0:
        return 0.0

    return intersection / union


# ================================================================
# TEXT SIMILARITY
# ================================================================

def text_similarity(text1, text2):

    text1 = normalize_text(text1)
    text2 = normalize_text(text2)

    if not text1 or not text2:
        return 0.0

    return SequenceMatcher(
        None,
        text1,
        text2
    ).ratio()


# ================================================================
# MERGE OCR RESULTS
# ================================================================

def merge_results(results):

    """
    Merge detections produced by multiple OCR passes.

    If two OCR results describe approximately the same text
    in approximately the same location, keep the higher
    confidence result.
    """

    merged = []

    # Start with strongest results first
    sorted_results = sorted(
        results,
        key=lambda item: item["confidence"],
        reverse=True
    )

    for candidate in sorted_results:

        duplicate_found = False

        for existing in merged:

            iou = calculate_iou(
                candidate["box"],
                existing["box"]
            )

            similarity = text_similarity(
                candidate["text"],
                existing["text"]
            )

            # Strong spatial + textual similarity
            if (
                iou >= 0.45
                and similarity >= 0.80
            ):

                duplicate_found = True
                break

        if not duplicate_found:

            merged.append(
                candidate
            )

    # Restore approximate reading order
    merged.sort(
        key=lambda item: (
            item["box"][1],
            item["box"][0]
        )
    )

    return merged


# ================================================================
# CREATE OVERLAPPING REGIONS
# ================================================================

def create_tiles(image):

    height, width = image.shape[:2]

    # Two overlapping horizontal zones
    x_ranges = [
        (
            0,
            int(width * 0.60)
        ),
        (
            int(width * 0.40),
            width
        )
    ]

    # Two overlapping vertical zones
    y_ranges = [
        (
            0,
            int(height * 0.60)
        ),
        (
            int(height * 0.40),
            height
        )
    ]

    tiles = []

    tile_number = 0

    for y1, y2 in y_ranges:

        for x1, x2 in x_ranges:

            crop = image[
                y1:y2,
                x1:x2
            ]

            tiles.append({
                "image": crop,
                "x_offset": x1,
                "y_offset": y1,
                "number": tile_number
            })

            tile_number += 1

    return tiles

def enhance_declaration_crop(
    image,
    scale=3.0
):
    """
    Enhancement specifically for faint variable
    information such as batch number, dates,
    price and net quantity.
    """

    # Convert to grayscale
    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY
    )

    # Upscale
    gray = cv2.resize(
        gray,
        None,
        fx=scale,
        fy=scale,
        interpolation=cv2.INTER_CUBIC
    )

    # Improve local contrast
    clahe = cv2.createCLAHE(
        clipLimit=3.0,
        tileGridSize=(8, 8)
    )

    gray = clahe.apply(gray)

    # Sharpen faint printed characters
    blurred = cv2.GaussianBlur(
        gray,
        (0, 0),
        1.0
    )

    sharpened = cv2.addWeighted(
        gray,
        2.0,
        blurred,
        -1.0,
        0
    )

    # PaddleOCR works better consistently
    # with a 3-channel image
    processed = cv2.cvtColor(
        sharpened,
        cv2.COLOR_GRAY2BGR
    )

    return processed

def run_targeted_declaration_ocr(
    image,
    original_results
):
    """
    Run a second OCR pass only around important declaration
    labels whose values may be too small for full-image OCR.

    Targets:
    - UNIT SALE PRICE
    - B.NO / BATCH
    - MFD / USE BY
    - NET QTY
    """

    target_patterns = [
    r"^\s*UNIT\s*SALE\s*PRICE\b",

    r"^\s*PER\s*PACK\s*/?\s*B\.?\s*NO\.?",

    r"^\s*MFD\s*&?\s*USE\s*BY\b",

    r"^\s*NET\s*(?:QTY|QUANTITY|WT|WEIGHT)\b",

    # Generic batch/lot label ONLY if it starts the line
    r"^\s*(?:BATCH(?:\s*NO\.?)?|B\.?\s*NO\.?|LOT(?:\s*NO\.?)?)"
    r"\s*[:\-]?"
    ]

    target_items = []

    for item in original_results:

        text = item["text"]

        if any(
            re.search(
                pattern,
                text,
                re.IGNORECASE
            )
            for pattern in target_patterns
        ):
            target_items.append(item)

    if not target_items:
        return []

    # ------------------------------------------------
    # Find one region containing all target labels
    # ------------------------------------------------

    min_x = min(
        item["box"][0]
        for item in target_items
    )

    min_y = min(
        item["box"][1]
        for item in target_items
    )

    max_x = max(
        item["box"][2]
        for item in target_items
    )

    max_y = max(
        item["box"][3]
        for item in target_items
    )

    image_height, image_width = image.shape[:2]

    # Extra space around labels because the actual
    # printed values may be beside or below them.
    padding_left = 30
    padding_right = 260
    padding_top = 25
    padding_bottom = 50


    x1 = max(
        0,
        min_x - padding_left
    )

    y1 = max(
        0,
        min_y - padding_top
    )

    x2 = min(
        image_width,
        max_x + padding_right
    )

    y2 = min(
        image_height,
        max_y + padding_bottom
    )

    crop = image[
    y1:y2,
    x1:x2
    ]

    cv2.imwrite(
        "app/uploads/declaration_crop_raw.jpg",
        crop
    )

    if crop.size == 0:
        return []

    
    # ------------------------------------------------
    # Enlarge only this small region
    # ------------------------------------------------
    scale = 3.0

    enhanced_crop = enhance_declaration_crop(
        crop,
        scale=scale
    )
    cv2.imwrite(
    "app/uploads/declaration_crop_debug.jpg",
    enhanced_crop
    )

    print(
        "Targeted OCR: declaration panel..."
    )

    results = run_ocr_pass(
        image=enhanced_crop,
        source="declaration_crop",
        scale=scale,
        x_offset=x1,
        y_offset=y1
    )

    print(
        f"Targeted OCR: {len(results)} detections"
    )

    return results

# ================================================================
# MAIN PUBLIC FUNCTION
# ================================================================

def extract_text(image_path: str):

    image = cv2.imread(image_path)

    if image is None:
        raise ValueError(
            f"Could not read image: {image_path}"
        )

    print("OCR Pass 1: Original image...")

    original_results = run_ocr_pass(
        image=image,
        source="original",
        scale=1.0
    )

    print(
    f"Pass 1: {len(original_results)} detections"
    )

    # ------------------------------------------------
    # TARGETED OCR FOR SMALL DECLARATION VALUES
    # ------------------------------------------------

    targeted_results = run_targeted_declaration_ocr(
        image,
        original_results
    )

    # Combine full-image + targeted detections
    all_results = (
        original_results
        + targeted_results
    )

    merged_results = merge_results(
        all_results
    )

    print(
        f"Final OCR detections: {len(merged_results)}"
    )

    return merged_results