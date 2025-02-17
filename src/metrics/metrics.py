import os
import json
import tempfile
import httpx
from fastapi import FastAPI, Form, HTTPException
from datetime import datetime
import numpy as np
import wfdb
from scipy import stats
from scipy.signal import find_peaks, welch, butter, filtfilt

class AnalisadorECG:
    """
    Classe para análise de sinais ECG com detecção de picos R aprimorada e cálculo de métricas de Holter.
    """

    def __init__(self, caminho_diretorio):
        self.caminho_diretorio = caminho_diretorio
        self.resultados = []  # Armazena os resultados brutos de cada registro

    def filtrar_sinal(self, sinal, fs, lowcut=0.5, highcut=40.0):
        nyquist = 0.5 * fs
        low = lowcut / nyquist
        high = highcut / nyquist
        b, a = butter(4, [low, high], btype='band')
        return filtfilt(b, a, sinal)

    def detectar_picos_qrs(self, sinal, fs):
        sinal_filtrado = self.filtrar_sinal(sinal, fs)
        sinal_norm = (sinal_filtrado - np.mean(sinal_filtrado)) / np.std(sinal_filtrado)
        distance = int(0.2 * fs)  # 200ms entre picos
        prominence = 1.5
        height = 1.0
        picos, _ = find_peaks(sinal_norm, distance=distance, prominence=prominence, height=height)
        if len(picos) < 2:
            return None

        intervalos_rr = np.diff(picos) * (1000 / fs)
        intervalos_rr = intervalos_rr[(intervalos_rr >= 400) & (intervalos_rr <= 1500)]
        if len(intervalos_rr) < 2:
            return None

        frequencias_cardiacas = 60000 / intervalos_rr

        # Remoção de outliers com IQR
        q1, q3 = np.percentile(intervalos_rr, [25, 75])
        iqr = q3 - q1
        mask = (intervalos_rr >= (q1 - 1.5 * iqr)) & (intervalos_rr <= (q3 + 1.5 * iqr))
        intervalos_rr_filtrados = intervalos_rr[mask]

        sdnn = np.std(intervalos_rr_filtrados)
        diff_rr = np.diff(intervalos_rr_filtrados)
        rmssd = np.sqrt(np.mean(np.square(diff_rr)))
        nn50 = sum(abs(diff_rr) > 50)
        pnn50 = (nn50 / len(diff_rr) * 100) if len(diff_rr) > 0 else 0

        # Segmentação para SDANN e SDNN Index (segmentos de 5 minutos)
        segment_size = int(5 * 60 * (fs / 1000))
        num_segments = max(1, int(len(intervalos_rr_filtrados) / segment_size))
        sdann_values = []
        sdnn_index_values = []
        for i in range(num_segments):
            start_idx = int(i * segment_size)
            end_idx = int((i + 1) * segment_size)
            segment = intervalos_rr_filtrados[start_idx:end_idx]
            if len(segment) > 1:
                sdann_values.append(np.mean(segment))
                sdnn_index_values.append(np.std(segment))
        sdann = np.std(sdann_values) if len(sdann_values) > 1 else 0
        sdnn_index = np.mean(sdnn_index_values) if len(sdnn_index_values) > 0 else 0

        # Cálculo do Triangular Index e TINN
        if len(intervalos_rr_filtrados) > 0:
            bin_width = 8.0  # ms
            bins = int((np.max(intervalos_rr_filtrados) - np.min(intervalos_rr_filtrados)) / bin_width)
            hist, bin_edges = np.histogram(intervalos_rr_filtrados, bins=max(bins, 1))
            if np.sum(hist) > 0:
                triangular_index = len(intervalos_rr_filtrados) / np.max(hist)
                max_bin = np.argmax(hist)
                left_edge = bin_edges[max_bin]
                right_edge = bin_edges[max_bin + 1]
                tinn = right_edge - left_edge
            else:
                triangular_index = 0
                tinn = 0
        else:
            triangular_index = 0
            tinn = 0

        # Análise espectral (LF/HF)
        if len(intervalos_rr_filtrados) >= 256:
            freq, psd = welch(intervalos_rr_filtrados - np.mean(intervalos_rr_filtrados),
                              fs=4.0,
                              nperseg=256,
                              detrend='linear')
            lf = np.trapz(psd[(freq >= 0.04) & (freq < 0.15)])
            hf = np.trapz(psd[(freq >= 0.15) & (freq < 0.4)])
            total_power = np.trapz(psd[(freq >= 0.003) & (freq < 0.4)])
            lf_nu = (lf / (lf + hf)) * 100
            hf_nu = (hf / (lf + hf)) * 100
            lf_hf_ratio = lf / hf if hf > 0 else 0
        else:
            lf_hf_ratio = 0
            total_power = 0
            lf_nu = 0
            hf_nu = 0
        
        estatisticas_fc = {
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
          'triangular_index': float(triangular_index),
          'tinn': float(tinn)
        }
        return estatisticas_fc

    def calcular_estatisticas_sinal(self, sinal):
        estatisticas = {
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
        return estatisticas

    def analisar_diretorio(self):
        registros = []
        for arquivo in os.listdir(self.caminho_diretorio):
            if arquivo.endswith('.hea'):
                caminho_registro = os.path.join(self.caminho_diretorio, arquivo[:-4])
                registros.append(caminho_registro)
        print(f"Encontrados {len(registros)} registros no diretório.")

        for caminho_registro in registros:
            try:
                registro = wfdb.rdrecord(caminho_registro)
                nome_registro = os.path.basename(caminho_registro)
                info_registro = {
                    'nome_registro': nome_registro,
                    'n_sinais': registro.n_sig,
                    'fs': registro.fs,
                    'duracao': registro.sig_len / registro.fs,
                    'n_amostras': registro.sig_len
                }
                estatisticas_canais = []
                for i in range(registro.n_sig):
                    sinal = registro.p_signal[:, i]
                    estatisticas_sinal = self.calcular_estatisticas_sinal(sinal)
                    estatisticas_fc = self.detectar_picos_qrs(sinal, registro.fs)
                    dados_canal = {
                        'canal': i,
                        'nome_sinal': registro.sig_name[i],
                        'estatisticas_sinal': estatisticas_sinal,
                        'estatisticas_fc': estatisticas_fc
                    }
                    estatisticas_canais.append(dados_canal)
                registro_resultado = {
                    'info': info_registro,
                    'canais': estatisticas_canais
                }
                self.resultados.append(registro_resultado)
            except Exception as e:
                print(f"Erro ao processar registro {caminho_registro}: {str(e)}")
        return self.resultados

    def obter_resultados_formatados(self):
        """
        Retorna um único dicionário com TODOS os dados coletados:
          - Dados agregados e formatados (metrics, formatted_report, etc)
          - Dados brutos de cada registro (raw_results)
        """
        if not self.resultados:
            return {}

        total_qrs = 0
        all_media_fc = []
        all_mediana_fc = []
        all_min_fc = []
        all_max_fc = []
        all_estatisticas_sinal = []
        duracoes = []

        for reg in self.resultados:
            duracoes.append(reg['info']['duracao'])
            for canal in reg['canais']:
                fc = canal['estatisticas_fc']
                if fc:
                    total_qrs += fc.get('total_batimentos', 0)
                    all_media_fc.append(fc.get('media_fc', 0))
                    all_mediana_fc.append(fc.get('mediana_fc', 0))
                    all_min_fc.append(fc.get('min_fc', 0))
                    all_max_fc.append(fc.get('max_fc', 0))
                all_estatisticas_sinal.append(canal['estatisticas_sinal'])

        hr_mean = np.mean(all_media_fc) if all_media_fc else None
        hr_mediana = np.median(all_mediana_fc) if all_mediana_fc else None
        hr_min = np.min(all_min_fc) if all_min_fc else None
        hr_max = np.max(all_max_fc) if all_max_fc else None

        # Agregação das estatísticas dos sinais
        signal_means = [s['media'] for s in all_estatisticas_sinal if 'media' in s]
        signal_medians = [s['mediana'] for s in all_estatisticas_sinal if 'mediana' in s]
        signal_stds = [s['desvio_padrao'] for s in all_estatisticas_sinal if 'desvio_padrao' in s]
        signal_ptp = [s['pico_a_pico'] for s in all_estatisticas_sinal if 'pico_a_pico' in s]
        aggregated_signal_stats = {
            'mean': np.mean(signal_means) if signal_means else None,
            'median': np.median(signal_medians) if signal_medians else None,
            'std': np.mean(signal_stds) if signal_stds else None,
            'peak_to_peak': np.mean(signal_ptp) if signal_ptp else None
        }

        metrics = {
            'summary': {
                'total_qrs': total_qrs,
                'duration_hours': np.sum(duracoes) / 3600,
                'artifacts': None,
                'display_settings': None
            },
            'hr': {
                'min': hr_min,
                'mediana': hr_mediana,
                'mean': hr_mean,
                'max': hr_max,
                'brady_time': None,
                'tachy_episodes': None
            },
            'arrhythmias': {
                'vent_total': 0,
                'vent_isolated': 0,
                'vent_pairs': 0,
                'vent_runs': 0,
                'sv_total': 0,
                'sv_isolated': 0,
                'sv_pairs': 0,
                'sv_runs': 0,
                'pauses': 0
            },
            'annotations_used': False,
            'signal_stats': aggregated_signal_stats
        }

        first_info = self.resultados[0]['info']
        dur_sec = first_info['duracao']
        horas = int(dur_sec // 3600)
        minutos = int((dur_sec % 3600) // 60)
        segundos = int(dur_sec % 60)
        dur_format = f"{horas:02d}:{minutos:02d}:{segundos:02d}"

        files = {
            'hea': any(f.endswith('.hea') for f in os.listdir(self.caminho_diretorio)),
            'dat': any(f.endswith('.dat') for f in os.listdir(self.caminho_diretorio)),
            'atr': any(f.endswith('.atr') for f in os.listdir(self.caminho_diretorio)),
            'xws': any(f.endswith('.xws') for f in os.listdir(self.caminho_diretorio))
        }

        formatted_report = {
            'resumo_holter': f"{np.sum(duracoes)/3600:.1f}h",
            'informacoes_registro': {
                'base_de_dados': None,
                'formato': None,
                'frequencia_amostragem': first_info['fs'],
                'numero_de_canais': first_info['n_sinais'],
                'duracao_total': dur_format,
                'numero_de_amostras': first_info['n_amostras']
            },
            'arquivos_utilizados': files,
            'anotacoes_detalhadas': {},
            'dados_gerais': {
                'total_qrs': total_qrs,
                'artefatos': None,
                'qualidade_sinal': None
            },
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
                'minima': hr_min,
                'mediana': hr_mediana,
                'media': hr_mean,
                'maxima': hr_max,
                'tempo_em_bradicardia': None,
                'classificacao_fc_media': None
            }
        }

        record_info = {'files': files}
        config_used = {}
        signal_info = {
            'sampling_frequency': first_info['fs'],
            'n_channels': first_info['n_sinais'],
            'n_samples': first_info['n_amostras'],
            'duration_seconds': first_info['duracao']
        }

        # Retorna um dicionário com TODOS os dados:
        resultados_formatados = {
            'metrics': metrics,
            'formatted_report': formatted_report,
            'analysis_time': datetime.now().isoformat(),
            'record_info': record_info,
            'config_used': config_used,
            'signal_info': signal_info,
            'raw_results': self.resultados  # Dados brutos de cada registro
        }
        return resultados_formatados
