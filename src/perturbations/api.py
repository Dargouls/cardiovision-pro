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
  UPLOAD_DIR: str
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
        results = await analyzer.analisar_interferencias(filename, duracao=10, canal=0)

        return results

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing perturbations: {str(e)}")