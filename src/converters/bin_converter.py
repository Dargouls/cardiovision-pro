import os
import re
import numpy as np
import wfdb
from datetime import datetime
from enum import Enum
from typing import List, Tuple

class FileType(Enum):
    HEADER     = 1
    DATA       = 2
    ANNOTATION = 3

class BinConverter:
    """BIN Holter → WFDB (.dat/.hea/.atr)
       – 512-byte header, 1024-byte footer
       – 3 canais, 25 mm/s
       – packing 212 otimizado (<1 s em 130 MB)"""

    HEADER_SIZE      = 512
    FOOTER_SIZE      = 1024
    DEFAULT_FS       = 256       # Hz se header inválido
    COUNTS_PER_MV    = 200       # ganho: 200 contagens/mV

    def __init__(self, bin_file: str):
        self.bin_file: str = bin_file
        self.header: bytes = b""
        self.footer: bytes = b""
        self.ecg_data: np.ndarray = None  # float32 (mV)
        self.sample_rate: int = None
        self.annotations: List[Tuple[int,str]] = []

    def analyze_file_structure(self) -> None:
        """Carrega header, ECG e footer via memmap."""
        size = os.path.getsize(self.bin_file)
        if size < self.HEADER_SIZE + self.FOOTER_SIZE:
            raise ValueError("Arquivo BIN muito pequeno")
        mm = np.memmap(self.bin_file, dtype=np.uint8, mode='r')
        # header e footer crus
        self.header = mm[:self.HEADER_SIZE].tobytes()
        self.footer = mm[-self.FOOTER_SIZE:].tobytes()
        # ECG cru int16 → float32 (mV)
        raw16 = mm[self.HEADER_SIZE:-self.FOOTER_SIZE].view(np.int16)
        self.ecg_data = raw16.astype(np.float32) * 0.001
        # sample rate do header
        fs = int.from_bytes(self.header[2:4], 'little')
        self.sample_rate = fs if 100 <= fs <= 1000 else self.DEFAULT_FS

    def extract_annotations(self) -> None:
        """Extrai pares (posição, símbolo) do footer como uint16."""
        buf = self.footer
        # assume footer contém N registros de 4 bytes: [pos_lo,pos_hi,sym_lo,sym_hi]
        n = len(buf) // 4
        ann: List[Tuple[int,str]] = []
        for i in range(n):
            off = i * 4
            pos = int.from_bytes(buf[off:off+2], 'little')  # uint16
            code = buf[off+2]
            if pos == 0:
                continue
            c = chr(code)
            if not (c.isprintable() and not c.isspace()):
                c = 'N'
            ann.append((pos, c))
        # ordena por posição e remove possíveis repetições descendentes
        ann.sort(key=lambda x: x[0])
        # opcional: filtrar duplicatas ou não monotônicos:
        clean: List[Tuple[int,str]] = []
        last = -1
        for p,c in ann:
            if p > last:
                clean.append((p,c))
                last = p
        self.annotations = clean

    def convert_to_wfdb(self, output_dir: str) -> None:
        """Gera .dat (212), .hea e .atr (se houver)."""
        os.makedirs(output_dir, exist_ok=True)
        base = os.path.splitext(os.path.basename(self.bin_file))[0]

        # ─── 1) Prepara 3 canais ────────────────────────────────────────────
        raw_int = (self.ecg_data * self.COUNTS_PER_MV).astype(np.int16)
        total = raw_int.size
        # garante número par de amostras
        if total % 2 != 0:
            raw_int = np.append(raw_int, raw_int[-1])
            total += 1
        # ajusta para múltiplo de 3 canais
        n_frames = total // 3
        raw_int   = raw_int[: n_frames * 3]
        ecg3 = raw_int.reshape(n_frames, 3)
        # força número par de frames
        if ecg3.shape[0] % 2 != 0:
            ecg3 = ecg3[:-1]
        # agora temos n_pairs = ecg3.shape[0]//2 pares
        n_pairs = ecg3.shape[0] // 2

        # ─── 2) Packing 212 vetorizado ─────────────────────────────────────
        even = (ecg3[0::2].astype(np.uint32) & 0x0FFF)
        odd  = (ecg3[1::2].astype(np.uint32) & 0x0FFF)
        word = (odd << 12) | even    # shape (n_pairs, 3)
        # little-endian u4 → view como bytes → pega 3 bytes
        b4 = word.astype('<u4').view(np.uint8).reshape(-1, 4)
        b3 = b4[:, :3]
        dat_path = os.path.join(output_dir, f"{base}.dat")
        b3.tofile(dat_path)

        # ─── 3) Grava .hea ─────────────────────────────────────────────────
        hea_path = os.path.join(output_dir, f"{base}.hea")
        with open(hea_path, 'w') as f:
            f.write(f"{base} 3 {ecg3.shape[0]} {self.sample_rate}\n")
            for i in range(3):
                offset = i * 3
                f.write(
                    f"ECG 212 1 0 {offset} {self.COUNTS_PER_MV} 0 mV\n"
                )

        # ─── 4) Grava .atr ─────────────────────────────────────────────────
        self.extract_annotations()
        if self.annotations:
            samples = np.array([p for p,_ in self.annotations], dtype=np.int32)
            symbols = [s for _,s in self.annotations]
            wfdb.wrann(
                record_name=base,
                extension='atr',
                sample=samples,
                symbol=symbols,
                fs=self.sample_rate,
                write_dir=output_dir
            )
            print(f"- {base}.atr gerado ({len(symbols)} eventos)")
        else:
            print("Nenhuma anotação válida; .atr não gerado")

        # Relatório final
        size_mb = os.path.getsize(dat_path) / 1024**2
        print("Output em", output_dir)
        print(f"- {base}.dat → {size_mb:.1f} MiB")
        print(f"- {base}.hea")
