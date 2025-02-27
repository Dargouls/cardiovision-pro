import logging

from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware

from .utils.getAvailableRecords import get_available_records
from .utils.saveTempFiles import saveTempFiles
from .utils.clearTempFiles import clear_upload_directory

from .ecg_analysis.api import app as ecgAnalysis_Routes, get_segments
from .reportMetrics.api import app as reportMetrics_Routes, get_frequencies_chart, get_metrics
from .perturbations.api import app as perturbations_Routes, analyze_disturbances
from .residual.api import app as residual_Routes, analyze_ecg_artifacts

from .utils.xcmConverter import converter_xcm

from typing import List, Optional
import os
import wfdb
from .ecg_analysis.main import ECGAnalyzer
  
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn")

# Definir o diretório onde os arquivos serão salvos
UPLOAD_DIR = "./uploads"  # Defina um diretório válido dentro do seu projeto
RESULT_DIR = "./uploads"  # Defina um diretório válido dentro do seu projeto

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
app.include_router(perturbations_Routes)

@app.post("/analyze_ecg")
async def analyze_ecg(
    num_parts: Optional[int] = Form(2),  # Número de partes
    samples_per_part: Optional[int] = Form(5000),  # Número de amostras por parte
    files: List[UploadFile] = File(...),  # Arquivos a serem enviados
):  
  clear_upload_directory(UPLOAD_DIR)
  # Salvar arquivos temporariamente
  file_paths = await saveTempFiles(files)
  
  # Verificar se a extensão do primeiro arquivo é .xcm
  if file_paths and file_paths[0].endswith('.xcm'):
    converter_xcm(xcm_file_path=file_paths[0], output_folder=RESULT_DIR)
  
  # Realizar segmentação, gráficos e métricas
  segmentation = await get_segments(UPLOAD_DIR, num_parts, samples_per_part, file_paths)
  frequenciesChart = await get_frequencies_chart()
  metrics = await get_metrics()
  residual = await analyze_ecg_artifacts()
  disturbances = await analyze_disturbances()
  
  # Limpar o diretório de uploads
  clear_upload_directory(UPLOAD_DIR)
  
  return {
     "segmentation": segmentation,
     "frequenciesChart": frequenciesChart, 
     "metrics": metrics,
     "residual": residual,
     "disturbances": disturbances,
    "message": "success"
  }

@app.get("/")
def healthCheck():
    return {"message": "Hello World"}