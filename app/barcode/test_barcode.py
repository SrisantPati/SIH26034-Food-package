from app.barcode.barcode_scanner import scan_barcode


image_path = r"C:\Users\Srisant\product_compliance\app\uploads\lays1.jpg"


result = scan_barcode(
    image_path
)


print(
    "BARCODE RESULT:"
)

print(
    result
)