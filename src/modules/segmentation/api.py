from fastapi import HTTPException, File, UploadFile, Form, APIRouter

import wfdb

from ...utils.getAvailableRecords import get_available_records
from ...utils.saveTempFiles import saveTempFiles
from ...utils.copyWfdb import copy_record

from .main import ECGAnalyzer

from dotenv import load_dotenv
from pathlib import Path
from typing import List, Optional

import tempfile
import os
import asyncio

# Lock global para serializar acesso ao WFDB / Suspender corrotinas
wfdb_lock = asyncio.Lock()

# Carregar as variáveis do .env
load_dotenv()

# Obter a URL do gateway
GATEWAY_URL = os.getenv("GATEWAY_URL")

app = APIRouter()

@app.post("/analyze_segmentation")
async def get_segments(
    upload_dir: str = Form(...),
    num_parts: Optional[int] = Form(...),
    frequency: Optional[int] = Form(...),
    samples_per_part: Optional[int] = Form(...),
):
    try:
        print("Etapa: Segmentação")
        print('upload_dir in segment: ', upload_dir)
        available_records = get_available_records(upload_dir)[0]
        print('available_records in segment: ', available_records)
        if not available_records:
            raise HTTPException(status_code=400, detail="Nenhum registro WFDB encontrado.")
        
        hea_file = available_records
        base_path = f"{upload_dir}/{hea_file}"
        record = await copy_record(base_path)

        analyzer = ECGAnalyzer(record, num_parts, samples_per_part, frequency)
        segments_data = analyzer.analyze()
        
        return segments_data

    except Exception as e:
        import traceback
        print("Erro em segmentar:", str(e))
        traceback.print_exc()  # Imprime o traceback completo
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/update_segmentation")
async def reanalyze_segments(
    num_parts: Optional[int] = Form(4),         # Número de partes
    samples_per_part: Optional[int] = Form(5000),  # Número de amostras por parte
    frequency: Optional[int] = Form(None),
    files: List[UploadFile] = File(...),           # Arquivos a serem enviados
):
    try:
        # Cria um diretório temporário exclusivo para esta requisição
        with tempfile.TemporaryDirectory() as tmp_dir:
            await saveTempFiles(tmp_dir, files)
            
            # Utiliza a função get_available_records para identificar os registros disponíveis
            filename = get_available_records(Path(tmp_dir))[0]
            if not filename:
                raise HTTPException(status_code=400, detail="Nenhum registro WFDB encontrado no diretório temporário.")
            
            # Seleciona o primeiro registro disponível; se houver mais de um, pode-se implementar lógica adicional
            record_base = os.path.join(tmp_dir, filename)
            
            try:
                # wfdb.rdrecord procura arquivos com o mesmo prefixo (ex.: .hea, .dat, .atr)
                record = wfdb.rdrecord(record_base)
            except Exception as e:
                print(f"Erro ao tentar carregar o arquivo WFDB: {e}")
                raise HTTPException(status_code=500, detail="Erro ao carregar o arquivo WFDB.")
            
            # Cria a instância do analisador e executa a análise
            analyzer = ECGAnalyzer(record, num_parts, samples_per_part, frequency)
            segments_data = analyzer.analyze()
            
            return segments_data
        # Ao sair do bloco 'with', o diretório temporário e seus arquivos são removidos automaticamente.
    except Exception as e:
        print(f"Erro ao processar a requisição: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))