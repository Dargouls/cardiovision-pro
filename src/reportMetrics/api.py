from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from typing import List
from pathlib import Path
from .metrics_service import HolterAnalyzer, save_complete_analysis
from .ecg_analyzer import ECGAnalyzer
import os

from ..utils.getAvailableRecords import get_available_records

app = APIRouter()

BASE_PATH = Path("uploads")  # Diretório para registros de ECG
UPLOAD_DIR = './uploads'  # Defina um diretório válido dentro do seu projeto


@app.post("/metrics")
async def get_metrics():
		"""
		Endpoint para fazer upload de um registro de ECG.
		"""
		try:
			file_name = get_available_records()[0]
			metrics = HolterAnalyzer(UPLOAD_DIR + '/' + file_name)
			results = metrics.save_complete_analysis(UPLOAD_DIR + '/' + file_name)

			print('metricas prontas')
			return results
		except FileNotFoundError:
				raise HTTPException(status_code=404, detail="Registro não encontrado.")

@app.post("/frequencies_chart")
async def get_frequencies_chart():
	"""
	Endpoint para analisar um registro de ECG.
	"""

	try:
		filename = get_available_records()[0]
		analyzer = ECGAnalyzer(UPLOAD_DIR)
		results = analyzer.save_complete_analysis(filename)

		return results
	except FileNotFoundError:
		raise HTTPException(status_code=404, detail="Registro não encontrado.")
