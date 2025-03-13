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
async def get_metrics(
    UPLOAD_DIR: str = Form(...)
):
    try:
        records = get_available_records(UPLOAD_DIR)
        if not records:
            raise FileNotFoundError("Nenhum registro encontrado no diretório informado.")
        
        # Realiza a análise do(s) registro(s) disponível(is)
        analyzer = AnalisadorECG(UPLOAD_DIR)
        await analyzer.analisar_diretorio()
        
        results = analyzer.obter_resultados_formatados()
        
        return results
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Registro não encontrado.")