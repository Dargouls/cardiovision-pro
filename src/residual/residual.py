import wfdb
import numpy as np
from scipy.signal import savgol_filter  # Para suavização do sinal

from pathlib import Path

import json
import datetime

from ..utils.copyWfdb import copy_record

class ECGAnalyzer:
    PARAMS = {
        'grid': {
            'major': {'color': '#ff9999', 'alpha': 0.3},
            'minor': {'color': '#ff9999', 'alpha': 0.1}
        },
        'line': {
            'clean': {'color': '#000000', 'linewidth': 0.6},  # Cor para o sinal limpo
            'noise': {'color': '#ff0000', 'linewidth': 0.6, 'alpha': 0.5}   # Cor para a sujeira estatística com transparência
        },
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

    async def load_record(self, record_name):
        """Load an ECG record and its annotations."""
        try:
            record_path = self.base_path / record_name
            record = await copy_record(record_path)

            try:
                ann = wfdb.rdann(str(record_path), 'atr')
                print("Annotations loaded successfully")
            except Exception as e:
                print(f"Warning: Could not load annotations: {str(e)}")
                ann = None

            return record.p_signal, record.fs, ann
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
    async def analyze_ecg(self, record_name, segment_duration=10):
      result_data = {
          'record_name': record_name,
          'analysis_time': datetime.datetime.now().isoformat(),
          'input_parameters': {
              'segment_duration': segment_duration,
              'base_path': str(self.base_path)
          },
          'record_info': {},
          'signals': [],  # Agora será um array de objetos
          'annotations': {},
          'statistics': {},  # Adicionado para armazenar as métricas estatísticas
      }

      try:
          # Load the signal and annotations
          signals, fs, annotations = await self.load_record(record_name)
          n_channels = signals.shape[1]
          total_samples = len(signals)

          # Save basic record info
          result_data['record_info'] = {
              'sampling_frequency': int(fs),
              'duration': float(total_samples / fs),
              'n_channels': n_channels,
              'n_samples': int(total_samples)
          }

          # Save annotations if available
          if annotations:
              result_data['annotations'] = {
                  'sample_points': [int(x) for x in annotations.sample],
                  'symbols': list(annotations.symbol),
                  # 'aux_note': list(annotations.aux_note)
              }

          # Define segments: Start, Mid, End
          segment_length = int(segment_duration * fs)
          segments = {
              'start': 0,
              'mid': total_samples // 2 - segment_length // 2,
              'end': total_samples - segment_length
          }

          # Process each segment and channel
          for period, start in segments.items():
              for j in range(n_channels):
                  segment = signals[start:start + segment_length, j]
                  time = np.arange(len(segment)) / fs

                  # Suavização do sinal usando filtro Savitzky-Golay
                  smoothed_segment = savgol_filter(segment, window_length=51, polyorder=3)
                  noise = segment - smoothed_segment  # Sujeira estatística (ruído)

                  # Objeto do segmento para o canal
                  signal_object = {
                      'period': period,
                      'channel': j + 1,
                      'start_index': int(start),
                      'duration': float(segment_length / fs),
                      'time': time.tolist(),
                      'signal': segment.tolist(),  # Alterado de 'data' para 'signal'
                      'smoothed_signal': smoothed_segment.tolist(),  # Alterado de 'smoothed_data' para 'smoothed_signal'
                      'noise': noise.tolist(),
                      'annotations': []
                  }

                  # Adicionar anotações se disponíveis
                  if annotations:
                      segment_anns = [
                          (int(ann_time), ann_label)
                          for ann_time, ann_label in zip(annotations.sample, annotations.symbol)
                          if start <= ann_time < start + segment_length
                      ]
                      for ann_time, ann_label in segment_anns:
                          relative_time = float((ann_time - start) / fs)
                          signal_object['annotations'].append({
                              'time': relative_time,
                              'label': ann_label,
                              'value': float(segment[ann_time - start])
                          })

                  # Adicionar objeto ao array de sinais
                  result_data['signals'].append(signal_object)

                  # Calcular estatísticas
                  result_data['statistics'][f"{period}_Channel_{j+1}"] = {
                      'mean': float(np.mean(segment)),
                      'std': float(np.std(segment)),
                      'min': float(np.min(segment)),
                      'max': float(np.max(segment)),
                      'median': float(np.median(segment)),
                      'noise_mean': float(np.mean(noise)),
                      'noise_std': float(np.std(noise))
                  }

          # Convert all numpy types before JSON serialization
          result_data = self._convert_numpy_types(result_data)

          # Save all data to JSON file
          output_file = Path(self.base_path) / f"{record_name}_analysis.json"
          with open(output_file, 'w') as f:
              json.dump(result_data, f, indent=2)

          print(f"Analysis data saved to {output_file}")
          return result_data

      except Exception as e:
          print(f"Error analyzing residual: {str(e)}")
          return None


    async def save_complete_analysis(self, record_name):
        """Save complete analysis including signal data, annotations and visualizations."""
        analysis_data = await self.analyze_ecg(record_name)
        if analysis_data:
            print(f"Complete analysis saved successfully for record {record_name}")
            return True
        return False