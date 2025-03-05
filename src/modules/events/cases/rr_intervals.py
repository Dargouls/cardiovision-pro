import wfdb
import numpy as np
from neurokit2 import ecg_process

from ....utils.copyWfdb import copy_record

class RRIntervalsAnalyzer:
    def __init__(self, record_path):
        self.record_path = record_path

    async def _get_rr(self):
        record = await copy_record(self.record_path)
        signal = record.p_signal[:,0]
        fs = record.fs
        
        _, info = ecg_process(signal, fs)
        r_peaks = info['ECG_R_Peaks']
        rr = np.diff(r_peaks) / fs
        
        return {
            'rr_intervals': rr.tolist(),
            'time': (r_peaks[:-1] / fs).tolist()
        }

    async def get_results(self):
        results = await self._get_rr()
        return {'rr_intervals': results}