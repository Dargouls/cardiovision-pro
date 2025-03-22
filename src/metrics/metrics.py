import os
import numpy as np
from scipy import stats
from scipy.signal import find_peaks, welch, butter, filtfilt
from datetime import datetime
from ..utils.copyWfdb import copy_record

class AnalisadorECG:
    """
    Classe para análise de sinais ECG com detecção de picos R aprimorada e cálculo de métricas de Holter.
    Mantém a mesma estrutura de saída original.
    """
    def __init__(self, caminho_diretorio, frequency=None):
        self.caminho_diretorio = caminho_diretorio
        self.frequency = frequency  # Frequência fornecida pelo usuário ou None
        self.resultados = []

    def filtrar_sinal(self, sinal, fs, lowcut=0.5, highcut=40.0):
        nyquist = 0.5 * fs
        low = lowcut / nyquist
        high = highcut / nyquist
        b, a = butter(4, [low, high], btype='band')
        return filtfilt(b, a, sinal)

    def detectar_picos_qrs(self, sinal, fs):
        sinal_filtrado = self.filtrar_sinal(sinal, fs)
        sinal_norm = (sinal_filtrado - np.mean(sinal_filtrado)) / np.std(sinal_filtrado)
        distance = int(0.2 * fs)
        prominence = 1.5
        height = 1.0
        picos, _ = find_peaks(sinal_norm, distance=distance, prominence=prominence, height=height)
        
        if len(picos) < 2:
            return None

        intervalos_rr = np.diff(picos) * (1000 / fs)
        intervalos_rr = intervalos_rr[(intervalos_rr >= 400) & (intervalos_rr <= 1500)]
        
        if len(intervalos_rr) < 2:
            return None

        # Cálculos de HRV mantendo a estrutura original
        frequencias_cardiacas = 60000 / intervalos_rr
        q1, q3 = np.percentile(intervalos_rr, [25, 75])
        iqr = q3 - q1
        mask = (intervalos_rr >= (q1 - 1.5 * iqr)) & (intervalos_rr <= (q3 + 1.5 * iqr))
        intervalos_rr_filtrados = intervalos_rr[mask]

        # Métricas atualizadas do novo módulo
        sdnn = np.std(intervalos_rr_filtrados)
        diff_rr = np.diff(intervalos_rr_filtrados)
        rmssd = np.sqrt(np.mean(np.square(diff_rr)))
        nn50 = sum(abs(diff_rr) > 50)
        pnn50 = (nn50 / len(diff_rr) * 100) if len(diff_rr) > 0 else 0

        # Cálculos de segmentação
        segment_size = int(5 * 60 * (fs / 1000))
        num_segments = max(1, int(len(intervalos_rr_filtrados) / segment_size))
        sdann_values = [np.mean(intervalos_rr_filtrados[i*segment_size:(i+1)*segment_size]) 
                       for i in range(num_segments) if len(intervalos_rr_filtrados[i*segment_size:(i+1)*segment_size]) > 1]
        
        sdnn_index_values = [np.std(intervalos_rr_filtrados[i*segment_size:(i+1)*segment_size]) 
                            for i in range(num_segments) if len(intervalos_rr_filtrados[i*segment_size:(i+1)*segment_size]) > 1]

        sdann = np.std(sdann_values) if len(sdann_values) > 1 else 0
        sdnn_index = np.mean(sdnn_index_values) if sdnn_index_values else 0

        # Cálculos espectrais
        if len(intervalos_rr_filtrados) >= 256:
            freq, psd = welch(intervalos_rr_filtrados - np.mean(intervalos_rr_filtrados), 
                             fs=4.0, nperseg=256, detrend='linear')
            lf = np.trapz(psd[(freq >= 0.04) & (freq < 0.15)])
            hf = np.trapz(psd[(freq >= 0.15) & (freq < 0.4)])
            total_power = np.trapz(psd[freq < 0.4])
            lf_nu = (lf / (lf + hf)) * 100 if (lf + hf) > 0 else 0
            hf_nu = (hf / (lf + hf)) * 100 if (lf + hf) > 0 else 0
            lf_hf_ratio = lf / hf if hf > 0 else 0
        else:
            lf_hf_ratio = total_power = lf_nu = hf_nu = 0

        return {
            'media_fc': float(np.mean(frequencias_cardiacas)),
            'mediana_fc': float(np.median(frequencias_cardiacas)),
            'desvio_padrao_fc': float(np.std(frequencias_cardiacas)),
            'min_fc': float(np.min(frequencias_cardiacas)),
            'max_fc': float(np.max(frequencias_cardiacas)),
            'media_rr': float(np.mean(intervalos_rr_filtrados)),
            'desvio_padrao_rr': float(sdnn),
            'rmssd': float(rmssd),
            'nn50': int(nn50),
            'pnn50': float(pnn50),
            'total_batimentos': int(len(picos)),
            'sdann': float(sdann),
            'sdnn_index': float(sdnn_index),
            'lf_hf_ratio': float(lf_hf_ratio),
            'total_power': float(total_power),
            'lf_nu': float(lf_nu),
            'hf_nu': float(hf_nu),
            'triangular_index': 0,  # Mantido para compatibilidade
            'tinn': 0  # Mantido para compatibilidade
        }

    def calcular_estatisticas_sinal(self, sinal):
        return {
            'media': float(np.mean(sinal)),
            'mediana': float(np.median(sinal)),
            'desvio_padrao': float(np.std(sinal)),
            'variancia': float(np.var(sinal)),
            'minimo': float(np.min(sinal)),
            'maximo': float(np.max(sinal)),
            'pico_a_pico': float(np.ptp(sinal)),
            'assimetria': float(stats.skew(sinal)),
            'curtose': float(stats.kurtosis(sinal)),
            'rms': float(np.sqrt(np.mean(np.square(sinal)))),
            'percentil_25': float(np.percentile(sinal, 25)),
            'percentil_75': float(np.percentile(sinal, 75)),
            'iqr': float(np.percentile(sinal, 75) - np.percentile(sinal, 25))
        }

    async def analisar_diretorio(self):
        registros = [os.path.join(self.caminho_diretorio, f[:-4]) 
                    for f in os.listdir(self.caminho_diretorio) if f.endswith('.hea')]
        
        for caminho_registro in registros:
            try:
                registro = await copy_record(caminho_registro)
                # Usar a frequência fornecida pelo usuário, se disponível, ou a do arquivo
                fs = self.frequency if self.frequency is not None else registro.fs
                estatisticas_canais = []
                
                for i in range(registro.n_sig):
                    sinal = registro.p_signal[:, i]
                    estatisticas_canais.append({
                        'canal': i,
                        'nome_sinal': registro.sig_name[i],
                        'estatisticas_sinal': self.calcular_estatisticas_sinal(sinal),
                        'estatisticas_fc': self.detectar_picos_qrs(sinal, fs)
                    })
                
                self.resultados.append({
                    'info': {
                        'nome_registro': os.path.basename(caminho_registro),
                        'n_sinais': registro.n_sig,
                        'fs': fs,  # Reflete a frequência usada
                        'duracao': registro.sig_len / fs,
                        'n_amostras': registro.sig_len
                    },
                    'canais': estatisticas_canais
                })
                
            except Exception as e:
                continue
                
        return self.resultados

    def obter_resultados_formatados(self):
        if not self.resultados:
            return {}

        # Cálculos agregados mantendo a estrutura original
        total_qrs = sum(
            fc['total_batimentos'] 
            for r in self.resultados 
            for c in r['canais'] 
            if (fc := c['estatisticas_fc']) is not None
        )

        return {
            'metrics': {
                'summary': {
                    'total_qrs': total_qrs,
                    'duration_hours': sum(r['info']['duracao'] for r in self.resultados) / 3600,
                    'artifacts': None,
                    'display_settings': None
                },
                'hr': {
                    'min': self._calcular_min_max('min_fc', np.min),
                    'mediana': self._calcular_mediana(),
                    'mean': self._calcular_min_max('media_fc', np.mean),
                    'max': self._calcular_min_max('max_fc', np.max),
                    'brady_time': None,
                    'tachy_episodes': None
                },
                'arrhythmias': {k: 0 for k in [
                    'vent_total', 'vent_isolated', 'vent_pairs', 'vent_runs',
                    'sv_total', 'sv_isolated', 'sv_pairs', 'sv_runs', 'pauses'
                ]},
                'annotations_used': False,
                'signal_stats': self._agregar_estatisticas_sinal()
            },
            'formatted_report': self._gerar_relatorio_formatado(),
            'analysis_time': datetime.now().isoformat(),
            'record_info': self._gerar_info_arquivos(),
            'config_used': {},
            'signal_info': self._gerar_info_sinal(),
            'raw_results': self.resultados
        }

    # Métodos auxiliares para agregação (mantidos da versão original)
    def _calcular_min_max(self, campo, funcao):
        valores = [c['estatisticas_fc'][campo] 
                  for r in self.resultados 
                  for c in r['canais'] 
                  if c['estatisticas_fc'] and campo in c['estatisticas_fc']]
        return float(funcao(valores)) if valores else None

    def _calcular_mediana(self):
        medias = [c['estatisticas_fc']['mediana_fc'] 
                 for r in self.resultados 
                 for c in r['canais'] 
                 if c['estatisticas_fc']]
        return float(np.median(medias)) if medias else None

    def _agregar_estatisticas_sinal(self):
        stats = [c['estatisticas_sinal'] for r in self.resultados for c in r['canais']]
        return {
            'mean': float(np.mean([s['media'] for s in stats])),
            'median': float(np.median([s['mediana'] for s in stats])),
            'std': float(np.mean([s['desvio_padrao'] for s in stats])),
            'peak_to_peak': float(np.mean([s['pico_a_pico'] for s in stats]))
        }

    def _gerar_relatorio_formatado(self):
        primeiro = self.resultados[0]['info']
        return {
            'resumo_holter': f"{sum(r['info']['duracao'] for r in self.resultados)/3600:.1f}h",
            'informacoes_registro': {
                'base_de_dados': None,
                'formato': None,
                'frequencia_amostragem': primeiro['fs'],
                'numero_de_canais': primeiro['n_sinais'],
                'duracao_total': sum(r['info']['duracao'] for r in self.resultados),
                'numero_de_amostras': primeiro['n_amostras']
            },
            'arquivos_utilizados': {
                ext: any(f.endswith(f'.{ext}') for f in os.listdir(self.caminho_diretorio))
                for ext in ['hea', 'dat', 'atr', 'xws']
            },
            'anotacoes_detalhadas': {},
            'dados_gerais': {
                'total_qrs': sum(r['total_batimentos'] for r in self._extrair_metricas_fc()),
                'artefatos': None,
                'qualidade_sinal': None
            },
            # SEÇÃO AUSENTE ADICIONADA AQUI
            'analise_arritmias': {
                'batimentos_ectopicos': {
                    'ventriculares': {
                        'total': 0,
                        'isolados': 0,
                        'pares': 0,
                        'sequencias': 0
                    },
                    'supraventriculares': {
                        'total': 0,
                        'isolados': 0,
                        'pares': 0,
                        'sequencias': 0
                    }
                },
                'eventos_significativos': {
                    'pausas': 0,
                    'episodios_taquicardia': None
                }
            },
            'frequencia_cardiaca': {
                'minima': self._calcular_min_max('min_fc', np.min),
                'mediana': self._calcular_mediana(),
                'media': self._calcular_min_max('media_fc', np.mean),
                'maxima': self._calcular_min_max('max_fc', np.max),
                'tempo_em_bradicardia': None,
                'classificacao_fc_media': None
            }
        }

    def _gerar_info_arquivos(self):
        return {
            'files': {
                ext: any(f.endswith(f'.{ext}') for f in os.listdir(self.caminho_diretorio))
                for ext in ['hea', 'dat', 'atr', 'xws']
            }
        }

    def _gerar_info_sinal(self):
        primeiro = self.resultados[0]['info']
        return {
            'sampling_frequency': primeiro['fs'],
            'n_channels': primeiro['n_sinais'],
            'n_samples': primeiro['n_amostras'],
            'duration_seconds': primeiro['duracao']
        }

    def _extrair_metricas_fc(self):
        return [c['estatisticas_fc'] 
               for r in self.resultados 
               for c in r['canais'] 
               if c['estatisticas_fc']]