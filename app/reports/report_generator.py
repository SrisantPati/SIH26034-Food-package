from pathlib import Path

from reportlab.lib import colors

from reportlab.lib.pagesizes import A4

from reportlab.lib.styles import (
    getSampleStyleSheet,
    ParagraphStyle
)

from reportlab.lib.enums import (
    TA_CENTER
)

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak
)


REPORT_DIR = (
    Path(__file__).resolve().parent
    / "generated"
)

REPORT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


def safe_text(value):

    if value is None:
        return "-"

    # Standard ReportLab fonts are safest
    # with plain ASCII for this prototype.
    return (
        str(value)
        .replace("₹", "INR ")
        .replace("↔", "<->")
        .encode(
            "ascii",
            errors="replace"
        )
        .decode("ascii")
    )


def field_value(
    field
):

    if isinstance(
        field,
        dict
    ):

        value = field.get(
            "value"
        )

        if value is None:
            return "Not detected"

        unit = field.get(
            "unit"
        )

        if unit:
            return (
                f"{value} {unit}"
            )

        return str(
            value
        )

    if field is None:
        return "Not detected"

    return str(
        field
    )


def create_report(
    scan
):

    scan_id = scan["id"]

    output_path = (
        REPORT_DIR
        / f"packcheck_report_{scan_id}.pdf"
    )


    document = SimpleDocTemplate(

        str(output_path),

        pagesize=A4,

        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )


    styles = (
        getSampleStyleSheet()
    )


    title_style = ParagraphStyle(

        "PackCheckTitle",

        parent=styles["Title"],

        alignment=TA_CENTER,

        fontSize=22,

        spaceAfter=6
    )


    subtitle_style = ParagraphStyle(

        "Subtitle",

        parent=styles["Normal"],

        alignment=TA_CENTER,

        fontSize=10,

        textColor=colors.grey,

        spaceAfter=20
    )


    heading_style = (
        styles["Heading2"]
    )


    normal = (
        styles["Normal"]
    )


    story = []


    # =========================================
    # HEADER
    # =========================================

    story.append(

        Paragraph(
            "PackCheck",
            title_style
        )
    )

    story.append(

        Paragraph(
            "Packaged Commodity Compliance Report",
            subtitle_style
        )
    )


    # =========================================
    # REPORT INFORMATION
    # =========================================

    basic_data = [

        [
            "Report ID",
            safe_text(
                scan["id"]
            )
        ],

        [
            "Date",
            safe_text(
                scan["created_at"]
            )
        ],

        [
            "Product",
            safe_text(
                scan.get(
                    "product_name"
                )
            )
        ],

        [
            "Barcode",
            safe_text(
                scan.get(
                    "barcode"
                )
            )
        ],

        [
            "Overall Assessment",
            safe_text(
                scan.get(
                    "overall_status"
                )
            )
        ]
    ]


    info_table = Table(

        basic_data,

        colWidths=[
            150,
            330
        ]
    )


    info_table.setStyle(

        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (0, -1),
                colors.whitesmoke
            ),

            (
                "FONTNAME",
                (0, 0),
                (0, -1),
                "Helvetica-Bold"
            ),

            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.lightgrey
            ),

            (
                "PADDING",
                (0, 0),
                (-1, -1),
                8
            )
        ])
    )


    story.append(
        info_table
    )

    story.append(
        Spacer(
            1,
            22
        )
    )


    # =========================================
    # EXTRACTED PRODUCT INFORMATION
    # =========================================

    story.append(

        Paragraph(
            "Extracted Product Information",
            heading_style
        )
    )


    product = scan.get(
        "product",
        {}
    )


    extracted_rows = [
        [
            "Field",
            "Detected Value"
        ],

        [
            "Brand",
            safe_text(
                field_value(
                    product.get(
                        "brand_name"
                    )
                )
            )
        ],

        [
            "Food Name",
            safe_text(
                field_value(
                    product.get(
                        "food_name"
                    )
                )
            )
        ],

        [
            "Net Quantity",
            safe_text(
                field_value(
                    product.get(
                        "net_weight"
                    )
                )
            )
        ],

        [
            "MRP",
            safe_text(
                field_value(
                    product.get(
                        "mrp"
                    )
                )
            )
        ],

        [
            "Manufacturer",
            safe_text(
                field_value(
                    product.get(
                        "manufacturer"
                    )
                )
            )
        ],

        [
            "Best Before",
            safe_text(
                field_value(
                    product.get(
                        "best_before"
                    )
                )
            )
        ],

        [
            "Allergens",
            safe_text(
                field_value(
                    product.get(
                        "allergens"
                    )
                )
            )
        ]
    ]


    product_table = Table(

        extracted_rows,

        colWidths=[
            150,
            330
        ],

        repeatRows=1
    )


    product_table.setStyle(

        TableStyle([

            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.HexColor(
                    "#173B6C"
                )
            ),

            (
                "TEXTCOLOR",
                (0, 0),
                (-1, 0),
                colors.white
            ),

            (
                "FONTNAME",
                (0, 0),
                (-1, 0),
                "Helvetica-Bold"
            ),

            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.lightgrey
            ),

            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "TOP"
            ),

            (
                "PADDING",
                (0, 0),
                (-1, -1),
                7
            )
        ])
    )


    story.append(
        product_table
    )

    story.append(
        Spacer(
            1,
            22
        )
    )


    # =========================================
    # COMPLIANCE CHECKS
    # =========================================

    story.append(

        Paragraph(
            "Compliance Assessment",
            heading_style
        )
    )


    compliance = scan.get(
        "compliance",
        {}
    )


    checks = compliance.get(
        "checks",
        []
    )


    compliance_rows = [
        [
            "Declaration",
            "Status",
            "Reason"
        ]
    ]


    for check in checks:

        compliance_rows.append([
            safe_text(
                check.get(
                    "field"
                )
            ),

            safe_text(
                check.get(
                    "status"
                )
            ),

            Paragraph(
                safe_text(
                    check.get(
                        "reason"
                    )
                ),
                normal
            )
        ])


    compliance_table = Table(

        compliance_rows,

        colWidths=[
            130,
            110,
            240
        ],

        repeatRows=1
    )


    compliance_table.setStyle(

        TableStyle([

            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.HexColor(
                    "#173B6C"
                )
            ),

            (
                "TEXTCOLOR",
                (0, 0),
                (-1, 0),
                colors.white
            ),

            (
                "FONTNAME",
                (0, 0),
                (-1, 0),
                "Helvetica-Bold"
            ),

            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.lightgrey
            ),

            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "TOP"
            ),

            (
                "PADDING",
                (0, 0),
                (-1, -1),
                6
            )
        ])
    )


    story.append(
        compliance_table
    )


    story.append(
        Spacer(
            1,
            22
        )
    )


    # =========================================
    # BARCODE CROSS CHECK
    # =========================================

    story.append(

        Paragraph(
            "Barcode Cross-Check",
            heading_style
        )
    )


    cross_check = scan.get(
        "cross_check",
        {}
    )


    comparison_rows = [
        [
            "Field",
            "OCR",
            "Database",
            "Result"
        ]
    ]


    for label, key in [

        (
            "Brand",
            "brand"
        ),

        (
            "Food Name",
            "food_name"
        ),

        (
            "Net Quantity",
            "net_quantity"
        )
    ]:

        field = cross_check.get(
            key
        )

        if not isinstance(
            field,
            dict
        ):
            continue


        comparison_rows.append([

            label,

            safe_text(
                field.get(
                    "ocr"
                )
            ),

            safe_text(
                field.get(
                    "database"
                )
            ),

            safe_text(
                field.get(
                    "status"
                )
            )
        ])


    comparison_table = Table(

        comparison_rows,

        colWidths=[
            105,
            125,
            145,
            105
        ],

        repeatRows=1
    )


    comparison_table.setStyle(

        TableStyle([

            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.HexColor(
                    "#173B6C"
                )
            ),

            (
                "TEXTCOLOR",
                (0, 0),
                (-1, 0),
                colors.white
            ),

            (
                "FONTNAME",
                (0, 0),
                (-1, 0),
                "Helvetica-Bold"
            ),

            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.lightgrey
            ),

            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "TOP"
            ),

            (
                "PADDING",
                (0, 0),
                (-1, -1),
                6
            )
        ])
    )


    story.append(
        comparison_table
    )


    story.append(
        Spacer(
            1,
            25
        )
    )


    # =========================================
    # DISCLAIMER
    # =========================================

    story.append(

        Paragraph(
            "<b>Important:</b> "
            "This automated report provides preliminary "
            "compliance assistance. "
            "CANNOT_DETERMINE and REVIEW_REQUIRED results "
            "require manual verification. Barcode database "
            "information is reference data and does not prove "
            "that a declaration is physically present on the package.",
            normal
        )
    )


    document.build(
        story
    )


    return output_path