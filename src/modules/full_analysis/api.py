from fastapi import APIRouter, UploadFile, File, HTTPException, Form

from .full_analysis import ECGAnalyzer
from ...utils.getAvailableRecords import get_available_records

import os

GATEWAY_URL = os.getenv("GATEWAY_URL")

app = APIRouter()

@app.post("/full_analysis")
async def get_full_analysis(
  UPLOAD_DIR: str = Form(...),
	frequency: str = Form(...),
):
	"""
	Endpoint para analisar um registro de ECG.
	"""
	print('Iniciando análise completa do ECG...')

	try:
		filename = get_available_records(UPLOAD_DIR)[0]
		analyzer = ECGAnalyzer(UPLOAD_DIR)
		results = await analyzer.save_complete_analysis(filename, int(frequency))

		return results
	
	except FileNotFoundError:
		raise HTTPException(status_code=404, detail="Registro não encontrado.")
	
@app.get("/health_check")
async def Hello():
    """
    Endpoint de verificação de saúde da API.
    """
    return {"message": "API está funcionando corretamente!"}