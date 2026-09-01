from fastapi import FastAPI, UploadFile, File
from pathlib import Path
import shutil

from app.ocr.ocr_service import extract_text


app = FastAPI(title="Product Compliance System")


UPLOAD_DIR = Path(__file__).resolve().parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@app.get("/")
def root():
    return {
        "message": "Product Compliance System is running"
    }


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