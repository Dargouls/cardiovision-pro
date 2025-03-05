import wfdb
import pywt
import nolds
import numpy as np
from neurokit2 import ecg_process
from concurrent.futures import ThreadPoolExecutor

from ....utils.copyWfdb import copy_record

class BeatClassifier:
    def __init__(self, record_path):
        self.record_path = record_path
    
    async def _load_ecg(self):
        record = await copy_record(self.record_path)

        return record.p_signal[:,0], record.fs

    def _detect_anomalies(self, signal):
        coeffs = pywt.wavedec(signal, 'db4', level=5)
        cD5 = coeffs[-1]
        return np.where(np.abs(cD5) > 2*np.std(cD5))[0]

    def _classify_window(self, window):
        if len(window) < 10: return 'normal'
        entropy = nolds.sampen(window)
        return 'PVC' if entropy > 1.5 else 'PAC' if entropy > 0.8 else 'normal'

    async def _analyze_beats(self):
        signal, fs = await self._load_ecg()
        anomalies = self._detect_anomalies(signal)
        print('anomalias: ', anomalies)
        _, info = ecg_process(signal, fs)
        r_peaks = info['ECG_R_Peaks']
        
        windows = []
        for i in range(len(r_peaks)-1):
            start = r_peaks[i]
            end = r_peaks[i+1]
            windows.append(signal[start:end])
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            classes = list(executor.map(self._classify_window, windows))
        
        counts = {
            'normal': classes.count('normal'),
            'PVC': classes.count('PVC'),
            'PAC': classes.count('PAC')
        }
        
        return {'beat_classification': counts}

    async def get_results(self):
        results = await self._analyze_beats()
        return results