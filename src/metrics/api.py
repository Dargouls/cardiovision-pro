from fastapi import APIRouter, HTTPException, Form

from .metrics import AnalisadorECG
from ..utils.getAvailableRecords import get_available_records

import os
import tempfile
import json
import httpx

GATEWAY_URL = os.getenv("GATEWAY_URL")

app = APIRouter()

@app.post("/new_metrics")
async def get_newmetrics(
    UPLOAD_DIR: str,
    study_id: str = Form(...),
    user_id: str = Form(...),
):
    try:
        records = get_available_records(UPLOAD_DIR)
        if not records:
            raise FileNotFoundError("Nenhum registro encontrado no diretório informado.")
        # Seleciona o primeiro registro disponível
        file_name = records[0]
        file_path = os.path.join(UPLOAD_DIR, file_name)
        
        # Realiza a análise do(s) registro(s) disponível(is)
        analyzer = AnalisadorECG(UPLOAD_DIR)
        analyzer.analisar_diretorio()
        
        results = analyzer.obter_resultados_formatados()
        
        # Salva os resultados em um arquivo JSON temporário
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json", encoding="utf-8") as temp_file:
            json.dump(results, temp_file)
            temp_file_path = temp_file.name

        # Envia o arquivo JSON via multipart/form-data para o gateway
        async with httpx.AsyncClient() as client:
            with open(temp_file_path, "rb") as json_file:
                files = {
                    "study_id": (None, study_id),
                    "user_id": (None, user_id),
                    "module": (None, "newmetrics"),
                    "files": ("metrics.json", json_file, "application/json"),
                }
                gateway_response = await client.post(f"{GATEWAY_URL}/save-module", files=files)
                gateway_response.raise_for_status()
                gateway_result = gateway_response.json()
        
        os.remove(temp_file_path)
        return {"metrics": "OK"}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Registro não encontrado.")