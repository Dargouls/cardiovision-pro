
import uvicorn

import wfdb
import numpy as np
import os
from .signal_processor import SignalProcessor
from .metrics_calculator import MetricsCalculator
from .plotter import ECGPlotter
from .data_manager import ECGDataManager
from .config import ECGConfig

"""
	Classe principal para análise de ECG.
"""
class ECGAnalyzer:
	def __init__(self, record, num_parts=24, samples_per_part=5000):
			self.record = record
			self.num_parts = num_parts
			self.samples_per_part = samples_per_part
			self.total_samples = record.p_signal.shape[0]
			self.part_size = self.total_samples // num_parts
			
			# Inicializar componentes
			self.signal_processor = SignalProcessor()
			self.metrics_calculator = MetricsCalculator(self.signal_processor)
			self.plotter = ECGPlotter()
			self.data_manager = ECGDataManager(self.signal_processor)
	
	def analyze(self, return_data=False):
		"""
		Realiza análise completa do ECG.
		"""
		# Calcular métricas usando o primeiro canal
		# metrics = self.metrics_calculator.calculate_metrics(self.record.p_signal[:, 0])

		# Processar segmentos
		segments_data = {}
		for part in range(self.num_parts):
				start_idx = part * self.part_size
				end_idx = min(start_idx + self.samples_per_part, self.total_samples)

				segment_data = self.data_manager.process_segment(
						self.record.p_signal,
						start_idx,
						end_idx,
						self.record.sig_name
				)

				# Garantir que os valores em leads_data sejam serializáveis
				serializable_segment_data = {}
				for key, value in segment_data.items():
						if isinstance(value, np.ndarray):  # Se for um array NumPy
								serializable_segment_data[key] = value.tolist()
						else:  # Se já for serializável
								serializable_segment_data[key] = value

				segments_data[f"segment_{part + 1}"] = {
						"start_time": float(start_idx / ECGConfig.SAMPLE_RATE),
						"end_time": float(end_idx / ECGConfig.SAMPLE_RATE),
						"leads_data": serializable_segment_data
				}

# Processando os dados em segments_data
		for segment, segment_data in segments_data.items():
				leads_data = segment_data['leads_data']
				for key, value in leads_data.items():
						if isinstance(value, dict):  # Se for um dicionário (como 'ECG')
								for sub_key, sub_value in value.items():
										# Transformando arrays NumPy em listas nativas
										value[sub_key] = convert_numpy_to_native(sub_value)
										
						else:
								# Se o valor não for um dicionário, apenas converta o valor
								leads_data[key] = convert_numpy_to_native(value)

		return segments_data

	def analyze_img(self):
			"""
			Realiza análise completa do ECG.
			"""
			# Calcular métricas usando o primeiro canal
			metrics = self.metrics_calculator.calculate_metrics(self.record.p_signal[:, 0])
			self.metrics_calculator.save_metrics(metrics)
			
			# Processar e salvar segmentos
			segments_data = {}
			for part in range(self.num_parts):
					start_idx = part * self.part_size
					end_idx = min(start_idx + self.samples_per_part, self.total_samples)
					
					segment_data = self.data_manager.process_segment(
							self.record.p_signal,
							start_idx,
							end_idx,
							self.record.sig_name
					)
					
					segments_data[f"segment_{part + 1}"] = {
							"start_time": start_idx / ECGConfig.SAMPLE_RATE,
							"end_time": end_idx / ECGConfig.SAMPLE_RATE,
							"leads_data": segment_data
					}
			
			self.data_manager.save_segments_data(segments_data)
			
			# Plotar segmentos
			for part in range(self.num_parts):
					segment = segments_data[f"segment_{part + 1}"]
					segment_info = {
							"segment_number": part + 1,
							"total_segments": self.num_parts,
							"start_time": segment["start_time"],
							"end_time": segment["end_time"]
					}
					self.plotter.plot_segment(segment["leads_data"], segment_info)
            
# Função para transformar arrays NumPy em listas nativas
def convert_numpy_to_native(value):
    if isinstance(value, np.ndarray):  # Verifica se é um array NumPy
        return value.tolist()  # Converte para lista nativa
    return value  # Se não for NumPy, retorna o valor original

def analyze_ecg(record_path, num_parts=24, samples_per_part=5000):
    """
    Função principal para análise de ECG.
    """
    print('record_path: ', record_path)
    record = wfdb.rdrecord(record_path)
    analyzer = ECGAnalyzer(record, num_parts, samples_per_part)
    analyzer.analyze()
    print("Análise completa. Arquivos salvos:")
