import logging

from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware

from .utils.getAvailableRecords import get_available_records
from .utils.saveTempFiles import saveTempFiles
from .utils.clearTempFiles import clear_upload_directory

from .ecg_analysis.api import app as ecgAnalysis_Routes, get_segments
from .reportMetrics.api import app as reportMetrics_Routes, get_frequencies_chart, get_metrics

from typing import List, Optional
import os
import wfdb
from .ecg_analysis.main import ECGAnalyzer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn")

# Definir o diretório onde os arquivos serão salvos
UPLOAD_DIR = "./uploads"  # Defina um diretório válido dentro do seu projeto

# Garantir que o diretório de uploads existe
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

origins = [
    "*",
]

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(reportMetrics_Routes)
app.include_router(ecgAnalysis_Routes)
  
@app.post("/analyze_ecg")
async def analyze_ecg(
    num_parts: Optional[int] = Form(2),  # Número de partes
    samples_per_part: Optional[int] = Form(5000),  # Número de amostras por parte
    files: List[UploadFile] = File(...),  # Arquivos a serem enviados
):  
  file_paths = await saveTempFiles(files)
  
  segmentation = await get_segments(UPLOAD_DIR, num_parts, samples_per_part, file_paths)
  frequenciesChart = await get_frequencies_chart()
  metrics = await get_metrics()
  
  clear_upload_directory(UPLOAD_DIR)
  
  return {"segmentation": segmentation, "frequenciesChart": frequenciesChart, "metrics": metrics}

@app.get("/")
def healthCheck():
    return {"message": "Hello World"}