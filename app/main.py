from pathlib import Path
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi import Request

from fastapi import HTTPException
from fastapi.responses import FileResponse

from app.reports.report_generator import (
    create_report
)

import os
import shutil
import uuid

from app.database.database import (
    initialize_database,
    save_scan,
    get_scan,
    get_scan_history
)

from app.barcode.barcode_scanner import scan_barcode
from app.barcode.product_lookup import lookup_product
from app.barcode.cross_checker import compare_product_data

from app.ocr.ocr_service import extract_text
from app.extraction.extractor import extract_fields
from app.compliance.compliance_engine import run_compliance_checks

app = FastAPI(title="Product Compliance System")
initialize_database()
app.mount(
    "/static",
    StaticFiles(directory="app/static"),
    name="static"
)

templates = Jinja2Templates(
    directory="app/templates"
)

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="index.html"
    )

@app.post("/analyze")
async def analyze_product(
    file: UploadFile = File(...)
):

    extension = Path(
        file.filename
    ).suffix

    filename = (
        f"{uuid.uuid4()}{extension}"
    )

    image_path = (
        UPLOAD_DIR / filename
    )

    with image_path.open(
        "wb"
    ) as buffer:

        shutil.copyfileobj(
            file.file,
            buffer
        )

    # ----------------------------
    # OCR
    # ----------------------------

    ocr_results = extract_text(
        str(image_path)
    )

    # ----------------------------
    # FIELD EXTRACTION
    # ----------------------------

    product = extract_fields(
        ocr_results
    )

    # ----------------------------
    # BARCODE
    # ----------------------------

    barcode = scan_barcode(
        str(image_path)
    )

    # ----------------------------
    # BARCODE PRODUCT LOOKUP
    # ----------------------------

    if barcode.get("status") == "DETECTED":

        barcode_product = lookup_product(
            barcode.get("value")
        )

    else:

        barcode_product = {
            "barcode": None,
            "status": "NO_BARCODE",
            "source": "Open Food Facts"
        }

    # ----------------------------
    # OCR VS BARCODE CROSS-CHECK
    # ----------------------------

    cross_check = compare_product_data(
        product,
        barcode_product
    )

    # ----------------------------
    # COMPLIANCE
    # ----------------------------

    compliance = run_compliance_checks(
        product
    )

    scan_id = save_scan(
    filename=filename,
    product=product,
    barcode=barcode,
    barcode_product=barcode_product,
    cross_check=cross_check,
    compliance=compliance
    )
        # ----------------------------
    # FINAL RESPONSE
    # ----------------------------

    return {
        "success": True,
        "scan_id": scan_id,
        "report_url": f"/report/{scan_id}",
        "product": product,
        "barcode": barcode,
        "barcode_product": barcode_product,
        "cross_check": cross_check,
        "compliance": compliance
    }

@app.get("/history")
async def history():

    return {
        "scans":
            get_scan_history()
    }

    # ----------------------------
    # FINAL RESPONSE
    # ----------------------------

    

@app.get("/report/{scan_id}")
async def download_report(
    scan_id: int
):

    scan = get_scan(
        scan_id
    )

    if scan is None:

        raise HTTPException(
            status_code=404,
            detail="Scan not found"
        )


    report_path = create_report(
        scan
    )


    return FileResponse(

        path=str(
            report_path
        ),

        media_type="application/pdf",

        filename=(
            f"PackCheck_Report_{scan_id}.pdf"
        )
    )

UPLOAD_DIR = Path(__file__).resolve().parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

"""
@app.get("/")
def root():
    return {
        "message": "Product Compliance System is running"
    }
"""

@app.post("/upload")
async def upload_product_image(file: UploadFile = File(...)):
    file_path = UPLOAD_DIR / file.filename

    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {
        "message": "Image uploaded successfully",
        "filename": file.filename
    }


@app.post("/ocr")
async def run_ocr(file: UploadFile = File(...)):
    file_path = UPLOAD_DIR / file.filename

    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    result = extract_text(str(file_path))

    return {
        "filename": file.filename,
        "ocr_result": result
    }