from app.ocr.ocr_service import extract_text
from app.extraction.extractor import extract_fields


print("TEST STARTED")

image_path = r"C:\Users\Srisant\product_compliance\app\uploads\71ur3Tat2VL.jpg"


print("Starting OCR...")

ocr_results = extract_text(image_path)

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
