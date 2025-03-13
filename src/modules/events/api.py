from fastapi import HTTPException, File, UploadFile, Form, APIRouter

from ...utils.getAvailableRecords import get_available_records
from ...utils.saveTempFiles import saveTempFiles
from .events import HolterAnalyzer

from typing import List, Optional
from dotenv import load_dotenv
import tempfile
import os
import json
import httpx
import asyncio
import io

from .cases.beat_classification import BeatClassifier
from .cases.heart_rate import HeartRateAnalyzer
from .cases.rr_intervals import RRIntervalsAnalyzer
from .cases.spectral_analysis import SpectralAnalyzer

# Carregar as variáveis do .env
load_dotenv()

# Obter a URL do gateway
GATEWAY_URL = os.getenv("GATEWAY_URL")

app = APIRouter()

@app.post("/analyze_events")
async def get_events(
    study_id: str = Form(...),
    user_id: str = Form(...),
    UPLOAD_DIR: str = Form(...),
):
    try:
        available_records = get_available_records(UPLOAD_DIR)
        if not available_records:
            raise HTTPException(status_code=400, detail="Nenhum registro WFDB encontrado.")
        
        record_name = available_records[0]
        base_path = f"{UPLOAD_DIR}/{record_name}"

        # Executar análises em paralelo
        results = await asyncio.gather(
            # get_beat_classification(base_path),
            get_rr_intervals(base_path),
            # get_heart_rate(base_path),
            # get_spectral_analysis(base_path)
        )
        # beat_classification,
        rr_intervals = results
        # heart_rate, spectral_analysis = results

        # Estruturar resultados
        modules = [
            # ("beat_classification", beat_classification),
            ("rr_intervals", rr_intervals),
            # ("heart_rate", heart_rate),
            # ("spectral_analysis", spectral_analysis)
        ]
        
        # Enviar cada módulo separadamente utilizando arquivos em memória
        async with httpx.AsyncClient() as client:
            tasks = []
            for module_name, data in modules:
                # Gerar JSON em memória
                data_json = json.dumps(data)
                data_bytes = data_json.encode('utf-8')
                file_obj = io.BytesIO(data_bytes)
                
                files = {
                    "study_id": (None, study_id),
                    "user_id": (None, user_id),
                    "module": (None, module_name),
                    "files": (f"{module_name}.json", file_obj, "application/json")
                }
                
                tasks.append(
                    client.post(f"{GATEWAY_URL}/save-module", files=files)
                )
            
            responses = await asyncio.gather(*tasks)
            for resp in responses:
                print('Eventos: ', resp.status_code)
                resp.raise_for_status()
        
        print('eventos ok')
        return {"status": "OK"}

    except httpx.HTTPStatusError as http_err:
        raise HTTPException(
            status_code=http_err.response.status_code,
            detail=f"Erro no gateway: {http_err.response.text}"
        )
    except Exception as e:
        print('Erro em analisar eventos: ', e)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/update_events")
async def get_segments(
    files: List[UploadFile] = File(...),
):
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            await saveTempFiles(tmp_dir, files)
            available_records = get_available_records(tmp_dir)
            if not available_records:
                raise HTTPException(status_code=400, detail="Nenhum registro WFDB encontrado.")
            
            record_name = available_records[0]  # Já contém o nome sem a extensão
            # analyzer = HolterAnalyzer(f"{tmp_dir}/{record_name}")
            # data = analyzer.analyze()
            
            data = await get_rr_intervals(f"{tmp_dir}/{record_name}")

            return data
    except httpx.HTTPStatusError as http_err:
        raise HTTPException(status_code=http_err.response.status_code,
                            detail=f"Erro no gateway: {http_err.response.text}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def get_record_path(upload_dir: str) -> str:
    """Obtém o primeiro registro WFDB do diretório."""
    available_records = get_available_records(upload_dir)
    if not available_records:
        raise HTTPException(400, "Nenhum registro WFDB encontrado.")
    return f"{upload_dir}/{available_records[0]}"

@app.post("/heart-rate")
async def get_heart_rate(
    UPLOAD_DIR: str = Form(...),
    frequency: int = Form(...)
):
    try:
        print('Etapa: Heart Rate')
        record_path = get_record_path(UPLOAD_DIR)
        analyzer = HeartRateAnalyzer(record_path, frequency)
        results = await analyzer.get_results()
        return results
    except Exception as e:
        print(f'Erro em heart-rate: {e}')
        raise HTTPException(500, detail=str(e))


@app.post("/beat-classification")
async def get_beat_classification(
    UPLOAD_DIR: str = Form(...),
):
    try:
        print('Etapa: Beat Classification')
        record_path = get_record_path(UPLOAD_DIR)
        classifier = BeatClassifier(record_path)
        results = await classifier.get_results()  # Método assíncrono
        return results
    except Exception as e:
        print(f'Erro em beat-classification: {e}')
        raise HTTPException(500, detail=str(e))


@app.post("/spectral-analysis")
async def get_spectral_analysis(
    UPLOAD_DIR: str = Form(...),
):
    try:
        print('Etapa: Spectral Analysis')
        record_path = get_record_path(UPLOAD_DIR)
        analyzer = SpectralAnalyzer(record_path)  # Factory assíncrona
        results = await analyzer.get_results()
        return results
    except Exception as e:
        print(f'Erro em spectral-analysis: {e}')
        raise HTTPException(500, detail=str(e))


@app.post("/rr-intervals")
async def get_rr_intervals(
    UPLOAD_DIR: str = Form(...),
):
    try:
        print('Etapa: RR Intervals')
        record_path = get_record_path(UPLOAD_DIR)
        analyzer = RRIntervalsAnalyzer(record_path)
        results = await analyzer.get_results()
        return results
    except Exception as e:
        print(f'Erro em rr-intervals: {e}')
        raise HTTPException(500, detail=str(e))