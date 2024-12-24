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
async def get_metrics(files: List[UploadFile] = File(...)):
    """
    Endpoint para fazer upload de um registro de ECG.
    """
    try:
      file_paths = []
      files = sorted(files, key=lambda f: f.filename)
      for file in files:
        try:
          print(f"Salvando arquivo: {file.filename}")
          file_path = os.path.join(UPLOAD_DIR, file.filename)
          
          with open(file_path, "wb") as f:
              f.write(await file.read())
          file_paths.append(file_path)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erro ao salvar arquivo {file.filename}: {str(e)}")
      results = metrics.save_complete_analysis(UPLOAD_DIR + '/418')

      return results
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Registro não encontrado.")

@app.post("/frequencies_chart")
async def analyze_record(files: List[UploadFile] = File(...)):
    """
    Endpoint para analisar um registro de ECG.
    """      
    try:
      file_paths = []
      files = sorted(files, key=lambda f: f.filename)
            
      for file in files:
        try:
          file_path = os.path.join(UPLOAD_DIR, file.filename)
          
          with open(file_path, "wb") as f:
              f.write(await file.read())
          file_paths.append(file_path)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Erro ao salvar arquivo {file.filename}: {str(e)}")

      filename = analyzer.get_available_records()[0]
      results = analyzer.save_complete_analysis(filename)
      # filename = analyzer.get_available_records()[0]
      # results = analyzer.analyze_record(filename)
      return {"record_name": file.filename, "results": results}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Registro não encontrado.")