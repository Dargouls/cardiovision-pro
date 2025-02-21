import wfdb
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import json
import base64
from io import BytesIO
import datetime

UPLOAD_FOLDER = './uploads'
RESULTS_FOLDER = './results'

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

    def load_record(self, record_name, channel=0):
        """Load an ECG record and its annotations."""
        try:
            record_path = self.base_path / record_name

            record = wfdb.rdrecord(str(record_path))
            
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

    def analyze_ecg(self, record_name, duration=10, channel=0):
      result_data = {
          'record_name': record_name,
          'analysis_time': datetime.datetime.now().isoformat(),
          'record_info': {},
          'signals': {},
          'annotations': {},
          'sampling_rates': []  # Alterado para ser uma lista
      }
      try:
          # Load the signal and annotations
          signal, fs, annotations = self.load_record(record_name, channel)
          
          # Save basic record info
          result_data['record_info'] = {
              'sampling_frequency': int(fs),
              'duration': float(len(signal) / fs),
              'channel': channel,
              'n_samples': int(len(signal))
          }

          # Save annotations if available
          if annotations:
              result_data['annotations'] = {
                  'sample_points': [int(x) for x in annotations.sample]
              }

          # Define periods to analyze
          periods = {
              'Start': 0,
              'Mid': len(signal) // 2,
              'End': len(signal) - duration * fs
          }

          # Save data for each period
          for name, start in periods.items():
              segment = signal[start:start + duration * fs]
              time = np.arange(len(segment)) / fs

              result_data['signals'][name] = {
                  'start_index': int(start),
                  'duration': duration,
                  'data': segment.tolist()
              }

              # Get annotations for this segment
              if annotations:
                  segment_anns = [
                      (int(ann_time), ann_label)
                      for ann_time, ann_label in zip(annotations.sample, annotations.symbol)
                      if start <= ann_time < start + duration * fs
                  ]
                  result_data['annotations'][name] = {
                      'times': [t for t, _ in segment_anns],
                      'labels': [l for _, l in segment_anns]
                  }

              for rate in [1.0, 0.5, 0.25, 0.125, 0.0625]:
                  factor = int(1 / rate)

                  # Adiciona os dados como um objeto na lista de sampling_rates
                  result_data['sampling_rates'].append({
                      'period': name.lower(),  # Nome do período em minúsculo
                      'rate': float(rate),
                      'frequency': int(fs * rate),
                      'data': segment[::factor].tolist(),
                      'time': time[::factor].tolist()
                  })

          # Convert all numpy types before JSON serialization
          result_data = self._convert_numpy_types(result_data)

          return result_data

      except Exception as e:
          print(f"Error analyzing ECG: {str(e)}")
          return None


    def save_complete_analysis(self, record_name):
      analysis_data = self.analyze_ecg(record_name)
      if analysis_data:
        return analysis_data
        
      return False

    def get_available_records(self):
        """Get a list of available record names."""
        try:
            records = []
            for hea_file in self.base_path.glob('*.hea'):
                record_name = hea_file.stem
                dat_file = hea_file.with_suffix('.dat')
                
                if dat_file.exists():
                    records.append(record_name)
                    
                    atr_file = hea_file.with_suffix('.atr')
                    xws_file = hea_file.with_suffix('.xws')
                    
                    print(f"Record {record_name}:")
                    print(f"  .hea: Present")
                    print(f"  .dat: Present")
                    print(f"  .atr: {'Present' if atr_file.exists() else 'Missing'}")
                    print(f"  .xws: {'Present' if xws_file.exists() else 'Missing'}")

            return records
        except Exception as e:
            print(f"Error listing records: {str(e)}")
            return []
