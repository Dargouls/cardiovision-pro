import wfdb
import neurokit2 as nk
import numpy as np
from collections import defaultdict

class ECGArrhythmiaAnalyzer:
    def __init__(self, record_path, frequency=None):
        self.record_path = record_path
        self.fs = None
        self.analysis_fs = frequency
        self.signals = None
        self.total_signal = None
        self.arrhythmias = []

    def load_and_preprocess(self):
        self.signals, fields = wfdb.rdsamp(self.record_path)
        self.fs = fields['fs']
        self.analysis_fs = self.analysis_fs if self.analysis_fs is not None else self.fs
        # Usar apenas o primeiro canal (índice 0) em vez da média
        self.total_signal = self.signals[:, 0]  # Alteração aqui
        if self.analysis_fs != self.fs:
            duration = len(self.total_signal) / self.fs
            num_samples = int(duration * self.analysis_fs)
            self.total_signal = nk.signal_resample(self.total_signal, sampling_rate=self.fs, desired_sampling_rate=self.analysis_fs)
        return self.total_signal

    def detect_arrhythmias(self, max_types=5):
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
        
        self._balance_arrhythmia_selection(r_peaks)
        return self.arrhythmias

    def _balance_arrhythmia_selection(self, all_r_peaks):
        selected_arrhythmias = []
        type_count = defaultdict(int)
        
        # Ordenar arritmias por contagem decrescente
        sorted_arrhythmias = sorted(self.arrhythmias, key=lambda x: -x["count"])
        
        # Passo 1: Determinar o comprimento máximo dos segmentos
        segments_lengths = []
        for arr in sorted_arrhythmias:
            if len(selected_arrhythmias) >= 5:
                break
            if type_count[arr["type"]] < 2 or len(selected_arrhythmias) < 5:
                start = max(0, arr["positions"][0] - int(self.analysis_fs * 1))
                end = min(len(self.total_signal), arr["positions"][-1] + int(self.analysis_fs * 1))
                segments_lengths.append(end - start)
                type_count[arr["type"]] += 1
        
        max_length = max(segments_lengths) if segments_lengths else 0
        
        # Passo 2: Resetar contador e ajustar os segmentos
        type_count = defaultdict(int)
        selected_arrhythmias = []
        for arr in sorted_arrhythmias:
            if len(selected_arrhythmias) >= 5:
                break
            if type_count[arr["type"]] < 2 or len(selected_arrhythmias) < 5:
                # Definir início e fim inicial do segmento
                start = max(0, arr["positions"][0] - int(self.analysis_fs * 1))
                end = min(len(self.total_signal), arr["positions"][-1] + int(self.analysis_fs * 1))
                
                # Estender o segmento até max_length usando o sinal original
                if end - start < max_length:
                    extended_end = min(start + max_length, len(self.total_signal))
                    signal_segment = self.total_signal[start:extended_end]
                else:
                    signal_segment = self.total_signal[start:end]
                
                # Converter para lista
                signal_segment = signal_segment.tolist()
                
                # Ajustar posições de destaque e picos R
                highlight_start = int(arr["positions"][0] - start)
                highlight_end = int(arr["positions"][-1] - start)
                segment_peaks = [int(pos - start) for pos in all_r_peaks if start <= pos < start + max_length]
                
                # Adicionar o segmento ajustado à lista de arritmias selecionadas
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
            "Possible AFib": "Severe",
            "Unspecified Arrhythmia": "Unknown"
        }
        return severity_map.get(arrhythmia_type, "Unknown")

    def get_results(self):
        return {
            "arrhythmias": {
                "sampling_rate": int(self.analysis_fs),
                "arrhythmias": self.arrhythmias
            }
        }