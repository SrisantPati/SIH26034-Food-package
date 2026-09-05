from pathlib import Path
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi import Request

import os
import shutil
import uuid

from app.ocr.ocr_service import extract_text
from app.extraction.extractor import extract_fields
from app.compliance.compliance_engine import run_compliance_checks

app = FastAPI(title="Product Compliance System")
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

  

    extension = os.path.splitext(
        file.filename
    )[1]

    filename = (
        f"{uuid.uuid4()}{extension}"
    )

    image_path = os.path.join(
        "app/uploads",
        filename
    )

    with open(
        image_path,
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
        image_path
    )

    # ----------------------------
    # FIELD EXTRACTION
    # ----------------------------

    product = extract_fields(
        ocr_results
    )

    # ----------------------------
    # COMPLIANCE
    # ----------------------------

    compliance = run_compliance_checks(
        product
    )

    return {
        "success": True,
        "product": product,
        "compliance": compliance
    }

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