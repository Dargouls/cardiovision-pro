import logging

from fastapi import FastAPI, HTTPException, File, UploadFile, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client

from .utils.saveTempFiles import saveTempFiles
from .utils.http_worker import worker

from .ecg_analysis.api import app as ecgAnalysis_Routes, get_segments
from .reportMetrics.api import app as reportMetrics_Routes, get_frequencies_chart
from .perturbations.api import app as perturbations_Routes, analyze_disturbances
from .residual.api import app as residual_Routes, analyze_residual
from .metrics.api import app as metrics_Routes, get_metrics
from .metadata.api import app as metadata_Routes
from .modules.events.api import app as events_Routes, get_rr_intervals, get_heart_rate, get_beat_classification, get_spectral_analysis
from .modules.segmentation_st.api import app as segmentation_st_Routes, get_segmentation_st

from .utils.xcmConverter import converter_xcm

from dotenv import load_dotenv
from typing import List, Optional

import shutil
import uuid
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
# Configuração do Supabase
supabase: Client = None

app.include_router(reportMetrics_Routes)
app.include_router(ecgAnalysis_Routes)
app.include_router(perturbations_Routes)
app.include_router(metadata_Routes)
app.include_router(residual_Routes)
app.include_router(metrics_Routes)
app.include_router(events_Routes)
app.include_router(segmentation_st_Routes)

@app.on_event("startup")
async def startup():
    global supabase
    supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

async def send_module_data(queue: asyncio.Queue, module: str, 
                         data: dict, study_id: str, user_id: str, gateway_url: str):
    files_for_module = {
        "study_id": (None, study_id),
        "user_id": (None, user_id),
        "module": (None, module),
        "files": (f"{module}.json", json.dumps(data).encode('utf-8'), "application/json")
    }
    await queue.put((f"{gateway_url}/save-module", files_for_module))

async def update_progress(study_id: str, current_step: int, status: str, error: str = None):
    update_data = {
        "current_step": current_step,
        "status": status,
        "updated_at": "now()"
    }
    if error:
        update_data["error"] = error
    
    try:
        supabase.table("analysis-progress")\
                .update(update_data)\
                .eq("study_id", study_id)\
                .execute()
    except Exception as e:
        logger.error(f"Erro ao atualizar progresso: {str(e)}")

async def process_analysis(
    temp_dir: str,
    num_parts: int,
    samples_per_part: int,
    base_frequency: int,
    study_id: str,
    user_id: str
):
    try:
        modules = [
            ("segmentation", get_segments, {"upload_dir": temp_dir, "num_parts": num_parts, 
             "samples_per_part": samples_per_part, "frequency": base_frequency}),
            ("frequencies", get_frequencies_chart, {"UPLOAD_DIR": temp_dir, "frequency": base_frequency}),
            ("residual", analyze_residual, {"UPLOAD_DIR": temp_dir}),
            ("disturbances", analyze_disturbances, {"UPLOAD_DIR": temp_dir}),
            ("metrics", get_metrics, {"UPLOAD_DIR": temp_dir}),
            ("rr_intervals", get_rr_intervals, {"UPLOAD_DIR": temp_dir}),
            ("heart_rate", get_heart_rate, {"UPLOAD_DIR": temp_dir, "frequency": base_frequency}),
            ("beat_classification", get_beat_classification, {"UPLOAD_DIR": temp_dir}),
            ("spectral_analysis", get_spectral_analysis, {"UPLOAD_DIR": temp_dir}),
            ("segmentation_st", get_segmentation_st, {"upload_dir": temp_dir})
        ]

        total_steps = len(modules)
        results = {}

        await update_progress(study_id, 0, "PROCESSING")

        for step, (module_name, func, kwargs) in enumerate(modules, 1):
            try:
                logger.info(f"Processando módulo {module_name} (passo {step})")
                results[module_name] = await func(**kwargs)
                await update_progress(study_id, step, "PROCESSING")
            except Exception as e:
                logger.error(f"Erro no módulo {module_name}: {str(e)}")
                await update_progress(study_id, step, "FAILED", str(e))
                return


        client = httpx.AsyncClient(timeout=httpx.Timeout(10.0))
        queue = asyncio.Queue()
        num_workers = 2
        workers = [asyncio.create_task(worker(queue, client)) for _ in range(num_workers)]

        for module, data in results.items():
            await send_module_data(queue, module, data, study_id, user_id, GATEWAY_URL)

        
        await queue.join()
        for w in workers:
            w.cancel()
        await client.aclose()

        await update_progress(study_id, total_steps, "SUCCESS")

    except Exception as e:
        logger.error(f"Erro geral no processamento: {str(e)}")
        await update_progress(study_id, 0, "FAILED", str(e))
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

@app.post("/analyze_ecg")
async def analyze_ecg(
    background_tasks: BackgroundTasks,
    num_parts: Optional[int] = Form(...),
    samples_per_part: Optional[int] = Form(...),
    base_frequency: Optional[int] = Form(...),
    files: List[UploadFile] = File(...),
    study_id: Optional[str] = Form(...),
    user_id: Optional[str] = Form(...),
):
    try:
        supabase.table("analysis-progress").insert({
            "study_id": study_id,
            "user_id": user_id,
            "status": "PROCESSING",
            "current_step": 0
        }).execute()
    except Exception as e:
        logger.error(f"Erro ao criar registro de progresso: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro ao iniciar análise")

    temp_dir = tempfile.mkdtemp()  # Agora o diretório não será removido automaticamente

    try:
        file_paths = await saveTempFiles(temp_dir, files)
        if file_paths and file_paths[0].endswith('.xcm'):
            converter_xcm(xcm_file_path=file_paths[0], output_folder=temp_dir)
    except Exception as e:
        await update_progress(study_id, 0, "FAILED", str(e))
        shutil.rmtree(temp_dir)  # Remove o diretório em caso de erro
        raise HTTPException(status_code=400, detail=f"Erro no processamento do arquivo: {str(e)}")

    background_tasks.add_task(
        process_analysis,
        temp_dir,
        num_parts,
        samples_per_part,
        base_frequency,
        study_id,
        user_id
    )

    return {"study_id": study_id}

@app.get("/")
def healthCheck():
    return {"message": "Hello World"}

@app.get("/analysis/{study_id}/status")
async def get_analysis_status(study_id: str):
    try:
        response = supabase.table("analysis-progress")\
                        .select("*")\
                        .eq("study_id", study_id)\
                        .execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Análise não encontrada")
        return response.data[0]
    except Exception as e:
        logger.error(f"Erro ao buscar status: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro ao recuperar status")