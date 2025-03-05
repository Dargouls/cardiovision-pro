import wfdb
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from scipy.interpolate import interp1d
from neurokit2 import ecg_process  # Adicionado para _process_hr

from ....utils.copyWfdb import copy_record

class HeartRateAnalyzer:
    def __init__(self, record_path, desired_fs=250):
        """
        Parâmetros:
          record_path: caminho para o registro WFDB.
          desired_fs: (opcional) frequência desejada para interpolar o sinal de BPM.
                      Se None, utiliza a frequência original do registro.
        """
        self.record_path = record_path
        self.desired_fs = desired_fs

    async def _load_data(self):
        record = await copy_record(self.record_path)
        annotation = wfdb.rdann(self.record_path, 'atr')
        signal = record.p_signal[:, 0]
        fs = record.fs
        t_seconds = np.arange(len(signal)) / fs  # Tempo em segundos
        return {
            'signal': signal,
            'fs': fs,
            't_seconds': t_seconds,  # Renomeado para clareza
            'annotations': list(zip(annotation.sample, annotation.symbol))
        }

    def _process_hr(self, data):
        signals, info = ecg_process(data['signal'], sampling_rate=data['fs'])
        r_peaks = info['ECG_R_Peaks']
        rr = np.diff(r_peaks) / data['fs']
        return r_peaks, rr

    def _map_events(self, data):
        ventricular = []
        supraventricular = []
        for sample, symbol in data['annotations']:
            time = sample / data['fs']
            if symbol in ['V', 'F', 'Q']:
                ventricular.append(round(time, 2))
            elif symbol in ['A', 'S']:
                supraventricular.append(round(time, 2))
        return ventricular, supraventricular

    def _interpolate_hr(self, r_peaks, rr, fs, signal_length):
        """
        Interpola o sinal de BPM. Caso self.desired_fs seja informado,
        o vetor de tempo de saída terá a frequência desejada; do contrário, utiliza fs.
        """
        time_rr = r_peaks[:-1] / fs
        hr = 60 / rr

        if self.desired_fs is None:
            # Mantém a frequência original
            t = np.arange(signal_length) / fs
        else:
            # Calcula a duração total e cria um novo vetor de tempo com a frequência desejada
            duration = signal_length / fs
            t = np.arange(0, duration, 1 / self.desired_fs)

        interpolator = interp1d(time_rr, hr, kind='linear',
                                bounds_error=False, fill_value=(hr[0], hr[-1]))
        return interpolator(t).tolist()

    async def _full_analysis(self):
        data = await self._load_data()
        with ThreadPoolExecutor() as executor:
            future_hr = executor.submit(self._process_hr, data)
            future_events = executor.submit(self._map_events, data)
            r_peaks, rr = future_hr.result()
            ventricular, supraventricular = future_events.result()
        
        return {
            'time': data['t_seconds'].tolist(),  # Reutiliza o vetor de tempo original
            'samplingRate': data['fs'],
            'bpm_signal': self._interpolate_hr(r_peaks, rr, data['fs'], len(data['signal'])),
            'events': {
                'ventricular': ventricular,
                'supraventricular': supraventricular
            }
        }
    
    async def get_results(self):
        results = await self._full_analysis()
        return {'heart_rate': results}
