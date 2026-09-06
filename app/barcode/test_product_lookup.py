from app.barcode.product_lookup import lookup_product


barcode = "8901491000772"


result = lookup_product(
    barcode
)


print(
    "\nPRODUCT LOOKUP:"
)

print(
    result
)