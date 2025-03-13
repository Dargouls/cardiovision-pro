import wfdb
import numpy as np
from scipy.signal import find_peaks, butter, filtfilt
from neurokit2 import ecg_process

from ...utils.copyWfdb import copy_record

class STSegmentDetector:
    """
    Classe para análise dos eventos ST do ECG.
    Para cada derivação (lead), retorna um objeto contendo:
      - time: array com os tempos (em segundos) dos eventos (picos R)
      - signal: array onde cada elemento é um array [st1, st2] com os valores dos segmentos ST.
    """

    def __init__(self, record_path):
        """
        Inicializa o detector com o caminho do registro.
        
        :param record_path: Caminho para o registro ECG.
        """
        self.record_path = record_path

    async def _get_events(self):
        record = await copy_record(self.record_path)
        fs = record.fs
        results = []

        # Processa cada derivação (lead) individualmente.
        for channel in range(record.n_sig):
            signal = record.p_signal[:, channel]
            _, info = ecg_process(signal, fs)
            r_peaks = info['ECG_R_Peaks']
            
            times = []
            st_signals = []

            # Para cada pico R, exceto o último para evitar índice fora do limite
            for r in r_peaks[:-1]:
                # Define a linha de base usando os 40 ms anteriores ao pico R
                pr_start = max(0, r - int(0.04 * fs))
                baseline = np.mean(signal[pr_start:r]) if r > pr_start else 0

                # Calcula ST1: 40 ms após o pico R
                idx_st1 = r + int(0.04 * fs)
                st1_val = (signal[idx_st1] - baseline) * 1000 if idx_st1 < len(signal) else None

                # Calcula ST2: 80 ms após o pico R
                idx_st2 = r + int(0.08 * fs)
                st2_val = (signal[idx_st2] - baseline) * 1000 if idx_st2 < len(signal) else None

                times.append(r / fs)
                st_signals.append([st1_val, st2_val])

            lead_name = record.sig_name[channel] if hasattr(record, "sig_name") else f"Lead {channel}"
            results.append({
                "lead": lead_name,
                "time": times,
                "signal": st_signals
            })

        return results

    async def get_results(self):
        """
        Obtém os resultados da análise dos eventos ST.
        
        :return: Array de objetos para cada derivação, com as variáveis 'time' e 'signal'.
        """
        return await self._get_events()
