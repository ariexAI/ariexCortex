from pdf2image import convert_from_path
import pytesseract

POPPLER_PATH = r"C:\poppler\Release-25.12.0-0\poppler-25.12.0\Library\bin"

def extract_text_from_pdf(pdf_path):

    images = convert_from_path(pdf_path, poppler_path=POPPLER_PATH)

    text_output = ""

    for image in images:
        text = pytesseract.image_to_string(image)
        text_output += text

    return text_output