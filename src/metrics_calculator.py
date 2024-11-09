# metrics_calculator.py
import numpy as np
from signal_processor import SignalProcessor
import json

class MetricsCalculator:
    """
    Classe para cálculo de métricas do ECG.
    """
    def __init__(self, signal_processor):
        self.signal_processor = signal_processor
    
    def calculate_metrics(self, signal):
        """
        Calcula métricas importantes do ECG.
        """
        filtered_signal = self.signal_processor.apply_filters(signal)
        r_peaks = self.signal_processor.detect_qrs_complexes(filtered_signal)
        
        # Calcular intervalos RR
        rr_intervals = np.diff(r_peaks) / ECGConfig.SAMPLE_RATE
        
        metrics = {
            "heart_rate_bpm": round(60 / np.mean(rr_intervals), 2),
            "hrv_sdnn_ms": round(np.std(rr_intervals) * 1000, 2),
            "mean_rr_interval_ms": round(np.mean(rr_intervals) * 1000, 2),
            "qrs_rate_per_minute": round(len(r_peaks) / (len(signal) / ECGConfig.SAMPLE_RATE / 60), 2),
            "mean_r_amplitude_mv": round(np.mean(filtered_signal[r_peaks]), 4),
            "r_amplitude_variability": round(np.std(filtered_signal[r_peaks]), 4),
            "signal_energy": round(np.sum(filtered_signal**2), 2),
            "rhythm_irregularity_index": round(np.std(rr_intervals) / np.mean(rr_intervals), 4),
            "mean_power_spectral_density": round(np.mean(np.abs(np.fft.fft(filtered_signal))**2), 2),
            "zero_crossing_rate": round(np.sum(np.diff(np.signbit(filtered_signal)) != 0) / len(filtered_signal), 4)
        }
        
        return metrics
    
    def save_metrics(self, metrics, filename='ecg_metrics.json'):
        """
        Salva as métricas em arquivo JSON.
        """
        with open(filename, 'w') as f:
            json.dump(metrics, f, indent=4)
