import logging

from fastapi import HTTPException, File, UploadFile, Form, APIRouter

from ..utils.getAvailableRecords import get_available_records
from ..utils.saveTempFiles import saveTempFiles
from ..utils.clearTempFiles import clear_upload_directory

from typing import List, Optional
import os
import wfdb
from ..ecg_analysis.main import ECGAnalyzer

app = APIRouter()

@app.post("/analyze_ecg_base")
async def get_segments(
  upload_dir: str,
  num_parts: Optional[int] = Form(4),  # Número de partes
  samples_per_part: Optional[int] = Form(5000),  # Número de amostras por parte
  file_paths: list = Form([]),
):
  try:
    hea_file = get_available_records()[0]
    # Agora os arquivos estão ordenados, o que deve garantir que o arquivo .dat e .hea
    # sejam lidos na ordem correta
    try:
      record = wfdb.rdrecord(upload_dir + '/' + hea_file)  # Supondo que o primeiro arquivo seja o correto
    except Exception as e:
      print(f"Erro ao tentar carregar o arquivo: {e}")

    # Criar a instância do analisador
    analyzer = ECGAnalyzer(record, num_parts, samples_per_part)

    # Executar a análise e capturar os resultados
    segments_data = analyzer.analyze(return_data=True)
    
    return {
      "segments": segments_data,
    }

  except Exception as e:
    # Excluir os arquivos após o uso
      # for file_path in file_paths:
      #     os.remove(file_path)  # Remove o arquivo temporário
      # print('Limpar lixo')
      raise HTTPException(status_code=500, detail=str(e))