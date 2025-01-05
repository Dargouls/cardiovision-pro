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
        Processa um segmento de dados do ECG.
        """
        segment_data = {}
        
        for lead_idx, lead_name in enumerate(leads):
            signal = raw_data[start_idx:end_idx, lead_idx]
            filtered_signal = self.signal_processor.apply_filters(signal)
            normalized_signal = self.signal_processor.normalize_signal(filtered_signal)
            peaks = self.signal_processor.detect_qrs_complexes(normalized_signal)
            
            segment_data[lead_name] = {
                "signal": normalized_signal,  # Manter como numpy array
                "r_peaks": peaks,  # Manter como numpy array
                "time_points": np.arange(len(normalized_signal)),  # Manter como numpy array
                "sampling_rate": ECGConfig.SAMPLE_RATE
            }
        
        return segment_data
    
    def save_segments_data(self, segments_data, filename='ecg_segments.json'):
        """
        Salva dados dos segmentos em arquivo JSON.
        """
        # Converter arrays numpy para listas antes de salvar
        json_data = {}
        for segment_key, segment in segments_data.items():
            json_data[segment_key] = {
                "start_time": segment["start_time"],
                "end_time": segment["end_time"],
                "leads_data": {
                    lead: {
                        "signal": data["signal"].tolist(),
                        "r_peaks": data["r_peaks"].tolist(),
                        "sampling_rate": data["sampling_rate"]
                    }
                    for lead, data in segment["leads_data"].items()
                }
            }
        
        with open(filename, 'w') as f:
            json.dump(json_data, f, indent=4)
