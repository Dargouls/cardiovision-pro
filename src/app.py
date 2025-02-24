import logging

from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware

from .utils.saveTempFiles import saveTempFiles

from .ecg_analysis.api import app as ecgAnalysis_Routes, get_segments
from .reportMetrics.api import app as reportMetrics_Routes, get_frequencies_chart, get_metrics
from .perturbations.api import app as perturbations_Routes, analyze_disturbances
from .residual.api import app as residual_Routes, analyze_ecg_artifacts
from .metrics.api import app as metrics_Routes, get_newmetrics
from .metadata.api import app as metadata_Routes

from .utils.xcmConverter import converter_xcm

from typing import List, Optional
import os
import tempfile
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn")

# Definir o diretório onde os arquivos serão salvos
RESULT_DIR = "./uploads"  # Defina um diretório válido dentro do seu projeto

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
app.include_router(metadata_Routes)

@app.post("/analyze_ecg")
async def analyze_ecg(
    num_parts: Optional[int] = Form(2),  # Número de partes
    samples_per_part: Optional[int] = Form(5000),  # Número de amostras por parte
    files: List[UploadFile] = File(...),  # Arquivos a serem enviados
    user_id: Optional[str] = Form(...),
    study_id: Optional[str] = Form(...),
):
  # Salvar arquivos temporariamente
  with tempfile.TemporaryDirectory() as temp_dir:
    file_paths = await saveTempFiles(temp_dir, files)
    
    # Verificar se a extensão do primeiro arquivo é .xcm
    if file_paths and file_paths[0].endswith('.xcm'):
      converter_xcm(xcm_file_path=file_paths[0], output_folder=temp_dir)
    
    results = await asyncio.gather(
        get_segments(upload_dir=temp_dir, user_id=user_id, study_id=study_id, num_parts=num_parts, samples_per_part=samples_per_part, file_paths=file_paths),
        get_frequencies_chart(UPLOAD_DIR=temp_dir, user_id=user_id, study_id=study_id),
        get_metrics(UPLOAD_DIR=temp_dir, user_id=user_id, study_id=study_id),
        analyze_ecg_artifacts(UPLOAD_DIR=temp_dir, user_id=user_id, study_id=study_id),
        analyze_disturbances(UPLOAD_DIR=temp_dir, user_id=user_id, study_id=study_id),
        get_newmetrics(UPLOAD_DIR=temp_dir, user_id=user_id, study_id=study_id),
    )

    # Desempacotando os resultados
    segmentation, frequenciesChart, metrics, residual, disturbances, newmetrics = results

    return {
      "message": "Análise concluída com sucesso",
      "segmentation": segmentation,
      "frequenciesChart": frequenciesChart, 
      "metrics": metrics,
      "residual": residual,
      "disturbances": disturbances,
      "newmetrics": newmetrics
    }

@app.get("/")
def healthCheck():
    return {"message": "Hello World"}