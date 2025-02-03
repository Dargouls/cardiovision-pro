from fastapi import APIRouter, HTTPException
from pathlib import Path
from typing import Dict
from .residual import ECGAnalyzer  # Import the ECGAnalyzer class
import os

from ..utils.getAvailableRecords import get_available_records
from ..utils.saveTempFiles import saveTempFiles
from ..utils.clearTempFiles import clear_upload_directory

app = APIRouter()

BASE_PATH = Path("uploads")  # Directory for ECG records
UPLOAD_DIR = './uploads'  # Define a valid directory within your project

# Route to analyze ECG artifacts
@app.post("/analyze-ecg-artifacts")
async def analyze_ecg_artifacts():
    """
    Endpoint to analyze ECG artifacts and generate visualizations.
    """
    try:
        # Get available files in the upload directory
        available_records = get_available_records()
        if not available_records:
            raise HTTPException(status_code=404, detail="No ECG records found in the upload directory.")
        
        # Use the first available record for analysis
        record_name = available_records[0]
        
        # Initialize the ECG analyzer
        analyzer = ECGAnalyzer(UPLOAD_DIR)
        
        # Perform ECG analysis
        analysis_results = analyzer.analyze_ecg(record_name)
        
        if not analysis_results:
            raise HTTPException(status_code=500, detail="Error analyzing ECG residual.")
        
        # Return the results in JSON format
        return analysis_results

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing ECG artifacts: {str(e)}")