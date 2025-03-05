import wfdb
from scipy.signal import welch
from scipy.interpolate import interp1d
from neurokit2 import ecg_process

import numpy as np

from ....utils.copyWfdb import copy_record

class SpectralAnalyzer:
    def __init__(self, record_path):
        self.record_path = record_path

    async def _get_rr_intervals(self):
        record = await copy_record(self.record_path)
        signal = record.p_signal[:,0]
        fs = record.fs
        
        _, info = ecg_process(signal, fs)
        r_peaks = info['ECG_R_Peaks']
        return np.diff(r_peaks) / fs

    async def _calculate_spectrum(self):
        rr = await self._get_rr_intervals()
        fs_resample = 4  # Hz
        time = np.cumsum(rr)
        interpolator = interp1d(time, rr, kind='linear', 
                               bounds_error=False, fill_value='extrapolate')
        new_time = np.arange(time[0], time[-1], 1/fs_resample)
        rr_interp = interpolator(new_time)
        
        freqs, psd = welch(rr_interp, fs=fs_resample, nperseg=256)
        
        return {
            'freqs': freqs.tolist(),
            'power': (psd * 1e6).tolist()  # Convert to ms²/Hz
        }

    async def get_results(self):
        results = await self._calculate_spectrum()
        
        return {'spectral_analysis': results}