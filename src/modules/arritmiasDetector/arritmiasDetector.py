import wfdb
import neurokit2 as nk
import numpy as np
from collections import defaultdict

class ECGArrhythmiaAnalyzer:
    def __init__(self, record_path, frequency=None):
        self.record_path = record_path
        self.fs = None
        self.analysis_fs = frequency  # Frequência desejada
        self.signals = None
        self.total_signal = None
        self.arrhythmias = []

    def load_and_preprocess(self):
        self.signals, fields = wfdb.rdsamp(self.record_path)
        self.fs = fields['fs']
        self.analysis_fs = self.analysis_fs if self.analysis_fs is not None else self.fs
        self.total_signal = self.signals[:, 0]  # Primeiro canal
        if self.analysis_fs != self.fs:
            duration = len(self.total_signal) / self.fs
            num_samples = int(duration * self.analysis_fs)
            self.total_signal = nk.signal_resample(self.total_signal, sampling_rate=self.fs, desired_sampling_rate=self.analysis_fs)
        return self.total_signal

    def detect_arrhythmias(self, max_arrhythmias=5):
        _, peaks = nk.ecg_peaks(self.total_signal, sampling_rate=self.analysis_fs)
        r_peaks = np.array(peaks['ECG_R_Peaks'])
        r_peaks = r_peaks[r_peaks > 0]

        rr_intervals = np.diff(r_peaks) / self.analysis_fs * 1000
        rr_intervals = rr_intervals[(rr_intervals > 300) & (rr_intervals < 2000)]
        
        mean_rr = np.mean(rr_intervals)
        std_rr = np.std(rr_intervals)
        p25, p75 = np.percentile(rr_intervals, [25, 75])

        arrhythmia_regions = defaultdict(list)
        for i in range(1, len(rr_intervals)):
            delta = abs(rr_intervals[i] - rr_intervals[i-1])
            if rr_intervals[i] > mean_rr + 2 * std_rr:
                key = "Bradycardia"
            elif rr_intervals[i] < mean_rr - 2 * std_rr:
                key = "Tachycardia"
            elif delta > 350:
                key = "PVC"
            elif std_rr > 120 and p75 - p25 > 200:
                key = "Possible AFib"
            else:
                continue
            if arrhythmia_regions[key] and r_peaks[i] - arrhythmia_regions[key][-1][-1] < self.analysis_fs * 2:
                arrhythmia_regions[key][-1].append(r_peaks[i])
            else:
                arrhythmia_regions[key].append([r_peaks[i]])
        
        self.arrhythmias = []
        for key, regions in arrhythmia_regions.items():
            for region in regions:
                start = region[0]
                end = region[-1]
                self.arrhythmias.append({
                    "type": key,
                    "count": len(region),
                    "positions": [int(pos) for pos in region],
                    "severity": self._get_severity(key)
                })
        
        self._balance_arrhythmia_selection(r_peaks, max_arrhythmias)
        return self.arrhythmias

    def _balance_arrhythmia_selection(self, all_r_peaks, max_arrhythmias):
        selected_arrhythmias = []
        type_count = defaultdict(int)
        segment_duration = 7  # 7 segundos
        
        # Ordenar arritmias por contagem decrescente
        sorted_arrhythmias = sorted(self.arrhythmias, key=lambda x: -x["count"])
        
        # Calcular tamanho do segmento em amostras
        segment_length = int(segment_duration * self.analysis_fs)
        
        for arr in sorted_arrhythmias:
            if len(selected_arrhythmias) >= max_arrhythmias:
                break
            if type_count[arr["type"]] < 2 or len(selected_arrhythmias) < max_arrhythmias:
                # Centralizar o segmento na arritmia
                center = arr["positions"][0]
                start = max(0, center - segment_length // 2)
                end = min(len(self.total_signal), start + segment_length)
                
                # Ajustar início se o fim ultrapassar o sinal
                if end > len(self.total_signal):
                    end = len(self.total_signal)
                    start = max(0, end - segment_length)
                
                signal_segment = self.total_signal[start:end].tolist()
                
                # Ajustar posições de destaque para ficarem dentro do segmento
                highlight_start = max(0, int(arr["positions"][0] - start))
                highlight_end = min(len(signal_segment) - 1, int(arr["positions"][-1] - start))
                segment_peaks = [int(pos - start) for pos in all_r_peaks if start <= pos < end]
                
                selected_arrhythmias.append({
                    "type": arr["type"],
                    "severity": arr["severity"],
                    "signal": signal_segment,
                    "highlight": {
                        "start": highlight_start,
                        "end": highlight_end
                    },
                    "r_peaks": segment_peaks
                })
                type_count[arr["type"]] += 1
        
        self.arrhythmias = selected_arrhythmias

    def _get_severity(self, arrhythmia_type):
        severity_map = {
            "Tachycardia": "Moderate",
            "Bradycardia": "Moderate",
            "PVC": "Mild",
            "Possible AFib": "Severe"
        }
        return severity_map.get(arrhythmia_type, "Unknown")

    def get_results(self):
        return {
            "arrhythmias": {
                "sampling_rate": int(self.analysis_fs),
                "arrhythmias": self.arrhythmias
            }
        }