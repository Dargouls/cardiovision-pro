# segmentation
import uvicorn
import wfdb
import numpy as np
import os
from .signal_processor import SignalProcessor
from .data_manager import ECGDataManager

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

            # Agora process_segment retorna uma lista de leads
            segment_leads = self.data_manager.process_segment(
                self.record.p_signal,
                start_idx,
                end_idx,
                self.record.sig_name
            )

            processed_leads = []
            for lead in segment_leads:
                original_signal = lead["signal"]
                r_peaks = lead["r_peaks"]

                if self.desired_frequency:
                    resampled_signal, new_time = self._resample_signal(
                        original_signal, self.original_fs, self.desired_frequency
                    )
                    r_peaks_time = r_peaks / self.original_fs  # converter para tempo
                    new_r_peaks = (r_peaks_time * self.desired_frequency).astype(int)
                    valid_peaks = [int(p) for p in new_r_peaks if 0 <= p < len(resampled_signal)]
                    
                    processed_leads.append({
                        "name": lead["name"],
                        "signal": resampled_signal.tolist(),
                        "r_peaks": valid_peaks,
                        "time_points": new_time.tolist()
                    })
                else:
                    processed_leads.append({
                        "name": lead["name"],
                        "signal": original_signal.tolist(),
                        "r_peaks": r_peaks.tolist(),
                        "time_points": np.arange(len(original_signal)).tolist()
                    })

            segments_data.append({
                "startTime": float(start_idx / self.original_fs),
                "endTime": float(end_idx / self.original_fs),
                "derivations": processed_leads,
                "samplingRate": self.desired_frequency or self.original_fs,
                "samplesPerPart": self.samples_per_part
            })
        
        return segments_data
