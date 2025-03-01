import wfdb
import numpy as np
from scipy.signal import welch
from scipy.interpolate import interp1d
import neurokit2 as nk
import pywt
import nolds

class HolterAnalyzer:
    def __init__(self, record_path):
        """Inicializa o analisador Holter com o caminho local do registro."""
        self.record_path = record_path
        self._load_data()

    def _load_data(self):
        """Carrega o sinal ECG e as anotações dos arquivos locais."""
        self.record = wfdb.rdrecord(self.record_path)
        self.annotation = wfdb.rdann(self.record_path, 'atr')
        self.ecg_signal = self.record.p_signal[:, 0]
        self.fs = self.record.fs
        self.t = np.arange(len(self.ecg_signal)) / self.fs
        self.t_hours = (self.t).tolist()  # Eixo x para o gráfico de FC

    def process_ecg(self):
        """Processa o sinal ECG para detectar picos R, calcular intervalos RR e frequência cardíaca."""
        signals, info = nk.ecg_process(self.ecg_signal, sampling_rate=self.fs)
        self.r_peaks = info['ECG_R_Peaks']
        self.rr_intervals = np.diff(self.r_peaks) / self.fs
        self.time_rr = self.r_peaks[:-1] / self.fs
        self.hr = 60 / self.rr_intervals
        hr_interpolator = interp1d(
            self.time_rr, self.hr, kind='linear', bounds_error=False,
            fill_value=(self.hr[0], self.hr[-1])
        )
        self.hr_full = hr_interpolator(self.t)

    def detect_events_wavelet(self):
        """Detecta eventos anormais no sinal ECG usando Wavelet Transform."""
        coeffs = pywt.wavedec(self.ecg_signal, 'db4', level=5)
        cD5 = coeffs[-1]
        threshold = 2 * np.std(cD5)
        anomaly_indices = np.where(np.abs(cD5) > threshold)[0]
        self.anomaly_times = self.t[anomaly_indices * (len(self.t) // len(cD5))]

    def map_annotations(self):
        """Mapeia anotações do arquivo .atr para eventos ventriculares e supraventriculares."""
        self.ventricular_event_times = []
        self.supraventricular_event_times = []
        for i, ann in enumerate(self.annotation.sample):
            time = ann / self.fs
            if self.annotation.symbol[i] in ['V', 'F', 'Q']:
                self.ventricular_event_times.append(time)
            elif self.annotation.symbol[i] in ['A', 'S']:
                self.supraventricular_event_times.append(time)

    def approximate_entropy(self, signal, m=2):
        """Calcula a entropia amostral (SampEn) do sinal usando nolds."""
        if len(signal) < m + 1:
            return 0  # Retorna 0 se o sinal for muito curto
        return nolds.sampen(signal, emb_dim=m)

    def classify_beats(self):
        """Classifica os batimentos como normais, PVC ou PAC usando Wavelet e entropia."""
        self.beat_classes = ['normal'] * len(self.r_peaks)
        entropy_values = []
        for i in range(len(self.r_peaks) - 1):
            window = self.ecg_signal[self.r_peaks[i]:self.r_peaks[i+1]]
            entropy = self.approximate_entropy(window) if len(window) > 10 else 0
            entropy_values.append(entropy)
        self.entropy_threshold = np.percentile(entropy_values, 95)

        for idx, r_peak in enumerate(self.r_peaks):
            time = r_peak / self.fs
            if any(abs(time - v_time) < 0.1 for v_time in self.ventricular_event_times) or \
               any(abs(time - a_time) < 0.1 for a_time in self.anomaly_times):
                self.beat_classes[idx] = 'PVC'
            elif any(abs(time - s_time) < 0.1 for s_time in self.supraventricular_event_times) or \
                 (idx < len(entropy_values) and entropy_values[idx] > self.entropy_threshold):
                self.beat_classes[idx] = 'PAC'
        self.beat_classes_num = np.array([0 if cls == 'normal' else 1 if cls == 'PVC' else 2 for cls in self.beat_classes])

    def spectral_analysis(self):
        """Realiza análise espectral dos intervalos RR para obter o espectro de potência."""
        sampling_freq = 4
        dt = 1 / sampling_freq
        uniform_time = np.arange(self.time_rr[0], self.time_rr[-1], dt)
        rr_interpolator = interp1d(
            self.time_rr, self.rr_intervals, kind='linear',
            bounds_error=False, fill_value=(self.rr_intervals[0], self.rr_intervals[-1])
        )
        resampled_rr = rr_interpolator(uniform_time)
        self.freqs, self.power_spectrum = welch(resampled_rr, fs=sampling_freq, nperseg=1024)
        self.power_spectrum *= 1e6

    def calculate_hrv(self):
        """Calcula métricas de variabilidade da frequência cardíaca (HRV)."""
        self.rmssd = np.sqrt(np.mean(np.diff(self.rr_intervals)**2))
        self.sdnn = np.std(self.rr_intervals)

    def get_results(self):
        """Retorna os resultados da análise em um dicionário JSON, incluindo dados para gráficos."""
        results = {
            "heart_rate": {
                # "mean": float(np.mean(self.hr)),
                # "min": float(np.min(self.hr)),
                # "max": float(np.max(self.hr)),
                "t_hours": self.t_hours,                # Tempo em horas para o gráfico de FC
                "hr_full": self.hr_full.tolist()          # Valores da FC (bpm)
            },
            "rr_intervals": {
                # "time_hours": (self.time_rr).tolist(), # Tempo dos intervalos em segundos
                "values": self.rr_intervals.tolist()            # Valores dos intervalos RR (s)
            },
            "events": {
                "ventricular": self.ventricular_event_times,          # Tempos dos eventos ventriculares (segundos)
                "supraventricular": self.supraventricular_event_times   # Tempos dos eventos supraventriculares (segundos)
            },
            "spectral_analysis": {
                "freqs": self.freqs.tolist(),               # Frequências para o gráfico do espectro
                "power_spectrum": self.power_spectrum.tolist()  # Valores de potência para cada frequência
            },
            "hrv": {
                "rmssd": float(self.rmssd),
                "sdnn": float(self.sdnn)
            },
            "beat_classification": {
                # "classes": self.beat_classes,
                "counts": {
                    "normal": int(np.sum(self.beat_classes_num == 0)),
                    "PVC": int(np.sum(self.beat_classes_num == 1)),
                    "PAC": int(np.sum(self.beat_classes_num == 2))
                }
            }
        }
        return results

    def analyze(self):
        """Executa a análise completa do registro ECG e retorna os resultados em JSON."""
        self.process_ecg()
        self.detect_events_wavelet()
        self.map_annotations()
        self.classify_beats()
        self.spectral_analysis()
        self.calculate_hrv()
        return self.get_results()

# Exemplo de uso:
# analyzer = HolterAnalyzer('/content/uploads/100')
# results = analyzer.analyze()
# print(results)
