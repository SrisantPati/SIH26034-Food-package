from app.ocr.ocr_service import extract_text
from app.extraction.extractor import extract_fields

def debug_compliance_lines(ocr_results):

    keywords = [
        "net",
        "weight",
        "qty",
        "quantity",
        "mrp",
        "price",
        "best",
        "before",
        "mfg",
        "mfd",
        "manufact",
        "packed",
        "pkd",
        "batch",
        "lot",
    ]

    print("\n")
    print("=" * 70)
    print("COMPLIANCE OCR DEBUG")
    print("=" * 70)

    sorted_items = sorted(
        ocr_results,
        key=lambda item: (
            item["box"][1],
            item["box"][0]
        )
    )

    for i, item in enumerate(sorted_items):

        text = item["text"]

        if any(
            keyword in text.lower()
            for keyword in keywords
        ):

            print(f"\nINDEX: {i}")
            print(f"TEXT: {text}")
            print(f"CONFIDENCE: {item.get('confidence')}")
            print(f"BOX: {item.get('box')}")

            print("\nNearby BEFORE:")

            for j in range(
                max(0, i - 3),
                i
            ):
                print(
                    j,
                    sorted_items[j]["text"],
                    sorted_items[j]["box"]
                )

            print("\nNearby AFTER:")

            for j in range(
                i + 1,
                min(len(sorted_items), i + 6)
            ):
                print(
                    j,
                    sorted_items[j]["text"],
                    sorted_items[j]["box"]
                )

            print("-" * 70)
print("TEST STARTED")

image_path = r"C:\Users\Srisant\product_compliance\app\uploads\71ur3Tat2VL.jpg"

print("Starting OCR...")

ocr_results = extract_text(image_path)
debug_compliance_lines(ocr_results)
print("OCR FINISHED")

# Print raw OCR results
print("\n===== RAW OCR DATA =====")

for item in ocr_results:
    print(item)

print("\nStarting extraction...")

product = extract_fields(ocr_results)

print("EXTRACTION FINISHED")

print("\n===== EXTRACTED PRODUCT DATA =====")

for key, value in product.items():
    print(f"{key}: {value}")

print("TEST FINISHED")
