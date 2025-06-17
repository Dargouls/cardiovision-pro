from fastapi import APIRouter, HTTPException

from .residual import ECGAnalyzer  # Import the ECGAnalyzer class

import os

from ...utils.getAvailableRecords import get_available_records
from ...utils.saveTempFiles import saveTempFiles

GATEWAY_URL = os.getenv("GATEWAY_URL")

app = APIRouter()

# Route to analyze ECG artifacts
@app.post("/analyze-ecg-artifacts")
async def analyze_residual(
  UPLOAD_DIR: str
):
    """
    Endpoint to analyze ECG artifacts and generate visualizations.
    """
    try:
        # Get available files in the upload directory
        available_records = get_available_records(UPLOAD_DIR)[0]
        if not available_records:
            raise HTTPException(status_code=404, detail="No ECG records found in the upload directory.")
        
        # Initialize the ECG analyzer
        analyzer = ECGAnalyzer(UPLOAD_DIR)
        
        # Perform ECG analysis
        results = await analyzer.analyze_ecg(available_records)
        
        if not results:
            raise HTTPException(status_code=500, detail="Error analyzing ECG residual.")
            
        return results

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing ECG artifacts: {str(e)}")