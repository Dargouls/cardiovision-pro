from fastapi import APIRouter, HTTPException, Form, UploadFile, File
from typing import List, Optional

import os
import tempfile

from ..utils.getAvailableRecords import get_available_records
from ..utils.saveTempFiles import saveTempFiles

from .metadata import decodeXCM, AdvancedMedicalReportExtractor  # Importa a função de extração de metadados

app = APIRouter()

@app.post("/get_metadata")
async def get_metadata(
  study_id: str = Form(...),
  user_id: str = Form(...),
  files: List[UploadFile] = File(...),  # Arquivos a serem enviados
):
  try:
    with tempfile.TemporaryDirectory() as temp_dir:
      filepaths = await saveTempFiles(temp_dir, files)

      if not filepaths:
          print("Nenhum registro encontrado no diretório informado.")
          raise FileNotFoundError("Nenhum registro encontrado no diretório informado.")
      
      metadata = decodeXCM(filepaths[0])
      # extractor = AdvancedMedicalReportExtractor(metadata)
       
      return {
          "metadata": metadata,
          "study_id": study_id,
          "user_id": user_id
        }
  except FileNotFoundError:
      raise HTTPException(status_code=404, detail="Registro não encontrado.")
