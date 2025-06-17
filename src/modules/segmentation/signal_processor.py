# signal_processor.py
import numpy as np
from scipy.signal import butter, filtfilt, find_peaks
from .config import ECGConfig

class SignalProcessor:
    """
    Classe para processamento de sinais ECG.
    """
    def __init__(self):
        self.config = ECGConfig()
    
    def apply_filters(self, signal):
        """
        Aplica filtros passa-alta e passa-baixa ao sinal.
        """
        nyquist = self.config.SAMPLE_RATE / 2
        
        # Filtro passa-alta
        high_pass = butter(2, self.config.FILTER_HIGH_PASS/nyquist, 'high')
        signal = filtfilt(high_pass[0], high_pass[1], signal)
        
        # Filtro passa-baixa
        low_pass = butter(2, self.config.FILTER_LOW_PASS/nyquist, 'low')
        signal = filtfilt(low_pass[0], low_pass[1], signal)
        
        return signal
    
    def detect_qrs_complexes(self, signal):
        """
        Detecta complexos QRS no sinal.
        """
        min_distance = int(self.config.QRS_MIN_DISTANCE * self.config.SAMPLE_RATE)
        peaks, _ = find_peaks(signal,
                            distance=min_distance,
                            height=0.1,
                            prominence=0.1)
        return peaks
    
    def normalize_signal(self, signal):
        """
        Normaliza o sinal para ter média zero e desvio padrão unitário.
        """
        normalized = signal - np.mean(signal)
        normalized = normalized / np.std(normalized) * 0.5
        return normalized
