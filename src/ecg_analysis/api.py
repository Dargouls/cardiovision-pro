import logging

from fastapi import HTTPException, File, UploadFile, Form, APIRouter

from ..utils.getAvailableRecords import get_available_records
from ..utils.saveTempFiles import saveTempFiles
from ..ecg_analysis.main import ECGAnalyzer

from typing import List, Optional
import tempfile
import os
import json
import httpx
from dotenv import load_dotenv
from pathlib import Path
import wfdb

# Carregar as variáveis do .env
load_dotenv()

# Obter a URL do gateway
GATEWAY_URL = os.getenv("GATEWAY_URL")

app = APIRouter()

@app.post("/analyze_segmentation")
async def get_segments(
    study_id: str = Form(...),
    user_id: str = Form(...),
    upload_dir: str = Form(...),
    num_parts: Optional[int] = Form(4),         # Número de partes
    samples_per_part: Optional[int] = Form(5000),  # Número de amostras por parte
    file_paths: List[str] = Form([]),
):
    try:
        # Obter o primeiro registro disponível no diretório
        available_records = get_available_records(upload_dir)
        if not available_records:
            raise HTTPException(status_code=400, detail="Nenhum registro WFDB encontrado.")
        hea_file = available_records[0]

        # Tentar ler o registro WFDB (concatenando o caminho e o nome do arquivo)
        try:
            record = wfdb.rdrecord(f"{upload_dir}/{hea_file}")
        except Exception as e:
            print(f"Erro ao tentar carregar o arquivo: {e}")
            raise HTTPException(status_code=500, detail="Erro ao carregar o arquivo WFDB.")

        # Instanciar o analisador e executar a análise
        analyzer = ECGAnalyzer(record, num_parts, samples_per_part)
        segments_data = analyzer.analyze()

        # Criar um arquivo JSON temporário com os dados de segmentação
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json", encoding="utf-8") as temp_file:
            json.dump(segments_data, temp_file)
            temp_file_path = temp_file.name

        # Enviar o arquivo JSON via multipart/form-data para o gateway
        async with httpx.AsyncClient() as client:
            with open(temp_file_path, "rb") as json_file:
                files = {
                    "study_id": (None, study_id),
                    "user_id": (None, user_id),
                    "module": (None, "segmentation"),
                    "files": ("segmentatin.json", json_file, "application/json"),
                }
                gateway_response = await client.post(f"{GATEWAY_URL}/save-module", files=files)
                gateway_response.raise_for_status()
                gateway_result = gateway_response.json()  # Ex.: { "message": "Dados recebidos com sucesso" }

        # Remover o arquivo temporário após o envio
        os.remove(temp_file_path)

        # Retornar o status conforme a resposta do gateway
        return {
            "status": 'OK'
        }

    except httpx.HTTPStatusError as http_err:
        raise HTTPException(status_code=http_err.response.status_code,
                            detail=f"Erro no gateway: {http_err.response.text}")
    except Exception as e:
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
            
            print(filename, num_parts,samples_per_part, frequency)
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
            print('análise')
            segments_data = analyzer.analyze()
            
            return segments_data
        # Ao sair do bloco 'with', o diretório temporário e seus arquivos são removidos automaticamente.
    except Exception as e:
        print(f"Erro ao processar a requisição: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))