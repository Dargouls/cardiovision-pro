from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from typing import List, Optional
import os
import wfdb
from .main import ECGAnalyzer

# Definir o diretório onde os arquivos serão salvos
UPLOAD_DIR = "./uploads"  # Defina um diretório válido dentro do seu projeto

# Garantir que o diretório de uploads existe
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

app = FastAPI()

@app.post("/analyze_ecg")
async def analyze_ecg(
    num_parts: Optional[int] = Form(1),  # Número de partes
    samples_per_part: Optional[int] = Form(5000),  # Número de amostras por parte
    files: List[UploadFile] = File(...),  # Arquivos a serem enviados
):
    try:
        # Processar os arquivos recebidos
        file_paths = []
        for file in files:
            file_path = os.path.join(UPLOAD_DIR, file.filename)
            with open(file_path, "wb") as f:
                f.write(await file.read())
            file_paths.append(file_path)

        # Processar o primeiro arquivo recebido
        record = wfdb.rdrecord(file_paths[0])

        # Criar a instância do analisador
        analyzer = ECGAnalyzer(record, num_parts, samples_per_part)

        # Executar a análise e capturar os resultados
        metrics, segments_data = analyzer.analyze(return_data=True)
        return {
            "message": "Análise completa.",
            "metrics": metrics,
            "segments": segments_data,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def read_root():
    return {"message": "Bem-vindo à API de Análise de ECG com FastAPI!"}
