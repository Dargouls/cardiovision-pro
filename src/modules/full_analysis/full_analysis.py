# full_analysis.py
import os
import wfdb
import numpy as np
from scipy.signal import resample_poly
from pathlib import Path
from fastapi import HTTPException

from ...utils.copyWfdb import copy_record

class ECGAnalyzer:
    """
    Classe para análise completa do sinal de ECG: leitura, reamostragem e retorno
    de todos os canais em formato compatível com API.
    """

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        if not self.base_path.exists():
            raise FileNotFoundError(f"Diretório não encontrado: {base_path}")

    def list_records(self) -> list[str]:
        """Retorna lista de registros WFDB disponíveis (sem extensão)."""
        hea_files = list(self.base_path.glob('*.hea'))
        return [p.stem for p in hea_files if (p.with_suffix('.dat')).exists()]

    async def _load_record(self, record_name: str) -> tuple[np.ndarray, float]:
        """
        Lê o registro WFDB via copy_record e retorna tupla (sinal, fs).
        Signal pode ser 1D (mono) ou 2D (multi-canais).
        """
        record_path = self.base_path / record_name
        # copia para temp e lê
        record = await copy_record(record_path)
        signal = record.p_signal  # shape (n_samples, n_channels)
        fs = record.fs
        if fs <= 0:
            raise ValueError(f"Frequência inválida no registro: {fs}")
        return signal, fs

    async def save_complete_analysis(self,
                                     record_name: str,
                                     desired_frequency: int) -> dict:
        """
        Carrega e analisa o ECG completo de todos os canais.
        Reamostra para desired_frequency (Hz) com filtro anti-aliasing.
        Retorna dict:
          {
            "full_analysis": [
               {"data": [...], "time": [...]},  # canal 0
               {"data": [...], "time": [...]},  # canal 1
               ...
            ]
          }
        """
        # validar frequência
        if desired_frequency <= 0:
            raise HTTPException(status_code=400, detail="desired_frequency deve ser > 0")

        # carregar sinal e fs
        signal, fs = await self._load_record(record_name)
        # garantir 2D
        if signal.ndim == 1:
            signal = signal[:, np.newaxis]

        # calcular fatores up/down inteiros
        from fractions import Fraction
        frac = Fraction(desired_frequency, fs).limit_denominator()
        up, down = frac.numerator, frac.denominator

        duration = signal.shape[0] / fs
        results = []

        # processar cada canal separadamente
        for ch_idx in range(signal.shape[1]):
            chan = signal[:, ch_idx]
            # reamostrar
            resampled = resample_poly(chan, up, down)
            # timestamps iguais para todos canais
            new_n = len(resampled)
            times = np.linspace(0, duration, new_n, endpoint=False)
            results.append({
                "data": resampled.tolist(),
                "time": times.tolist()
            })

        return {"full_analysis": results}