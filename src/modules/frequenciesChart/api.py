from fastapi import APIRouter, UploadFile, File, HTTPException, Form

from .ecg_analyzer import ECGAnalyzer
from ...utils.getAvailableRecords import get_available_records
from ...utils.saveTempFiles import saveTempFiles

from typing import Optional
from pathlib import Path
import os
import tempfile

GATEWAY_URL = os.getenv("GATEWAY_URL")

app = APIRouter()

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
