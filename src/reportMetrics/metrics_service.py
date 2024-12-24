import numpy as np
import wfdb
from scipy import signal
from datetime import datetime, timedelta
import itertools
import json
import os
from pathlib import Path

UPLOAD_FOLDER = './uploads'
RESULTS_FOLDER = './results'

CONFIG = {
    'qrs': {
        'filter': [5, 15],          
        'window': 0.08,             
        'threshold': 0.3,           
        'min_dist': 0.2             
    },
    'st': {
        'thresholds': {
            'depression': 0.1,
            'elevation': 0.3
        },
        'duration': 60,             
        'interval': 60              
    },
    'hr': {
        'brady': 50,               
        'tachy': 120,              
        'rr_range': [400, 2000],   
        'limits': [20, 200]        
    },
    'prematuridade_sv': 0.30,      
    'pausa_min': 2.0               
}

def numpy_to_python(obj):
    """Convert numpy types to python native types for JSON serialization"""
    if isinstance(obj, (np.int_, np.intc, np.intp, np.int8,
        np.int16, np.int32, np.int64, np.uint8,
        np.uint16, np.uint32, np.uint64)):
        return int(obj)
    elif isinstance(obj, (np.float_, np.float16, np.float32, np.float64)):
        return float(obj)
    elif isinstance(obj, (np.bool_)):
        return bool(obj)
    elif isinstance(obj, (np.ndarray,)):
        return obj.tolist()
    elif isinstance(obj, (np.complex_, np.complex64, np.complex128)):
        return {'real': obj.real, 'imag': obj.imag}
    elif isinstance(obj, datetime):
        return obj.isoformat()
    return obj

