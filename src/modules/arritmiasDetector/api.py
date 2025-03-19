from fastapi import APIRouter, HTTPException, Form
from typing import Optional

from ...utils.getAvailableRecords import get_available_records

from .arritmiasDetector import ECGArrhythmiaAnalyzer

app = APIRouter()

@app.post("/arrhythmias")
async def get_arrhythmias(
    upload_dir: str = Form(...),
    frequency: Optional[int] = Form(...)
):
    try:
        print('Etapa: Detectando Arritmias')
        record_path = f"{upload_dir}/{get_available_records(upload_dir)[0]}"

        analyzer = ECGArrhythmiaAnalyzer(record_path, frequency)
        analyzer.load_and_preprocess()
        analyzer.detect_arrhythmias()
        results = analyzer.get_results()
        
        return results
    except Exception as e:
        print(f'Erro em arritmias: {e}')
        raise HTTPException(500, detail=str(e))