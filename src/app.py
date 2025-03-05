import logging

from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware

from .utils.saveTempFiles import saveTempFiles
from .utils.http_worker import worker

from .ecg_analysis.api import app as ecgAnalysis_Routes, get_segments
from .reportMetrics.api import app as reportMetrics_Routes, get_frequencies_chart
from .perturbations.api import app as perturbations_Routes, analyze_disturbances
from .residual.api import app as residual_Routes, analyze_ecg_artifacts
from .metrics.api import app as metrics_Routes, get_metrics
from .metadata.api import app as metadata_Routes
from .modules.events.api import app as events_Routes, get_rr_intervals, get_heart_rate, get_beat_classification, get_spectral_analysis

from .utils.xcmConverter import converter_xcm

from dotenv import load_dotenv
from typing import List, Optional

import tempfile
import asyncio
import httpx
import os
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn")

# Carregar as variáveis do .env
load_dotenv()

# Obter a URL do gateway
GATEWAY_URL = os.getenv("GATEWAY_URL")

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
app.include_router(residual_Routes)
app.include_router(metrics_Routes)
app.include_router(events_Routes)

# Função genérica para processar dados do ECG
async def process_ecg_data(temp_dir: str, num_parts: int, samples_per_part: int, base_frequency: int) -> dict:
    results = await asyncio.gather(
        get_segments(upload_dir=temp_dir, num_parts=num_parts, samples_per_part=samples_per_part, frequency=base_frequency),
        get_frequencies_chart(UPLOAD_DIR=temp_dir, frequency=base_frequency),
        analyze_ecg_artifacts(UPLOAD_DIR=temp_dir),
        analyze_disturbances(UPLOAD_DIR=temp_dir),
        get_metrics(UPLOAD_DIR=temp_dir),
        get_rr_intervals(UPLOAD_DIR=temp_dir),
        get_heart_rate(UPLOAD_DIR=temp_dir, frequency=base_frequency),
        get_beat_classification(UPLOAD_DIR=temp_dir),
        get_spectral_analysis(UPLOAD_DIR=temp_dir)
    )
    modules = ["segmentation", "frequencies", "artifacts", "disturbances", "newmetrics", 
               "rr_interval", "heart_rate", "beat_classification", "spectral_analysis"]
    return dict(zip(modules, results))

# Função para enviar dados de um módulo ao gateway
async def send_module_data(queue: asyncio.Queue, module: str, 
                         data: dict, study_id: str, user_id: str, gateway_url: str):
    files_for_module = {
        "study_id": (None, study_id),
        "user_id": (None, user_id),
        "module": (None, module),
        "files": (f"{module}.json", json.dumps(data).encode('utf-8'), "application/json")
    }
    await queue.put((f"{gateway_url}/save-module", files_for_module))

# Rota principal
@app.post("/analyze_ecg")
async def analyze_ecg(
    num_parts: Optional[int] = Form(2),
    samples_per_part: Optional[int] = Form(25),
    base_frequency: Optional[int] = Form(250),
    files: List[UploadFile] = File(...),
    user_id: Optional[str] = Form(...),
    study_id: Optional[str] = Form(...),
):
    with tempfile.TemporaryDirectory() as temp_dir:
        # Salvar arquivos e verificar conversão
        file_paths = await saveTempFiles(temp_dir, files)
        if file_paths and file_paths[0].endswith('.xcm'):
            converter_xcm(xcm_file_path=file_paths[0], output_folder=temp_dir)
        
        # Processar dados
        results = await process_ecg_data(temp_dir, num_parts, samples_per_part, base_frequency)
        
        # Configurar client e worker
        client = httpx.AsyncClient(timeout=httpx.Timeout(10.0))
        queue = asyncio.Queue()
        num_workers = 2
        workers = [asyncio.create_task(worker(queue, client)) for _ in range(num_workers)]
        
        # Enviar resultados para os módulos
        for module, data in results.items():
            await send_module_data(queue, module, data, study_id, user_id, GATEWAY_URL)
        
        # Aguardar conclusão e limpar
        await queue.join()
        for w in workers:
            w.cancel()
        await client.aclose()
        
        return {"message": "Análise concluída com sucesso"}

@app.get("/")
def healthCheck():
    return {"message": "Hello World"}