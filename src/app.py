from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from typing import List, Optional
import os
import wfdb
from .ecg_analysis.main import ECGAnalyzer

# Definir o diretório onde os arquivos serão salvos
UPLOAD_DIR = "./uploads"  # Defina um diretório válido dentro do seu projeto

# Garantir que o diretório de uploads existe
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

origins = [
    "*",
]

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

    
@app.post("/analyze_ecg")
async def analyze_ecg(
    num_parts: Optional[int] = Form(2),  # Número de partes
    samples_per_part: Optional[int] = Form(5000),  # Número de amostras por parte
    files: List[UploadFile] = File(...),  # Arquivos a serem enviados
):

    try:
        # Processar os arquivos recebidos e armazenar temporariamente
        file_paths = []
        # Limpar o diretório
        for file_path in file_paths:
            os.remove(file_path)  # Remove o arquivo temporário
        
        # Ordenar os arquivos antes de processá-los, de preferência primeiro .dat, depois .hea
        files = sorted(files, key=lambda f: f.filename)
        
        for file in files:
            file_path = os.path.join(UPLOAD_DIR, file.filename)
            with open(file_path, "wb") as f:
                f.write(await file.read())
            file_paths.append(file_path)
        
        print('criação de caminhos feita', file_paths)

        # Agora os arquivos estão ordenados, o que deve garantir que o arquivo .dat e .hea
        # sejam lidos na ordem correta
        try:
            record = wfdb.rdrecord(file_paths[0])  # Supondo que o primeiro arquivo seja o correto
        except Exception as e:
            print(f"Erro ao tentar carregar o arquivo: {e}")

        print('salvar arquivos feito')
        # Criar a instância do analisador
        analyzer = ECGAnalyzer(record, num_parts, samples_per_part)

        # Executar a análise e capturar os resultados
        metrics, segments_data = analyzer.analyze(return_data=True)
        print('Analizador de arquivos feito')

        # Excluir os arquivos após o uso
        for file_path in file_paths:
            os.remove(file_path)  # Remove o arquivo temporário
        print('Limpar lixo')

        return {
            "message": "Análise completa.",
            "metrics": metrics,
            "segments": segments_data,
        }

    except Exception as e:
      # Excluir os arquivos após o uso
        # for file_path in file_paths:
        #     os.remove(file_path)  # Remove o arquivo temporário
        # print('Limpar lixo')
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze_ecg_img")
async def analyze_ecg_img(
    num_parts: Optional[int] = Form(1),  # Número de partes
    samples_per_part: Optional[int] = Form(5000),  # Número de amostras por parte
    files: List[UploadFile] = File(...),  # Arquivos a serem enviados
):
    try:
        # Processar os arquivos recebidos
        file_paths = []
        
        # Limpar o diretório
        for file_path in file_paths:
            os.remove(file_path)  # Remove o arquivo temporário
        
        for file in files:
            # Usar o diretório de uploads definido
            file_path = os.path.join(UPLOAD_DIR, file.filename)
            with open(file_path, "wb") as f:
                f.write(await file.read())
            file_paths.append(file_path)

        # Exemplo de como pegar o primeiro arquivo para o processamento
        record = wfdb.rdrecord(file_paths[0])  # Supondo que você esteja analisando o primeiro arquivo

        # Criar a instância do analisador
        analyzer = ECGAnalyzer(record, num_parts, samples_per_part)

        # Executar a análise
        analyzer.analyze()

				 # Excluir os arquivos após o uso
        for file_path in file_paths:
            os.remove(file_path)  # Remove o arquivo temporário
        print('Limpar lixo')
        return {
            "message": "Análise completa. Arquivos salvos.",
            "output_files": ["ecg_metrics.json", "ecg_segments.json"]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
      
@app.get("/")
def healthCheck():
    return {"message": "Bem-vindo à API de Análise de ECG com FastAPI!"}