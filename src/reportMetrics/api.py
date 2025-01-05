from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from typing import List
from pathlib import Path
from .metrics_service import HolterAnalyzer, save_complete_analysis
from .ecg_analyzer import ECGAnalyzer
import os

app = APIRouter()

BASE_PATH = Path("uploads")  # Diretório para registros de ECG
UPLOAD_DIR = './uploads'  # Defina um diretório válido dentro do seu projeto

analyzer = ECGAnalyzer(UPLOAD_DIR)
metrics = HolterAnalyzer(UPLOAD_DIR + '/418')

@app.post("/metrics")
async def get_metrics():
    """
    Endpoint para fazer upload de um registro de ECG.
    """
    try:
      results = metrics.save_complete_analysis(UPLOAD_DIR + '/418')

      return results
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Registro não encontrado.")

@app.post("/frequencies_chart")
async def get_frequencies_chart():
	"""
	Endpoint para analisar um registro de ECG.
	"""
	try:
		filename = analyzer.get_available_records()[0]
		results = analyzer.save_complete_analysis(filename)
		return results
	except FileNotFoundError:
		raise HTTPException(status_code=404, detail="Registro não encontrado.")
