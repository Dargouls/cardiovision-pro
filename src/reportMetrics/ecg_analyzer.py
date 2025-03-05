import wfdb
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import json
import base64
from io import BytesIO
import datetime

from ..utils.copyWfdb import copy_record

class ECGAnalyzer:
    PARAMS = {
        'grid': {
            'major': {'color': '#ff9999', 'alpha': 0.3},
            'minor': {'color': '#ff9999', 'alpha': 0.1}
        },
        'line': {'color': '#000000', 'linewidth': 0.6},
        'features': {
            1.0: "Clinical Quality - All waves visible",
            0.5: "Diagnostic - Main components visible",
            0.25: "Monitoring - Basic rhythm visible",
            0.125: "Basic - Limited clinical value",
            0.0625: "Overview - Minimal detail"
        }
    }
    
    def __init__(self, base_path):
        """Initialize ECG Analyzer with the base path for ECG records."""
        self.base_path = Path(base_path)
        self.display_settings = {}
        self._load_display_settings()
    
    def _load_display_settings(self):
        """Load display settings from .xws files if available"""
        for xws_file in self.base_path.glob('*.xws'):
            try:
                with open(xws_file, 'r') as f:
                    settings = json.load(f)
                self.display_settings[xws_file.stem] = settings
            except Exception as e:
                print(f"Warning: Could not load display settings from {xws_file}: {str(e)}")

    async def load_record(self, record_name, channel=0):
        """Load an ECG record and its annotations."""
        try:
            record_path = self.base_path / record_name

            record = await copy_record(record_path)
            
            try:
                ann = wfdb.rdann(str(record_path), 'atr')
            except Exception as e:
                print(f"Warning: Could not load annotations: {str(e)}")
                ann = None
                
            return record.p_signal[:, channel], record.fs, ann
        except Exception as e:
            raise ValueError(f"Error loading record {record_name}: {str(e)}")

    def _convert_numpy_types(self, obj):
        """Convert numpy types to native Python types for JSON serialization."""
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, dict):
            return {key: self._convert_numpy_types(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_numpy_types(item) for item in obj]
        return obj

    
    async def analyze_ecg(self, record_name, duration=10, channel=0, desired_frequency=None, period=None):
      result_data = {
          'record_name': record_name,
          'analysis_time': datetime.datetime.now().isoformat(),
          'record_info': {},
          'annotations': {},
          'sampling_rates': []
      }
      try:
          # Carregar o sinal e as anotações
          signal, fs, annotations = await self.load_record(record_name, channel)
          
          # Validar frequências
          if desired_frequency is not None:
              if fs <= 0:
                  raise ValueError("Frequência de amostragem original deve ser positiva.")
              if desired_frequency <= 0:
                  raise ValueError("Frequência desejada deve ser positiva.")
          
          # Informações básicas do registro
          result_data['record_info'] = {
              'sampling_frequency': int(fs),
              'duration': float(len(signal) / fs),
              'channel': channel,
              'n_samples': int(len(signal))
          }

          # Anotações
          if annotations:
              result_data['annotations'] = {
                  'sample_points': [int(x) for x in annotations.sample]
              }

          # Definir períodos com base no parâmetro 'period'
          if period is not None:
              period = period.lower()
              allowed_periods = ['start', 'mid', 'end']
              if period not in allowed_periods:
                  raise ValueError(f"Período inválido: '{period}'. Valores permitidos: {allowed_periods}.")
              
              # Calcular início do período solicitado
              if period == 'start':
                  start_idx = 0
              elif period == 'mid':
                  start_idx = len(signal) // 2
              else:  # 'end'
                  start_idx = max(0, len(signal) - int(duration * fs))
              
              periods = {period.capitalize(): start_idx}
          else:
              # Períodos originais (start, mid, end)
              periods = {
                  'Start': 0,
                  'Mid': len(signal) // 2,
                  'End': max(0, len(signal) - int(duration * fs))
              }

          # Processar cada período definido
          for name, start in periods.items():
              start = int(start)
              start = max(0, start)  # Garantir que não seja negativo
              end = start + int(duration * fs)
              end = min(end, len(signal))  # Não ultrapassar o fim do sinal
              
              segment = signal[start:end]
              original_duration = len(segment) / fs

              # Anotações no segmento
              if annotations:
                  segment_anns = [
                      (int(ann_time), ann_label)
                      for ann_time, ann_label in zip(annotations.sample, annotations.symbol)
                      if start <= ann_time < end
                  ]
                  result_data['annotations'][name] = {
                      'times': [t for t, _ in segment_anns],
                      'labels': [l for _, l in segment_anns]
                  }

              # Reamostrar para a frequência desejada
              if desired_frequency is not None:
                  new_num_samples = int(original_duration * desired_frequency)
                  if new_num_samples == 0:
                      resampled_data = []
                      new_time = []
                  else:
                      original_time = np.arange(len(segment)) / fs
                      new_time = np.linspace(0, original_duration, new_num_samples, endpoint=False)
                      resampled_data = np.interp(new_time, original_time, segment)
                  
                  result_data['sampling_rates'].append({
                      'period': name.lower(),
                      'rate': desired_frequency / fs,
                      'frequency': desired_frequency,
                      'data': resampled_data.tolist(),
                      'time': new_time.tolist()
                  })
              else:
                  # Taxas padrão (1.0, 0.5, etc.)
                  for rate in [1.0, 0.5, 0.25, 0.125, 0.0625]:
                      factor = int(1 / rate)
                      downsampled_data = segment[::factor]
                      downsampled_time = (np.arange(len(downsampled_data)) * (1 / (fs * rate))).tolist()
                      
                      result_data['sampling_rates'].append({
                          'period': name.lower(),
                          'rate': float(rate),
                          'frequency': int(fs * rate),
                          'data': downsampled_data.tolist(),
                          'time': downsampled_time
                      })

          # Converter tipos numpy para Python
          result_data = self._convert_numpy_types(result_data)
          return result_data

      except Exception as e:
          print(f"Erro na análise de frequências: {str(e)}")
          return None
    
    async def save_complete_analysis(self, record_name, desired_frequency=None, period=None):
      analysis_data = await self.analyze_ecg(record_name, desired_frequency=desired_frequency, period=period)
      return analysis_data if analysis_data else False

    def get_available_records(self):
        """Listar registros disponíveis."""
        try:
            records = []
            for hea_file in self.base_path.glob('*.hea'):
                record_name = hea_file.stem
                dat_file = hea_file.with_suffix('.dat')
                if dat_file.exists():
                    records.append(record_name)
            return records
        except Exception as e:
            print(f"Erro ao listar registros: {str(e)}")
            return []