
import uvicorn

import wfdb
import numpy as np
import os
from .signal_processor import SignalProcessor
from .data_manager import ECGDataManager
from .config import ECGConfig

"""
	Classe principal para análise de ECG.
"""
class ECGAnalyzer:
	def __init__(self, record, num_parts=24, paper_speed=5000):
			self.record = record
			self.num_parts = num_parts
			self.paper_speed = paper_speed
			self.total_samples = record.p_signal.shape[0]
			self.part_size = self.total_samples // num_parts
			
			# Inicializar componentes
			self.signal_processor = SignalProcessor()
			self.data_manager = ECGDataManager(self.signal_processor)
	
	def analyze(self):
		"""
		Realiza análise completa do ECG e retorna no formato esperado pelo frontend.
		"""
		segments_data = []
		for part in range(self.num_parts):
			start_idx = part * self.part_size
			end_idx = min(start_idx + self.paper_speed, self.total_samples)

			segment_data = self.data_manager.process_segment(
				self.record.p_signal,
				start_idx,
				end_idx,
				self.record.sig_name
			)

			segments_data.append({
				"startTime": float(start_idx / ECGConfig.SAMPLE_RATE),
				"endTime": float(end_idx / ECGConfig.SAMPLE_RATE),
				"signal": convert_numpy_to_native(segment_data["ECG"]["signal"]),
				"rPeaks": convert_numpy_to_native(segment_data["ECG"]["r_peaks"]),
				"samplingRate": ECGConfig.SAMPLE_RATE,
			})
		
		return segments_data

# Função para transformar arrays NumPy em listas nativas
def convert_numpy_to_native(value):
    if isinstance(value, np.ndarray):  # Verifica se é um array NumPy
        return value.tolist()  # Converte para lista nativa
    return value  # Se não for NumPy, retorna o valor original

def analyze_ecg(record_path, num_parts=24, paper_speed=5000):
    """
    Função principal para análise de ECG.
    """
    record = wfdb.rdrecord(record_path)
    analyzer = ECGAnalyzer(record, num_parts, paper_speed)
    analyzer.analyze()