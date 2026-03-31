# -----------------------
# PATH FIX (IMPORTANT)
# -----------------------
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# -----------------------
# IMPORTS
# -----------------------
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import shutil
import pytesseract
import cv2
import numpy as np
from PIL import Image

# -----------------------
# SERVICES
# -----------------------
from services.auto_boq_service import build_auto_boq
from services.footing_service import calculate_footing
from services.slab_service import calculate_slab
from services.boq_services import generate_project_boq
from services.excel_service import generate_boq_excel
from services.pdf_footing_extractor import extract_text_from_pdf, find_footing_sizes
from services.cortex_service import process_query

from models.footing_model import FootingInput

# -----------------------
# APP INIT
# -----------------------
app = FastAPI(title="Ariex Cortex API")

# -----------------------
@app.get("/")
def root():
    return FileResponse("index.html")
# -----------------------
# OCR CONFIG
# -----------------------
pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# -----------------------
# MODELS
# -----------------------

class SlabInput(BaseModel):
    length: float = Field(gt=0)
    breadth: float = Field(gt=0)
    thickness: float = Field(gt=0)

    steel_diameter: float = Field(gt=0)
    steel_spacing: float = Field(gt=0)

    rcc_rate: float = Field(ge=0)
    steel_rate: float = Field(ge=0)


class ProjectInput(BaseModel):
    footing: FootingInput
    slab: SlabInput
    project_name: Optional[str] = "My Project"
    building_type: Optional[str] = "G+2"
    col_data: Optional[Dict[str, Any]] = None
    beam_data: Optional[Dict[str, Any]] = None


# -----------------------
# CORTEX CHAT MODELS
# -----------------------

class HistoryItem(BaseModel):
    role: str
    content: str


class CortexRequest(BaseModel):
    question: str
    history: Optional[List[HistoryItem]] = []


class CortexResponse(BaseModel):
    answer: str
    category: str


# -----------------------
# HEALTH CHECK
# -----------------------

@app.get("/health")
def health():
    return {"status": "online", "engine": "Ariex Cortex v2"}

# -----------------------
# FOOTING BOQ
# -----------------------

@app.post("/calculate_full_footing")
def calculate_full_footing_endpoint(data: FootingInput):
    result = calculate_footing(data)
    return {
        "project_summary": {
            "number_of_footings": data.number_of_footings,
            "total_cost": round(result["total_cost"], 2)
        }
    }

# -----------------------
# SLAB BOQ
# -----------------------

@app.post("/calculate_slab")
def slab_endpoint(data: SlabInput):
    result = calculate_slab(data)
    return {
        "volume_m3": round(result["volume"], 2),
        "steel_kg": round(result["steel_weight"], 2),
        "concrete_cost": round(result["concrete_amount"], 2),
        "steel_cost": round(result["steel_amount"], 2),
        "total_cost": round(result["total_cost"], 2)
    }

# -----------------------
# PROJECT BOQ
# -----------------------

@app.post("/calculate_project_boq")
def calculate_project_boq_endpoint(data: ProjectInput):
    return generate_project_boq(data)

# -----------------------
# EXCEL GENERATION
# -----------------------

last_excel_path = None

@app.post("/generate_boq_excel")
def generate_boq_excel_endpoint(data: ProjectInput):
    global last_excel_path

    result = generate_project_boq(data)
    boq_data = result["boq"]
    grand_total = result["grand_total"]

    full_total = grand_total

    if data.col_data:
        col = data.col_data
        full_total += (
            col.get("colRCC", 0) * col.get("cRccRate", 0) +
            col.get("colSteel", 0) * col.get("cSteelRate", 0) +
            col.get("colFW", 0) * col.get("cFwRate", 0)
        )

    if data.beam_data:
        beam = data.beam_data
        full_total += (
            beam.get("beamRCC", 0) * beam.get("bRccRate", 0) +
            beam.get("beamSteel", 0) * beam.get("bSteelRate", 0) +
            beam.get("beamFW", 0) * beam.get("bFwRate", 0)
        )

    last_excel_path = generate_boq_excel(
        boq_data,
        round(full_total, 2),
        project_name=data.project_name,
        building_type=data.building_type,
        col_data=data.col_data,
        beam_data=data.beam_data
    )

    return {"status": "ready"}

@app.get("/download_latest_excel")
def download_latest_excel():
    global last_excel_path

    if not last_excel_path or not os.path.exists(last_excel_path):
        return {"error": "No Excel file generated yet."}

    return FileResponse(
        path=last_excel_path,
        filename="project_boq.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# -----------------------
# DRAWING UPLOAD
# -----------------------

@app.post("/upload_drawing")
def upload_drawing(file: UploadFile = File(...)):
    upload_folder = "drawings"
    os.makedirs(upload_folder, exist_ok=True)

    file_path = os.path.join(upload_folder, file.filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {"message": "uploaded", "file": file.filename}

# -----------------------
# DETECT FOOTING
# -----------------------

@app.get("/detect_footing_sizes")
def detect_footing_sizes_api():
    drawing_folder = "drawings"

    if not os.path.exists(drawing_folder):
        return {"message": "No drawings"}

    files = os.listdir(drawing_folder)

    if not files:
        return {"message": "Empty folder"}

    latest = os.path.join(drawing_folder, files[-1])

    img = cv2.imread(latest)

    if img is None:
        pil_img = Image.open(latest).convert("RGB")
        img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    text = pytesseract.image_to_string(gray)

    sizes = find_footing_sizes(text)

    return {"sizes": sizes, "text": text}

# -----------------------
# AUTO BOQ
# -----------------------

@app.post("/auto_boq_from_drawing")
def auto_boq_from_drawing(file: UploadFile = File(...)):
    upload_folder = "drawings"
    os.makedirs(upload_folder, exist_ok=True)

    path = os.path.join(upload_folder, file.filename)

    with open(path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    sizes = find_footing_sizes(pytesseract.image_to_string(cv2.imread(path)))

    params = {
        "number_of_footings": 1,
        "excavation_depth": 1.5,
        "pcc_thickness": 0.1,
        "steel_diameter": 12,
        "steel_spacing": 0.15,
        "excavation_rate": 300,
        "pcc_rate": 4500,
        "rcc_rate": 7000,
        "steel_rate": 70
    }

    result = build_auto_boq(sizes, calculate_footing, params)

    return {"boq": result}

# -----------------------
# 🧠 ARIEX CORTEX (FINAL)
# -----------------------

@app.post("/cortex/query", response_model=CortexResponse)
def cortex_query(data: CortexRequest):
    history = [{"role": h.role, "content": h.content} for h in data.history]

    result = process_query(data.question, history)

    return {
        "answer": result["answer"],
        "category": result["category"]
    }