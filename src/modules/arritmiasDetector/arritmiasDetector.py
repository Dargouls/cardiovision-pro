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
        try:
            self.signals, fields = wfdb.rdsamp(self.record_path)
            self.fs = fields['fs']
            self.analysis_fs = self.analysis_fs if self.analysis_fs is not None else self.fs
            
            # Seleciona o primeiro canal, mas verifica se há dados
            if self.signals.size == 0 or self.signals.shape[1] == 0:
                raise ValueError("O sinal ECG está vazio")
                
            self.total_signal = self.signals[:, 0]  # Primeiro canal
            
            # Verifica se o sinal tem amplitude suficiente
            signal_range = np.max(self.total_signal) - np.min(self.total_signal)
            if signal_range < 0.1:  # Threshold mínimo de amplitude
                print(f"Aviso: Amplitude do sinal muito baixa ({signal_range:.6f})")
            
            if self.analysis_fs != self.fs:
                duration = len(self.total_signal) / self.fs
                num_samples = int(duration * self.analysis_fs)
                self.total_signal = nk.signal_resample(self.total_signal, sampling_rate=self.fs, desired_sampling_rate=self.analysis_fs)
            
            return self.total_signal
        except Exception as e:
            print(f"Erro ao carregar/preprocessar o sinal: {str(e)}")
            raise

    def detect_arrhythmias(self, max_arrhythmias=5):
        try:
            # Primeiro, vamos aplicar um pré-processamento para melhorar a detecção de picos
            cleaned_signal = nk.ecg_clean(self.total_signal, sampling_rate=self.analysis_fs)
            
            # Detectar os picos R com método robusto
            _, peaks = nk.ecg_peaks(cleaned_signal, sampling_rate=self.analysis_fs, method='neurokit')
            r_peaks = np.array(peaks['ECG_R_Peaks'])
            
            # Verificar se foram encontrados picos R suficientes
            if len(r_peaks) < 4:
                print(f"Aviso: Poucos picos R detectados ({len(r_peaks)}). Algoritmo de arritmia não pode continuar.")
                self.arrhythmias = []
                return []
            
            # Calcular os intervalos RR (ms)
            rr_intervals = np.diff(r_peaks) / self.analysis_fs * 1000
            
            # Filtrar valores fisiologicamente impossíveis, mas com limites mais flexíveis
            rr_intervals_clean = rr_intervals[(rr_intervals > 250) & (rr_intervals < 2500)]
            
            # Verificar se ainda temos intervalos suficientes após filtragem
            if len(rr_intervals_clean) < 3:
                print(f"Aviso: Poucos intervalos RR válidos após filtragem ({len(rr_intervals_clean)}). Usando intervalos originais.")
                rr_intervals_clean = rr_intervals  # Usar os originais se restarem muito poucos
            
            # Cálculos estatísticos protegidos contra arrays vazios
            if len(rr_intervals_clean) > 0:
                mean_rr = np.mean(rr_intervals_clean)
                std_rr = np.std(rr_intervals_clean)
                if len(rr_intervals_clean) >= 4:
                    p25, p75 = np.percentile(rr_intervals_clean, [25, 75])
                else:
                    p25, p75 = mean_rr * 0.9, mean_rr * 1.1  # Aproximação se poucos pontos
            else:
                print("Aviso: Nenhum intervalo RR válido. Impossível detectar arritmias.")
                self.arrhythmias = []
                return []
            
            arrhythmia_regions = defaultdict(list)
            # Percorrer apenas se houver intervalos suficientes
            if len(rr_intervals) > 1:
                for i in range(1, len(rr_intervals)):
                    if i >= len(r_peaks):
                        # Proteção contra índices fora dos limites
                        break
                    
                    delta = abs(rr_intervals[i-1] - rr_intervals[i-2]) if i > 1 else 0
                    
                    # Classificação de arritmias com thresholds mais adaptativos
                    if rr_intervals[i-1] > mean_rr + 1.5 * std_rr and rr_intervals[i-1] > 1000:
                        key = "Bradycardia"
                    elif rr_intervals[i-1] < mean_rr - 1.5 * std_rr and rr_intervals[i-1] < 600:
                        key = "Tachycardia"
                    elif delta > 300:
                        key = "PVC"
                    elif std_rr > 100 and (p75 - p25) > 150:
                        key = "Possible AFib"
                    else:
                        continue
                        
                    # Segurança adicional para índices
                    if i < len(r_peaks):
                        if arrhythmia_regions[key] and r_peaks[i] - arrhythmia_regions[key][-1][-1] < self.analysis_fs * 2:
                            arrhythmia_regions[key][-1].append(r_peaks[i])
                        else:
                            arrhythmia_regions[key].append([r_peaks[i]])
            
            # Converter regiões para formato final
            self.arrhythmias = []
            for key, regions in arrhythmia_regions.items():
                for region in regions:
                    if not region:  # Pula regiões vazias
                        continue
                    self.arrhythmias.append({
                        "type": key,
                        "count": len(region),
                        "positions": [int(pos) for pos in region],
                        "severity": self._get_severity(key)
                    })
            
            # Se houver arritmias detectadas, balancear seleção
            if self.arrhythmias:
                self._balance_arrhythmia_selection(r_peaks, max_arrhythmias)
            
            return self.arrhythmias
            
        except Exception as e:
            print(f"Erro na detecção de arritmias: {str(e)}")
            import traceback
            traceback.print_exc()
            self.arrhythmias = []
            return []

    def _balance_arrhythmia_selection(self, all_r_peaks, max_arrhythmias):
        if not self.arrhythmias or not len(all_r_peaks):
            return  # Proteção contra arrays vazios
            
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
                
            if not arr["positions"]:  # Proteção extra contra posições vazias
                continue
                
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
                
                # Segurança para r_peaks
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
                "sampling_rate": int(self.analysis_fs) if self.analysis_fs else 0,
                "arrhythmias": self.arrhythmias
            }
        }