from fastapi import APIRouter, HTTPException, Form
from pathlib import Path
from typing import List, Dict
from .perturbations import AnalisadorInterferencia  # Import the AnalisadorInterferencia class

import os
import tempfile
import json
import httpx

from ..utils.getAvailableRecords import get_available_records
from ..utils.saveTempFiles import saveTempFiles

GATEWAY_URL = os.getenv("GATEWAY_URL")

app = APIRouter()

# Route to analyze perturbations in ECG
@app.post("/perturbations")
async def analyze_disturbances(
  UPLOAD_DIR: str,
  study_id: str = Form(...),
  user_id: str = Form(...),
):
    """
    Endpoint to analyze perturbations and technical issues in ECG records.
    """
    try:
        # Get available files in the upload directory
        filename = get_available_records(UPLOAD_DIR)[0]
        
        # Initialize the perturbation analyzer
        analyzer = AnalisadorInterferencia(UPLOAD_DIR)
        
        # Perform perturbation analysis
        results = analyzer.analisar_interferencias(filename, duracao=10, canal=0)

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json", encoding="utf-8") as temp_file:
          json.dump(results, temp_file)
          temp_file_path = temp_file.name

      # Enviar o arquivo JSON via multipart/form-data para o gateway
        async with httpx.AsyncClient() as client:
          with open(temp_file_path, "rb") as json_file:
              files = {
                  "study_id": (None, study_id),
                  "user_id": (None, user_id),
                  "module": (None, "disturbances"),
                  "files": ("disturbances.json", json_file, "application/json"),
              }
              gateway_response = await client.post(f"{GATEWAY_URL}/save-module", files=files)
              gateway_response.raise_for_status()
              gateway_result = gateway_response.json()  # Ex.: { "message": "Dados recebidos com sucesso" }
        
        os.remove(temp_file_path)
        # Return the results in JSON format
        return {"disturbances": "OK"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing perturbations: {str(e)}")