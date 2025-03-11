import wfdb
import numpy as np
import neurokit2 as nk
import asyncio
from concurrent.futures import ProcessPoolExecutor
import os

class STSegmentDetector:
    def __init__(self, record_path, st_offset_ms=60):  # st_offset_ms=60 é o valor padrão
        self.record_path = record_path
        self.st_offset_ms = st_offset_ms

    async def load_data(self):
        """Carrega os dados do registro ECG."""
        record = wfdb.rdrecord(self.record_path)
        return {
            'signals': record.p_signal.astype(np.float32),  # Garantir precisão numérica
            'fs': record.fs,
            't_seconds': np.arange(record.p_signal.shape[0]) / record.fs
        }

    def _process_lead(self, signal, fs, t_seconds, samples_offset, lead_number):
        """Processa uma derivação individual do ECG e retorna apenas dados válidos."""
        try:
            # Limpeza do sinal para remover ruídos e artefatos
            cleaned_signal = nk.ecg_clean(signal, sampling_rate=fs, method="neurokit")
            
            # Processamento do ECG com o sinal limpo
            _, info = nk.ecg_process(cleaned_signal, sampling_rate=fs)
            r_peaks = info['ECG_R_Peaks']
            
            # Delineamento QRS usando Transformada Wavelet Discreta (dwt)
            _, delineate_info = nk.ecg_delineate(
                cleaned_signal, r_peaks, sampling_rate=fs, method="dwt"
            )
            qrs_offsets = np.array(delineate_info.get("ECG_S_Peaks", []))
            
            # Cálculo dos valores ST com operações vetorizadas
            valid_mask = ~np.isnan(qrs_offsets)
            valid_offsets = qrs_offsets[valid_mask].astype(int)
            measure_indices = valid_offsets + samples_offset
            
            # Máscaras para índices válidos
            within_bounds = (measure_indices >= 0) & (measure_indices < len(signal))
            valid_measure_indices = measure_indices[within_bounds]
            
            # Coleta apenas os valores e tempos válidos
            st_values = signal[valid_measure_indices].tolist()
            st_times = t_seconds[valid_measure_indices].tolist()
            
            return {
                'lead': lead_number,
                'st_values': st_values,
                'st_times': st_times
            }
        except Exception as e:
            return {'lead': lead_number, 'error': str(e)}

    async def detect_st_segments(self):
        """Detecta os segmentos ST em todas as derivações usando paralelismo otimizado."""
        data = await self.load_data()
        signals = data['signals']
        fs = data['fs']
        samples_offset = int((self.st_offset_ms / 1000) * fs)  # Conversão de ms para amostras
        
        # Processamento paralelo com limite de workers
        loop = asyncio.get_event_loop()
        with ProcessPoolExecutor(max_workers=min(4, os.cpu_count())) as executor:
            tasks = [
                loop.run_in_executor(
                    executor,
                    self._process_lead,
                    signals[:, lead],
                    fs,
                    data['t_seconds'],
                    samples_offset,
                    lead + 1
                )
                for lead in range(signals.shape[1])
            ]
            results = await asyncio.gather(*tasks)
        
        return results

    async def get_results(self):
        """Retorna os resultados da detecção dos segmentos ST com apenas dados válidos."""
        results = await self.detect_st_segments()
        # Opcional: Filtrar resultados com erro
        valid_results = [r for r in results if 'error' not in r]
        return {'segmentation_st': valid_results}