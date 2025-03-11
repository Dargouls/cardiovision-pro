from fastapi import APIRouter, HTTPException, Form
from typing import Optional

from ...utils.getAvailableRecords import get_available_records

from .segmentation_st import STSegmentDetector

app = APIRouter()

@app.post("/segmentation-st")
async def get_segmentation_st(
    upload_dir: str = Form(...),
    st_offset_ms: Optional[int] = Form(...)
):
    try:
        print('Etapa: Segmentation ST')
        record_path = f"{upload_dir}/{get_available_records(upload_dir)[0]}"

        analyzer = STSegmentDetector(record_path, st_offset_ms)
        
        results = await analyzer.get_results()
        return results
    except Exception as e:
        print(f'Erro em segmentation-st: {e}')
        raise HTTPException(500, detail=str(e))