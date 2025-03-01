from fastapi import HTTPException, File, UploadFile, Form, APIRouter

from ..utils.getAvailableRecords import get_available_records
from ..utils.saveTempFiles import saveTempFiles
from .events import HolterAnalyzer

from typing import List, Optional
import tempfile
import os
import json
import httpx
from dotenv import load_dotenv
from pathlib import Path
import wfdb

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
        # Obter o primeiro registro disponível no diretório
        available_records = get_available_records(UPLOAD_DIR)
        if not available_records:
            raise HTTPException(status_code=400, detail="Nenhum registro WFDB encontrado.")
        
        record_name = available_records[0]  # Já contém o nome sem a extensão
        analyzer = HolterAnalyzer(f"{UPLOAD_DIR}/{record_name}")
        data = analyzer.analyze()

        # Criar um arquivo JSON temporário com os dados de segmentação
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json", encoding="utf-8") as temp_file:
            json.dump(data, temp_file)
            temp_file_path = temp_file.name

        # Enviar o arquivo JSON via multipart/form-data para o gateway
        async with httpx.AsyncClient() as client:
            with open(temp_file_path, "rb") as json_file:
                files = {
                    "study_id": (None, study_id),
                    "user_id": (None, user_id),
                    "module": (None, "events"),
                    "files": ("events.json", json_file, "application/json"),
                }
                gateway_response = await client.post(f"{GATEWAY_URL}/save-module", files=files)
                gateway_response.raise_for_status()
                gateway_result = gateway_response.json()  # Ex.: { "message": "Dados recebidos com sucesso" }

        # Remover o arquivo temporário após o envio
        os.remove(temp_file_path)

        # Retornar o status conforme a resposta do gateway
        return {
            "status": 'OK'
        }

    except httpx.HTTPStatusError as http_err:
        raise HTTPException(status_code=http_err.response.status_code,
                            detail=f"Erro no gateway: {http_err.response.text}")
    except Exception as e:
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
            analyzer = HolterAnalyzer(f"{tmp_dir}/{record_name}")
            data = analyzer.analyze()

            return data
    except httpx.HTTPStatusError as http_err:
        raise HTTPException(status_code=http_err.response.status_code,
                            detail=f"Erro no gateway: {http_err.response.text}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
