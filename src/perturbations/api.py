from fastapi import APIRouter, HTTPException
from pathlib import Path
from typing import List, Dict
from .perturbations import AnalisadorInterferencia  # Import the AnalisadorInterferencia class
import os

from ..utils.getAvailableRecords import get_available_records
from ..utils.saveTempFiles import saveTempFiles
from ..utils.clearTempFiles import clear_upload_directory

app = APIRouter()

BASE_PATH = Path("uploads")  # Directory for ECG records
UPLOAD_DIR = './uploads'  # Define a valid directory within your project

# Route to analyze perturbations in ECG
@app.post("/perturbations")
async def analyze_perturbations():
    """
    Endpoint to analyze perturbations and technical issues in ECG records.
    """
    try:
        # Get available files in the upload directory
        filename = get_available_records()[0]
        
        # Initialize the perturbation analyzer
        analyzer = AnalisadorInterferencia(UPLOAD_DIR)
        
        # Dictionary to store results for each file
        results: Dict[str, Dict] = {}

        # Perform perturbation analysis
        analysis_results = analyzer.analisar_interferencias(filename)
        print(analysis_results)
        # Clear the upload directory after processing
        clear_upload_directory(UPLOAD_DIR)

        # Return the results in JSON format
        return {"analyzed_files": analysis_results}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing perturbations: {str(e)}")