from fastapi import APIRouter, UploadFile, File, HTTPException, Form

from .metrics_service import HolterAnalyzer, save_complete_analysis
from .ecg_analyzer import ECGAnalyzer
from ..utils.getAvailableRecords import get_available_records
from ..utils.saveTempFiles import saveTempFiles

from typing import Optional
from pathlib import Path
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
	frequency: str = Form(...),
):
	"""
	Endpoint para analisar um registro de ECG.
	"""

	try:
		filename = get_available_records(UPLOAD_DIR)[0]
		analyzer = ECGAnalyzer(UPLOAD_DIR)
		results = await analyzer.save_complete_analysis(filename, int(frequency))

		return results
	
	except FileNotFoundError:
		raise HTTPException(status_code=404, detail="Registro não encontrado.")
	
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
import tempfile
import os
from pathlib import Path

@app.post("/update_frequencies_charts")
async def update_frequencies_chart(
  files: list[UploadFile] = File(...),
  frequency: str = Form(...),
	period: Optional[str] = Form(None),
):
  try:
    # Cria um diretório temporário exclusivo para esta requisição
    with tempfile.TemporaryDirectory() as tmp_dir:
      # Salva cada arquivo enviado no diretório temporário
      
      await saveTempFiles(tmp_dir, files)
			
      filename = get_available_records(Path(tmp_dir))[0]

      if not filename:
        raise HTTPException(status_code=400, detail="Nenhum registro WFDB encontrado no diretório temporário.")
      
      # Cria uma instância do analisador e executa a análise
      analyzer = ECGAnalyzer(tmp_dir)
      results = analyzer.save_complete_analysis(filename, int(frequency), period)
			
      return results

  except FileNotFoundError:
    raise HTTPException(status_code=404, detail="Registro não encontrado.")
