import cv2


def scan_barcode(image_path):
    """
    Detect and decode barcode from an image.

    Returns:
    {
        "value": "...",
        "format": "...",
        "status": "DETECTED"
    }

    or NOT_DETECTED.
    """

    image = cv2.imread(
        image_path
    )

    if image is None:
        return {
            "value": None,
            "format": None,
            "status": "NOT_DETECTED"
        }


    detector = cv2.barcode_BarcodeDetector()


    try:

        ok, decoded_info, decoded_type, points = (
            detector.detectAndDecodeWithType(
                image
            )
        )

    except Exception:

        return {
            "value": None,
            "format": None,
            "status": "NOT_DETECTED"
        }


    if not ok:
        return {
            "value": None,
            "format": None,
            "status": "NOT_DETECTED"
        }


    if not decoded_info:
        return {
            "value": None,
            "format": None,
            "status": "NOT_DETECTED"
        }


    for value, barcode_type in zip(
        decoded_info,
        decoded_type
    ):

        value = value.strip()

        if not value:
            continue


        return {
            "value": value,
            "format": barcode_type,
            "status": "DETECTED"
        }


    return {
        "value": None,
        "format": None,
        "status": "NOT_DETECTED"
    }