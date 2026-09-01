from PIL import Image, ImageDraw, ImageFont

from app.ocr.ocr_service import extract_text


# -----------------------------------------
# IMAGE PATH
# -----------------------------------------

image_path = "app/uploads/51wr9HQU0DL.jpg"

output_path = "app/uploads/ocr_debug.jpg"


# -----------------------------------------
# RUN OCR
# -----------------------------------------

print("Starting OCR...")

ocr_results = extract_text(image_path)

print(f"OCR detected {len(ocr_results)} text regions")


# -----------------------------------------
# OPEN IMAGE
# -----------------------------------------

image = Image.open(image_path).convert("RGB")

draw = ImageDraw.Draw(image)


# -----------------------------------------
# FONT
# -----------------------------------------

try:
    font = ImageFont.truetype("arial.ttf", 18)
except:
    font = ImageFont.load_default()


# -----------------------------------------
# DRAW OCR BOXES
# -----------------------------------------

for index, item in enumerate(ocr_results):

    text = item["text"]
    confidence = item["confidence"]
    box = item["box"]

    x1, y1, x2, y2 = box

    # Draw bounding box
    draw.rectangle(
        [x1, y1, x2, y2],
        outline="red",
        width=3
    )

    # Label
    label = f"{index}: {text} ({confidence:.2f})"

    draw.text(
    (x1, y1),
    str(index),
    fill="blue",
    font=font
)

# -----------------------------------------
# SAVE
# -----------------------------------------

image.save(output_path)

print("\nOCR DEBUG IMAGE SAVED:")
print(output_path)