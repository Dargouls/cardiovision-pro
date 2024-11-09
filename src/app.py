# Importações
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import wfdb
from typing import Optional
import uvicorn
from threading import Thread

# Definição da API FastAPI
app = FastAPI()

class AnalyzeRequest(BaseModel):
    record_path: str  # Caminho do arquivo do ECG
    num_parts: Optional[int] = 24
    samples_per_part: Optional[int] = 5000

@app.post("/analyze_ecg")
def analyze_ecg(data: AnalyzeRequest):
    try:
        # Carregar o registro do arquivo de ECG
        record = wfdb.rdrecord(data.record_path)
        
        # Criar a instância do analisador (essa parte depende da implementação do ECGAnalyzer)
        analyzer = ECGAnalyzer(record, data.num_parts, data.samples_per_part)
        
        # Executar a análise
        analyzer.analyze()
        
        # Retornar uma resposta de sucesso
        return {
            "message": "Análise completa. Arquivos salvos.",
            "output_files": ["ecg_metrics.json", "ecg_segments.json"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def read_root():
    return {"message": "Bem-vindo à API de Análise de ECG com FastAPI!"}

# Função para rodar o servidor Uvicorn dentro de um thread com outra porta
def run_uvicorn():
    uvicorn.run(app, host="0.0.0.0", port=8001)  # Mudei a porta para 8001

# Rodar o servidor FastAPI dentro de uma thread para evitar bloqueio da execução
thread = Thread(target=run_uvicorn)
thread.start()

