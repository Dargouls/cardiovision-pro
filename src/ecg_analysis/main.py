# segmentation
import uvicorn
import wfdb
import numpy as np
import os
from .signal_processor import SignalProcessor
from .data_manager import ECGDataManager
from .config import ECGConfig

class ECGAnalyzer:
    def __init__(self, record, num_parts=24, samples_per_part=5000, desired_frequency=None):
        self.record = record
        self.num_parts = num_parts
        self.samples_per_part = samples_per_part
        self.total_samples = record.p_signal.shape[0]
        self.part_size = self.total_samples // num_parts
        self.desired_frequency = desired_frequency
        self.original_fs = record.fs  # Frequência original do registro
        
        # Inicializar componentes
        self.signal_processor = SignalProcessor()
        self.data_manager = ECGDataManager(self.signal_processor)

    def _resample_signal(self, signal, original_fs, desired_fs):
        """Reamostra o sinal para a frequência desejada usando interpolação linear."""
        if original_fs == desired_fs:
            return signal, np.arange(len(signal)) / original_fs
        
        duration = len(signal) / original_fs
        new_num_samples = int(duration * desired_fs)
        original_time = np.arange(len(signal)) / original_fs
        new_time = np.linspace(0, duration, new_num_samples, endpoint=False)
        return np.interp(new_time, original_time, signal), new_time

    def analyze(self):
        segments_data = []
        for part in range(self.num_parts):
            start_idx = part * self.part_size
            end_idx = min(start_idx + self.samples_per_part, self.total_samples)

            # Processar segmento original
            segment_data = self.data_manager.process_segment(
                self.record.p_signal,
                start_idx,
                end_idx,
                self.record.sig_name
            )

            # Extrair dados do segmento
            original_signal = segment_data["ECG"]["signal"]
            r_peaks = segment_data["ECG"]["r_peaks"]
            
            # Aplicar reamostragem se necessário
            if self.desired_frequency:
                resampled_signal, new_time = self._resample_signal(
                    original_signal,
                    self.original_fs,
                    self.desired_frequency
                )
                
                # Converter picos R para nova taxa de amostragem
                r_peaks_time = r_peaks / self.original_fs  # Converter para tempo absoluto
                new_r_peaks = (r_peaks_time * self.desired_frequency).astype(int)
                
                # Garantir que os índices estão dentro dos limites
                valid_peaks = [int(p) for p in new_r_peaks if 0 <= p < len(resampled_signal)]
                signal_output = resampled_signal.tolist()
                sampling_rate = self.desired_frequency
                r_peaks_output = valid_peaks
            else:
                signal_output = original_signal.tolist()
                sampling_rate = self.original_fs
                r_peaks_output = r_peaks.tolist()

            segments_data.append({
                "startTime": float(start_idx / self.original_fs),
                "endTime": float(end_idx / self.original_fs),
                "signal": signal_output,
                "rPeaks": r_peaks_output,
                "samplingRate": sampling_rate,
                "samplesPerPart": self.samples_per_part
            })
        
        return segments_data

def convert_numpy_to_native(value):
    return value.tolist() if isinstance(value, np.ndarray) else value

def analyze_ecg(record_path, num_parts=24, samples_per_part=5000, desired_frequency=None):
    record = wfdb.rdrecord(record_path)
    analyzer = ECGAnalyzer(
        record,
        num_parts,
        samples_per_part,
        desired_frequency
    )
    return analyzer.analyze()