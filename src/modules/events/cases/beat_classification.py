import wfdb
import numpy as np
import antropy as ant
from concurrent.futures import ProcessPoolExecutor
from neurokit2 import ecg_process
import pywt

from ....utils.copyWfdb import copy_record

class BeatClassifier:
    def __init__(self, record_path):
        self.record_path = record_path

    async def _load_ecg(self):
        record = await copy_record(self.record_path)
        return record.p_signal[:, 0], record.fs

    def _classify_window(self, window):
        if len(window) < 30:
            return 'normal'

        entropy = ant.sample_entropy(window, order=2, metric='chebyshev')

        if entropy > 1.2:
            return 'pvc'
        elif entropy > 0.65:
            return 'pac'
        else:
            return 'normal'

    def _detect_anomalies(self, signal):
        coeffs = pywt.wavedec(signal, 'db4', level=5)
        cD5 = coeffs[-1]
        return np.where(np.abs(cD5) > 2*np.std(cD5))[0]
        
    async def _analyze_beats(self):
        signal, fs = await self._load_ecg()
        _, info = ecg_process(signal, fs)
        r_peaks = info['ECG_R_Peaks']

        windows = [signal[r_peaks[i]:r_peaks[i+1]] for i in range(len(r_peaks)-1)]

        with ProcessPoolExecutor(max_workers=6) as executor:
            classes = list(executor.map(self._classify_window, windows, chunksize=50))

        counts = {
            'normal': classes.count('normal'),
            'pvc': classes.count('pvc'),
            'pac': classes.count('pac')
        }

        total = sum(counts.values())
        percentages = {
            'normal_pct': round((counts['normal'] / total * 100), 2) if total > 0 else 0,
            'pvc_pct': round((counts['pvc'] / total * 100), 2) if total > 0 else 0,
            'pac_pct': round((counts['pac'] / total * 100), 2) if total > 0 else 0
        }

        # Combinar contagens e porcentagens em um único dicionário
        return {
            'beat_classification': {
                **counts,
                **percentages
            }
        }

    async def get_results(self):
        return await self._analyze_beats()