class HolterAnalyzer:
    def __init__(self, record_path):
        self.record_path = record_path
        self.display_settings = {}
        self.annotations = None
        self.record = None
        
    def load_files(self):
        """Carrega todos os arquivos disponíveis (.hea, .dat, .atr, .xws)"""
        # Carrega dados do sinal (.hea e .dat)
        try:
          self.record = wfdb.rdrecord(self.record_path)
          print(f"Carregando arquivos .hea e .dat de {self.record}")
        except Exception as e:
          raise ValueError(f"Erro ao carregar arquivos .hea/.dat: {str(e)}")
            
        # Carrega anotações (.atr)
        try:
          self.annotations = wfdb.rdann(self.record_path, 'atr')
          print("Arquivo .atr carregado com sucesso")
        except Exception as e:
          print(f"Aviso: Não foi possível carregar arquivo .atr: {str(e)}")
        
        # Tenta carregar configurações de visualização (.xws)
        xws_path = f"{self.record_path}.xws"
        if os.path.exists(xws_path):
            try:
                with open(xws_path, 'r') as f:
                    content = f.read().strip()
                    if content:
                        import re
                        url_match = re.search(r'https?://[^\s<>"]+|www\.[^\s<>"]+', content)
                        
                        if url_match:
                            base_url = url_match.group()
                            if base_url.startswith('//'):
                                base_url = 'http:' + base_url
                            base_url = base_url.replace('.xws', '')
                            self.display_settings = {
                                'database_url': base_url,
                                'record_id': os.path.basename(self.record_path),
                                'record_info': {
                                    'database': 'vfdb',
                                    'format': 'MIT-BIH',
                                    'fs': numpy_to_python(self.record.fs),
                                    'n_sig': numpy_to_python(self.record.n_sig),
                                    'sig_len': numpy_to_python(self.record.sig_len),
                                    'base_time': self.record.base_time if hasattr(self.record, 'base_time') else None,
                                    'base_date': self.record.base_date if hasattr(self.record, 'base_date') else None
                                }
                            }
                            print(f"Informações do registro extraídas da URL do .xws: {base_url}")
                        else:
                            try:
                                self.display_settings = json.loads(content)
                                print("Arquivo .xws carregado como JSON")
                            except json.JSONDecodeError:
                                settings = {}
                                for line in content.split('\n'):
                                    line = line.strip()
                                    if ':' in line:
                                        key, value = line.split(':', 1)
                                        settings[key.strip()] = value.strip()
                                    elif '=' in line:
                                        key, value = line.split('=', 1)
                                        settings[key.strip()] = value.strip()
                                
                                self.display_settings = settings
                                print(f"Arquivo .xws carregado como texto estruturado: {settings}")
                    else:
                        print("Arquivo .xws está vazio")
            except Exception as e:
                print(f"Erro ao processar arquivo .xws: {str(e)}")
                self.display_settings = {'error': str(e), 'raw_content': content}
        else:
            print("Arquivo .xws não encontrado")

    def detect_qrs(self, ecg, fs):
        """Detecção de complexos QRS com suporte a anotações"""
        # Detecção automática
        b, a = signal.butter(3, [c/(fs/2) for c in CONFIG['qrs']['filter']], 'band')
        filtered = signal.filtfilt(b, a, ecg)
        
        squared = np.diff(filtered)**2
        
        win_size = int(CONFIG['qrs']['window']*fs)
        integrated = np.convolve(squared, np.ones(win_size)/win_size, 'same')
        
        peaks = signal.find_peaks(
            integrated,
            distance=int(CONFIG['qrs']['min_dist']*fs),
            height=CONFIG['qrs']['threshold']*np.mean(integrated)
        )[0]
        
        peaks = np.array([
            p + np.argmax(np.abs(ecg[p:p+int(0.05*fs)]))
            for p in peaks if p < len(ecg)-int(0.05*fs)
        ])
        
        if self.annotations is not None:
            ann_peaks = self.annotations.sample
            ann_types = self.annotations.symbol
            qrs_anns = ann_peaks[np.isin(ann_types, ['N', 'V', 'S'])]
            all_peaks = np.unique(np.concatenate([peaks, qrs_anns]))
            return all_peaks
        return peaks

    def analyze_holter(self):
        """Análise completa do Holter usando todos os arquivos disponíveis"""
        signal = self.record.p_signal[:,0]
        fs = self.record.fs
        
        # Normalização do sinal
        signal = (signal - np.median(signal)) / (np.percentile(signal,75) - np.percentile(signal,25))
        
        # Detecção QRS com anotações
        peaks = self.detect_qrs(signal, fs)
        
        # Cálculo dos intervalos RR
        rr = np.diff(peaks) / fs * 1000
        valid_rr = rr[
            (rr >= CONFIG['hr']['rr_range'][0]) & 
            (rr <= CONFIG['hr']['rr_range'][1])
        ]
        
        # Cálculo da frequência cardíaca
        hr = 60000/valid_rr
        hr = hr[
            (hr >= CONFIG['hr']['limits'][0]) & 
            (hr <= CONFIG['hr']['limits'][1])
        ]
        
        # Estatísticas RR
        mean_rr = np.median(valid_rr)
        rr_mad = np.median(np.abs(valid_rr - mean_rr))
        
        # Detecção de arritmias
        if self.annotations is not None:
            vent_idx = np.where(np.isin(self.annotations.symbol, ['V']))[0]
            sv_idx = np.where(np.isin(self.annotations.symbol, ['S', 'A']))[0]
        else:
            vent_idx = np.where(
                (valid_rr < 0.7*mean_rr) & 
                (valid_rr > 200) & 
                (np.abs(valid_rr - mean_rr) > 3*rr_mad)
            )[0]
            
            sv_idx = np.where(
                (valid_rr < (1-CONFIG['prematuridade_sv'])*mean_rr) & 
                (valid_rr > 0.7*mean_rr)
            )[0]
        
        # Análise de sequências
        vent_runs = [len(list(g)) for _, g in itertools.groupby(np.diff(vent_idx) == 1) if g]
        sv_runs = [len(list(g)) for _, g in itertools.groupby(np.diff(sv_idx) == 1) if g]
        
        # Análise de taquicardia
        tachy_mask = hr >= CONFIG['hr']['tachy']
        tachy_idx = np.where(tachy_mask)[0]
        tachy_runs = [len(list(g)) for _, g in itertools.groupby(np.diff(tachy_idx) == 1) if g]
        
        total_time = len(signal)/(fs*3600)
        
        metrics = {
            'summary': {
                'total_qrs': numpy_to_python(len(peaks)),
                'duration_hours': numpy_to_python(total_time),
                'artifacts': numpy_to_python((len(rr) - len(valid_rr))/len(rr) * 100 if len(rr) > 0 else 0),
                'display_settings': self.display_settings
            },
            'hr': {
                'min': numpy_to_python(np.percentile(hr, 1)) if len(hr) > 0 else 0,
                'mean': numpy_to_python(np.median(hr)) if len(hr) > 0 else 0,
                'max': numpy_to_python(np.percentile(hr, 99)) if len(hr) > 0 else 0,
                'brady_time': numpy_to_python(np.sum(hr < CONFIG['hr']['brady'])/len(hr) * total_time) if len(hr) > 0 else 0,
                'tachy_episodes': numpy_to_python(len([r for r in tachy_runs if r >= 4]))
            },
            'arrhythmias': {
                'vent_total': numpy_to_python(len(vent_idx)),
                'vent_isolated': numpy_to_python(len(vent_idx) - sum(vent_runs) if vent_runs else len(vent_idx)),
                'vent_pairs': numpy_to_python(sum(1 for r in vent_runs if r == 2)),
                'vent_runs': numpy_to_python(sum(1 for r in vent_runs if r > 2)),
                'sv_total': numpy_to_python(len(sv_idx)),
                'sv_isolated': numpy_to_python(len(sv_idx) - sum(sv_runs) if sv_runs else len(sv_idx)),
                'sv_pairs': numpy_to_python(sum(1 for r in sv_runs if r == 2)),
                'sv_runs': numpy_to_python(sum(1 for r in sv_runs if r > 2)),
                'pauses': numpy_to_python(sum(valid_rr > CONFIG['pausa_min']*1000))
            },
            'annotations_used': self.annotations is not None,
            'signal_stats': {
                'mean': numpy_to_python(np.mean(signal)),
                'std': numpy_to_python(np.std(signal)),
                'peak_to_peak': numpy_to_python(np.ptp(signal))
            }
        }
        
        return metrics

    def format_report(self, metrics):
      """Formata resultados da análise em relatório legível"""
      d = timedelta(hours=metrics['summary']['duration_hours'])
      b = timedelta(hours=metrics['hr']['brady_time'])

      report_data = {
          "resumo_holter": f"{d.total_seconds()/3600:.1f}h",
          "informacoes_registro": {
              "base_de_dados": self.display_settings.get('record_info', {}).get('database', 'N/A'),
              "formato": self.display_settings.get('record_info', {}).get('format', 'N/A'),
              "frequencia_amostragem": self.record.fs,
              "numero_de_canais": self.record.n_sig,
              "duracao_total": str(d),
              "numero_de_amostras": self.record.sig_len,
          },
          "arquivos_utilizados": {
              "header_hea": os.path.exists(self.record_path + '.hea'),
              "dados_dat": os.path.exists(self.record_path + '.dat'),
              "anotacoes_atr": self.annotations is not None,
              "configuracoes_xws": bool(self.display_settings)
          },
          "anotacoes_detalhadas": {},
          "dados_gerais": {
              "total_qrs": metrics['summary']['total_qrs'],
              "artefatos": metrics['summary']['artifacts'],
              "qualidade_sinal": "Boa" if metrics['summary']['artifacts'] < 30 else 
                                "Regular" if metrics['summary']['artifacts'] < 50 else 
                                "Baixa"
          },
          "analise_arritmias": {
              "batimentos_ectopicos": {
                  "ventriculares": {
                      "total": metrics['arrhythmias']['vent_total'],
                      "isolados": metrics['arrhythmias']['vent_isolated'],
                      "pares": metrics['arrhythmias']['vent_pairs'],
                      "sequencias": metrics['arrhythmias']['vent_runs']
                  },
                  "supraventriculares": {
                      "total": metrics['arrhythmias']['sv_total'],
                      "isolados": metrics['arrhythmias']['sv_isolated'],
                      "pares": metrics['arrhythmias']['sv_pairs'],
                      "sequencias": metrics['arrhythmias']['sv_runs']
                  }
              },
              "eventos_significativos": {
                  "pausas": metrics['arrhythmias']['pauses'],
                  "episodios_taquicardia": metrics['hr']['tachy_episodes']
              }
          },
          "frequencia_cardiaca": {
              "minima": metrics['hr']['min'],
              "media": metrics['hr']['mean'],
              "maxima": metrics['hr']['max'],
              "tempo_em_bradicardia": str(b),
              "classificacao_fc_media": "Bradicardia" if metrics['hr']['mean'] < 60 else
                                        "Normal" if metrics['hr']['mean'] < 100 else
                                        "Taquicardia leve" if metrics['hr']['mean'] < 120 else
                                        "Taquicardia significativa"
          }
      }

      if self.annotations is not None:
          ann_types = np.unique(self.annotations.symbol)
          ann_counts = {t: np.sum(np.array(self.annotations.symbol) == t) for t in ann_types}
          report_data["anotacoes_detalhadas"] = {
              "tipos_de_batimentos_encontrados": {
                  ann_type: {
                      "label": {
                          'N': 'Normal',
                          'V': 'Ventricular prematuro',
                          'S': 'Supraventricular prematuro',
                          'F': 'Fusão',
                          'Q': 'Não classificado'
                      }.get(ann_type, f'Tipo {ann_type}'),
                      "count": numpy_to_python(count)
                  } for ann_type, count in ann_counts.items()
              }
          }

      if 'database_url' in self.display_settings:
          report_data["informacoes_adicionais"] = {
              "url_do_registro": self.display_settings['database_url'],
              "id_do_registro": self.display_settings.get('record_id', 'N/A')
          }

      return report_data
  
    def save_complete_analysis(self, record_path):
        """
        Analisa o registro ECG e salva todas as informações em JSON.
        
        Args:
            record_path (str): Caminho para o registro ECG
        """
        try:
            self.load_files()
            # Realiza a análise
            metrics = self.analyze_holter()
            
            # Gera o relatório formatado
            report = self.format_report(metrics)
            
            # Cria o dicionário completo para JSON
            complete_data = {
                'metrics': metrics,
                'formatted_report': report,
                'analysis_time': datetime.now().isoformat(),
                'record_info': {
                    'path': str(record_path),
                    'files': {
                        'hea': os.path.exists(record_path + '.hea'),
                        'dat': os.path.exists(record_path + '.dat'),
                        'atr': os.path.exists(record_path + '.atr'),
                        'xws': os.path.exists(record_path + '.xws')
                    }
                },
                'config_used': CONFIG,
                'signal_info': {
                    'sampling_frequency': numpy_to_python(self.record.fs),
                    'n_channels': numpy_to_python(self.record.n_sig),
                    'n_samples': numpy_to_python(self.record.sig_len),
                    'duration_seconds': numpy_to_python(self.record.sig_len / self.record.fs)
                }
            }
            
            return complete_data
            
        except Exception as e:
            print(f"Erro ao salvar análise: {str(e)}")
            return None
          
