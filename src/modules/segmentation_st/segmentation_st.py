# -*- coding: utf-8 -*-
import wfdb
import neurokit2 as nk
import numpy as np
import json

from ...utils.copyWfdb import copy_record

class STSegmentDetector:
  def __init__(self, record_path):
    self.record_path = record_path

  def load_ecg_data(self):
      """
      Carrega os dados do ECG a partir de um registro WFDB.
      Atualize o caminho para o seu arquivo (sem extensão .dat).
      """
      signals, fields = wfdb.rdsamp(self.record_path)
      return signals, fields

  def preprocess_ecg(self, signals, fs):
      """
      Filtra os sinais de ECG e detecta os R-picos para cada canal.
      """
      cleaned_signals = []
      r_peaks = []
      num_channels = signals.shape[1]
      
      for channel in range(num_channels):
          sig = signals[:, channel]
          print(f"Canal {channel + 1} - Tamanho do sinal: {len(sig)}")
          cleaned = nk.ecg_clean(sig, sampling_rate=fs, method='biosppy')
          _, peaks = nk.ecg_peaks(cleaned, sampling_rate=fs)
          cleaned_signals.append(cleaned)
          r_peaks.append(peaks['ECG_R_Peaks'])
      
      return cleaned_signals, r_peaks

  def calculate_st_deviation_with_limit(self, cleaned_signal, rpeaks, fs, max_samples=None):
      """
      Calcula o desvio do segmento ST e os tempos correspondentes.
      """
      st_deviations = []
      times = []
      contador = 0

      for rpeak in rpeaks:
          if max_samples is not None and contador >= max_samples:
              break

          try:
              j_point = rpeak + int(0.08 * fs)
              st_end = j_point + int(0.08 * fs)
              baseline_start = rpeak - int(0.2 * fs)
              baseline_end = rpeak - int(0.1 * fs)
              
              baseline = np.mean(cleaned_signal[baseline_start:baseline_end])
              st_value = np.mean(cleaned_signal[j_point:st_end]) - baseline
              
              st_deviations.append(st_value)
              times.append(rpeak / fs)  # Tempo em segundos
              contador += 1
          except IndexError:
              continue

      return np.array(st_deviations), times

  def get_results(self):
      # Carregar dados e configurar
      signals, fields = self.load_ecg_data()
      fs = fields['fs']
      num_channels = signals.shape[1]
      cleaned_signals, r_peaks = self.preprocess_ecg(signals, fs)
      
      # Processar cada canal
      all_st_deviations = []
      all_times = []
      max_samples = 5000
      
      for channel in range(num_channels):
          deviations, times = self.calculate_st_deviation_with_limit(
              cleaned_signals[channel], 
              r_peaks[channel], 
              fs, 
              max_samples
          )
          all_st_deviations.append(deviations)
          all_times.append(times)
      
      # Construir JSON
      result = []
      for channel in range(num_channels):
          lead_name = fields.get('sig_name', [f'Channel {i+1}' for i in range(num_channels)])[channel]
          result.append({
              "lead": lead_name,
              "signal": all_st_deviations[channel].tolist(),
              "time": all_times[channel]
          })
      return result