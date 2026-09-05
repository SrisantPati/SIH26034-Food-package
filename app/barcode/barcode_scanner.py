import cv2
import zxingcpp


def empty_result():
    return {
        "value": None,
        "format": None,
        "status": "NOT_DETECTED"
    }


def decode_image(image, source):
    """
    Try to decode barcodes from one image version.
    """

    try:

        results = zxingcpp.read_barcodes(
            image
        )

    except Exception as error:

        print(
            f"Barcode error ({source}):",
            error
        )

        return None


    if not results:
        return None


    for result in results:

        value = result.text.strip()

        if not value:
            continue


        barcode_format = getattr(
            result.format,
            "name",
            str(result.format)
        )


        return {
            "value": value,
            "format": barcode_format,
            "status": "DETECTED",
            "source": source
        }


    return None


def scan_barcode(image_path):
    """
    Decode an EAN / UPC / other barcode
    from a product image.

    Tries several lightweight image versions.
    """

    image = cv2.imread(
        image_path
    )


    if image is None:

        print(
            "Barcode scanner: image could not be loaded"
        )

        return empty_result()


    # =====================================
    # PASS 1 - ORIGINAL
    # =====================================

    result = decode_image(
        image,
        "original"
    )


    if result:

        print(
            "Barcode detected:",
            result["value"]
        )

        return result


    # =====================================
    # PASS 2 - GRAYSCALE
    # =====================================

    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY
    )


    result = decode_image(
        gray,
        "grayscale"
    )


    if result:

        print(
            "Barcode detected:",
            result["value"]
        )

        return result


    # =====================================
    # PASS 3 - 2X UPSCALE
    # =====================================

    enlarged = cv2.resize(
        image,
        None,
        fx=2.0,
        fy=2.0,
        interpolation=cv2.INTER_CUBIC
    )


    result = decode_image(
        enlarged,
        "2x"
    )


    if result:

        print(
            "Barcode detected:",
            result["value"]
        )

        return result


    # =====================================
    # PASS 4 - GRAYSCALE + 2X
    # =====================================

    gray_enlarged = cv2.resize(
        gray,
        None,
        fx=2.0,
        fy=2.0,
        interpolation=cv2.INTER_CUBIC
    )


    result = decode_image(
        gray_enlarged,
        "grayscale_2x"
    )


    if result:

        print(
            "Barcode detected:",
            result["value"]
        )

        return result


    print(
        "Barcode scanner: no barcode detected"
    )

    return empty_result()

