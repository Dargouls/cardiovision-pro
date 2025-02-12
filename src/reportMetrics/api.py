from fastapi import APIRouter, UploadFile, File, HTTPException, Form

from .metrics_service import HolterAnalyzer, save_complete_analysis
from .ecg_analyzer import ECGAnalyzer
from ..utils.getAvailableRecords import get_available_records

import os
import tempfile
import json
import httpx


GATEWAY_URL = os.getenv("GATEWAY_URL")

app = APIRouter()

@app.post("/metrics")
async def get_metrics(
  UPLOAD_DIR: str,
	study_id: str = Form(...),
	user_id: str = Form(...),
):
		"""
		Endpoint para fazer upload de um registro de ECG.
		"""
		try:
			file_name = get_available_records(UPLOAD_DIR)[0]
			metrics = HolterAnalyzer(UPLOAD_DIR + '/' + file_name)
			results = metrics.save_complete_analysis(UPLOAD_DIR + '/' + file_name)

			with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json", encoding="utf-8") as temp_file:
				json.dump(results, temp_file)
				temp_file_path = temp_file.name

    # Enviar o arquivo JSON via multipart/form-data para o gateway
			async with httpx.AsyncClient() as client:
				with open(temp_file_path, "rb") as json_file:
						files = {
								"study_id": (None, study_id),
								"user_id": (None, user_id),
								"module": (None, "metrics"),
								"files": ("metrics.json", json_file, "application/json"),
						}
						gateway_response = await client.post(f"{GATEWAY_URL}/save-module", files=files)
						gateway_response.raise_for_status()
						gateway_result = gateway_response.json()  # Ex.: { "message": "Dados recebidos com sucesso" }
			
			os.remove(temp_file_path)

			return {"metrics": "OK"}
		except FileNotFoundError:
				raise HTTPException(status_code=404, detail="Registro não encontrado.")

@app.post("/frequencies_chart")
async def get_frequencies_chart(
  UPLOAD_DIR: str,
	study_id: str = Form(...),
	user_id: str = Form(...),
):
	"""
	Endpoint para analisar um registro de ECG.
	"""

	try:
		filename = get_available_records(UPLOAD_DIR)[0]
		analyzer = ECGAnalyzer(UPLOAD_DIR)
		results = analyzer.save_complete_analysis(filename)

		with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json", encoding="utf-8") as temp_file:
			json.dump(results, temp_file)
			temp_file_path = temp_file.name

    # Enviar o arquivo JSON via multipart/form-data para o gateway
		async with httpx.AsyncClient() as client:
			with open(temp_file_path, "rb") as json_file:
					files = {
							"study_id": (None, study_id),
							"user_id": (None, user_id),
							"module": (None, "frequencies"),
							"files": ("frequenciesCharts.json", json_file, "application/json"),
					}
					gateway_response = await client.post(f"{GATEWAY_URL}/save-module", files=files)
					gateway_response.raise_for_status()
					gateway_result = gateway_response.json()  # Ex.: { "message": "Dados recebidos com sucesso" }
    
		os.remove(temp_file_path)

		return {"frequencies": "OK"}
	
	except FileNotFoundError:
		raise HTTPException(status_code=404, detail="Registro não encontrado.")
