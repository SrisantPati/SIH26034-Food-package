import sqlite3
import json
from pathlib import Path
from datetime import datetime


DB_PATH = (
    Path(__file__).resolve().parent
    / "packcheck.db"
)


def get_connection():

    connection = sqlite3.connect(
        DB_PATH
    )

    connection.row_factory = (
        sqlite3.Row
    )

    return connection


def initialize_database():

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS scans (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            filename TEXT,

            barcode TEXT,

            product_name TEXT,

            overall_status TEXT,

            product_json TEXT,

            barcode_json TEXT,

            barcode_product_json TEXT,

            cross_check_json TEXT,

            compliance_json TEXT,

            created_at TEXT
        )
        """
    )

    connection.commit()

    connection.close()


def save_scan(
    filename,
    product,
    barcode,
    barcode_product,
    cross_check,
    compliance
):

    product_name = None

    brand = product.get(
        "brand_name"
    )

    if isinstance(
        brand,
        dict
    ):
        product_name = brand.get(
            "value"
        )


    summary = compliance.get(
        "summary",
        {}
    )


    if summary.get(
        "non_compliant",
        0
    ) > 0:

        overall_status = (
            "NON_COMPLIANT"
        )

    elif (
        summary.get(
            "review_required",
            0
        ) > 0

        or

        summary.get(
            "cannot_determine",
            0
        ) > 0
    ):

        overall_status = (
            "REVIEW_REQUIRED"
        )

    else:

        overall_status = (
            "COMPLIANT"
        )


    connection = get_connection()

    cursor = connection.cursor()


    cursor.execute(
        """
        INSERT INTO scans (

            filename,
            barcode,
            product_name,
            overall_status,

            product_json,
            barcode_json,
            barcode_product_json,
            cross_check_json,
            compliance_json,

            created_at

        )

        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,

        (
            filename,

            barcode.get(
                "value"
            ),

            product_name,

            overall_status,

            json.dumps(
                product
            ),

            json.dumps(
                barcode
            ),

            json.dumps(
                barcode_product
            ),

            json.dumps(
                cross_check
            ),

            json.dumps(
                compliance
            ),

            datetime.now().isoformat(
                timespec="seconds"
            )
        )
    )


    scan_id = cursor.lastrowid

    connection.commit()

    connection.close()

    return scan_id


def get_scan(
    scan_id
):

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT *
        FROM scans
        WHERE id = ?
        """,
        (
            scan_id,
        )
    )

    row = cursor.fetchone()

    connection.close()


    if row is None:
        return None


    return {
        "id":
            row["id"],

        "filename":
            row["filename"],

        "barcode":
            row["barcode"],

        "product_name":
            row["product_name"],

        "overall_status":
            row["overall_status"],

        "created_at":
            row["created_at"],

        "product":
            json.loads(
                row["product_json"]
            ),

        "barcode_data":
            json.loads(
                row["barcode_json"]
            ),

        "barcode_product":
            json.loads(
                row[
                    "barcode_product_json"
                ]
            ),

        "cross_check":
            json.loads(
                row["cross_check_json"]
            ),

        "compliance":
            json.loads(
                row["compliance_json"]
            )
    }


def get_scan_history(
    limit=50
):

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT

            id,
            filename,
            barcode,
            product_name,
            overall_status,
            created_at

        FROM scans

        ORDER BY id DESC

        LIMIT ?
        """,
        (
            limit,
        )
    )

    rows = cursor.fetchall()

    connection.close()


    return [
        dict(row)
        for row in rows
    ]