def save_complete_analysis(record_path):
    """
    Analisa o registro ECG e salva todas as informações em JSON.
    
    Args:
        record_path (str): Caminho para o registro ECG
    """
    print(f'init {record_path}')
    try:
        # Realiza a análise
        analyzer = HolterAnalyzer(record_path)
        metrics = analyzer.analyze_holter()
        
        print('analyzer init')
        # Gera o relatório formatado
        report = analyzer.format_report(metrics)
        print('report')
        
        # Cria o dicionário completo para JSON
        complete_data = {
            'metrics': metrics,
            'formatted_report': report,
            'analysis_time': datetime.now().isoformat(),
            'record_info': {
                'path': str(record_path),
                'files': {
                    'hea': os.path.exists(record_path + '.hea'),
                    'dat': os.path.exists(record_path + '.dat'),
                    'atr': os.path.exists(record_path + '.atr'),
                    'xws': os.path.exists(record_path + '.xws')
                }
            },
            'config_used': CONFIG,
            'signal_info': {
                'sampling_frequency': numpy_to_python(analyzer.record.fs),
                'n_channels': numpy_to_python(analyzer.record.n_sig),
                'n_samples': numpy_to_python(analyzer.record.sig_len),
                'duration_seconds': numpy_to_python(analyzer.record.sig_len / analyzer.record.fs)
            }
        }
        print('complete_data')
        
        # Salva em JSON
        output_file = Path(RESULTS_FOLDER) / f"{os.path.basename(record_path)}_complete_analysis.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(complete_data, f, indent=2, ensure_ascii=False)
        
        print(f"Análise completa salva em: {output_file}")
        
        # Também exibe o relatório formatado
        print("\nRELATÓRIO FORMATADO:")
        print("="*50)
        print(report)
        
        return complete_data
        
    except Exception as e:
        print(f"Erro ao salvar análise: {str(e)}")
        return None