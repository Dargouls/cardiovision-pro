import wfdb
import numpy as np

class DataLoader:
    def __init__(self, record_path):
        self.record_path = record_path
        self._load_raw_data()

    def _load_raw_data(self):
        """Carrega dados brutos do disco"""
        self.record = wfdb.rdrecord(self.record_path)
        self.annotation = wfdb.rdann(self.record_path, 'atr')
        self.ecg_signal = self.record.p_signal[:, 0]
        self.fs = self.record.fs
        self.t = np.arange(len(self.ecg_signal)) / self.fs