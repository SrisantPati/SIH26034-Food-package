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

    # For now, return only the original OCR result.
    # This keeps testing fast.
    return original_results