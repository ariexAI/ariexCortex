import os
from pdf2image import convert_from_path
import pytesseract

POPPLER_PATH = r"C:\poppler\Release-25.12.0-0\poppler-25.12.0\Library\bin"

def process_drawing(pdf_path: str) -> dict:
    if not os.path.exists(pdf_path):
        return {"status": "error", "message": "File not found"}

    try:
        images = convert_from_path(pdf_path, dpi=300, poppler_path=POPPLER_PATH)
        
        full_text = ""
        for image in images:
            text = pytesseract.image_to_string(image)
            full_text += text

        return {
            "status": "success",
            "pages": len(images),
            "text": full_text
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}