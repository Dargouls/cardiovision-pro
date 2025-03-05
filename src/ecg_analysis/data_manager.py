# data_manager.py
import json
import numpy as np
from .config import ECGConfig

class ECGDataManager:
    """
    Classe para gerenciamento de dados do ECG.
    """
    def __init__(self, signal_processor):
        self.signal_processor = signal_processor
    
    def process_segment(self, raw_data, start_idx, end_idx, leads):
        """
        Processa um segmento de dados do ECG e retorna uma lista de derivações,
        onde cada derivação é um dicionário com os atributos 'name', 'signal', 'r_peaks', etc.
        """
        segment_data = []
        
        for lead_idx, lead_name in enumerate(leads):
            signal = raw_data[start_idx:end_idx, lead_idx]
            signal = np.nan_to_num(signal, nan=0.0)

            filtered_signal = self.signal_processor.apply_filters(signal)
            normalized_signal = self.signal_processor.normalize_signal(filtered_signal)
            peaks = self.signal_processor.detect_qrs_complexes(normalized_signal)
            
            segment_data.append({
                "name": lead_name or '',  # nome da derivação
                "signal": normalized_signal,  # numpy array
                "r_peaks": peaks,  # numpy array
                "time_points": np.arange(len(normalized_signal)),  # numpy array
                "sampling_rate": ECGConfig.SAMPLE_RATE
            })
            
        return segment_data
    
    def save_segments_data(self, segments_data, filename='ecg_segments.json'):
        json_data = []
        for segment in segments_data:
            # Se cada segmento tiver uma chave "leads_data" que também é uma lista, itere sobre ela:
            leads_data = []
            for lead_data in segment["leads_data"]:
                leads_data.append({
                    "name": lead_data["name"],
                    "signal": lead_data["signal"].tolist(),
                    "r_peaks": lead_data["r_peaks"].tolist(),
                    "sampling_rate": lead_data["sampling_rate"]
                })
            json_data.append({
                "start_time": segment["startTime"],
                "end_time": segment["endTime"],
                "leads_data": leads_data,
                "samplesPerPart": segment["samplesPerPart"],
                "samplingRate": segment["samplingRate"]
            })
        
        with open(filename, 'w') as f:
            json.dump(json_data, f, indent=4)
