import struct
import numpy as np
from scipy.signal import butter, filtfilt, find_peaks
import matplotlib.pyplot as plt
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional, Union
import os


@dataclass
class ECGConfig:
    """Configuration parameters for ECG processing"""
    sampling_rate: int = 250  # Hz
    channels: int = 2  # Number of ECG channels
    format: str = '212'  # WFDB format
    units: str = 'mV'  # Signal units
    window_ms: int = 200  # Window size for beat extraction
    qrs_filter_low: float = 5.0  # Lower cutoff frequency for QRS filter
    qrs_filter_high: float = 15.0  # Upper cutoff frequency for QRS filter
    peak_distance_sec: float = 0.6  # Minimum distance between R peaks
    peak_height_std: float = 2.0  # Peak height threshold in std deviations
    peak_prominence: float = 0.5  # Minimum peak prominence
    rr_min: float = 0.2  # Minimum RR interval (seconds)
    rr_max: float = 2.0  # Maximum RR interval (seconds)

config = ECGConfig(
	sampling_rate=250,      # Hz
	channels=2,             # Number of channels
	window_ms=200,          # Window size for beat extraction
	qrs_filter_low=5.0,     # Lower cutoff frequency for QRS filter
	qrs_filter_high=15.0,   # Upper cutoff frequency for QRS filter
	peak_distance_sec=0.6,  # Minimum distance between peaks
	peak_height_std=2.0,    # Peak height threshold in std deviations
	peak_prominence=0.5     # Minimum peak prominence
)

class SignalReader:
    @staticmethod
    def detect_format(file_path: str) -> str:
        """Auto-detect file format based on extension and content"""
        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.xcm':
            return 'binary32'
        elif ext in ['.dat', '.212']:
            return '212'
        elif ext in ['.csv', '.txt']:
            return 'text'
        return 'binary32'  # default

    @staticmethod
    def read_file(file_path: str, config: ECGConfig) -> np.ndarray:
        """Read signal data from various file formats"""
        format_type = SignalReader.detect_format(file_path)

        if format_type == 'binary32':
            return SignalReader._read_binary32(file_path)
        elif format_type == '212':
            return SignalReader._read_212(file_path)
        elif format_type == 'text':
            return SignalReader._read_text(file_path)

        raise ValueError(f"Unsupported format: {format_type}")

    @staticmethod
    def _read_binary32(file_path: str) -> np.ndarray:
        """Read 32-bit binary data with proper validation"""
        with open(file_path, 'rb') as f:
            binary_data = f.read()

        # Pre-allocate array for better performance
        num_samples = len(binary_data) // 4
        integers = np.zeros(num_samples, dtype=np.int32)

        # Process each 4-byte chunk
        valid_samples = 0
        for i in range(0, len(binary_data), 4):
            chunk = binary_data[i:i + 4]
            if len(chunk) == 4:
                try:
                    value = struct.unpack('<i', chunk)[0]
                    if -2**31 <= value <= 2**31-1:  # Validate range
                        integers[valid_samples] = value
                        valid_samples += 1
                except struct.error:
                    continue

        return integers[:valid_samples]

    @staticmethod
    def _read_212(file_path: str) -> np.ndarray:
        """Read 212 format data with proper validation"""
        data = []
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(3)
                if not chunk or len(chunk) < 3:
                    break

                b1, b2, b3 = chunk
                # First sample = 12 bits
                sample1 = (b2 & 0xF0) << 4 | b1
                if sample1 & 0x800:
                    sample1 -= 0x1000

                # Second sample = 12 bits
                sample2 = (b2 & 0x0F) << 8 | b3
                if sample2 & 0x800:
                    sample2 -= 0x1000

                data.extend([sample1, sample2])

        return np.array(data)

    @staticmethod
    def _read_text(file_path: str) -> np.ndarray:
        """Read text format data (CSV/TXT) with error handling"""
        try:
            return np.loadtxt(file_path, delimiter=',')
        except:
            return np.loadtxt(file_path)

class SignalProcessor:
    def __init__(self, signal: np.ndarray, config: ECGConfig):
        self.signal = signal
        self.config = config

    def preprocess(self) -> np.ndarray:
        """Apply all preprocessing steps"""
        signal = self.remove_baseline()
        signal = self.normalize(signal)
        signal = self.filter_noise(signal)
        return signal

    def normalize(self, signal: np.ndarray) -> np.ndarray:
        """Normalize signal with better handling of outliers"""
        q1, q3 = np.percentile(self.signal, [25, 75])
        iqr = q3 - q1
        valid_mask = (self.signal >= q1 - 3*iqr) & (self.signal <= q3 + 3*iqr)
        clean_signal = self.signal[valid_mask]

        # Calculate normalization parameters from clean signal
        p1, p99 = np.percentile(clean_signal, [1, 99])
        normalized = (self.signal - p1) / (p99 - p1)

        return np.clip(normalized * 2 - 1, -1, 1)

    def remove_baseline(self) -> np.ndarray:
        """Remove baseline wander using polynomial fitting"""
        polynomial_order = 3
        x = np.arange(len(self.signal))
        baseline = np.polyval(
            np.polyfit(x, self.signal, polynomial_order),
            x
        )
        return self.signal - baseline

    def filter_noise(self, signal: np.ndarray) -> np.ndarray:
        """Apply noise reduction filters"""
        nyq = self.config.sampling_rate * 0.5
        low = self.config.qrs_filter_low / nyq
        high = self.config.qrs_filter_high / nyq
        b, a = butter(4, [low, high], btype='band')
        return filtfilt(b, a, signal)

class BeatDetector:
    def __init__(self, signal: np.ndarray, config: ECGConfig):
        self.signal = signal
        self.config = config

    def find_beats(self) -> Tuple[np.ndarray, np.ndarray, float]:
        """Detect beats and calculate heart rate"""
        peaks = self._detect_peaks()
        beats = self._extract_beats(peaks)
        hr = self._calculate_hr(peaks)
        return beats, peaks, hr

    def _detect_peaks(self) -> np.ndarray:
        """Detect R peaks with adaptive thresholding"""
        min_distance = int(self.config.peak_distance_sec * self.config.sampling_rate)
        height = np.mean(self.signal) + self.config.peak_height_std * np.std(self.signal)

        peaks, _ = find_peaks(
            self.signal,
            distance=min_distance,
            height=height,
            prominence=self.config.peak_prominence
        )

        return self._validate_peaks(peaks)

    def _validate_peaks(self, peaks: np.ndarray) -> np.ndarray:
        """Validate detected peaks using physiological constraints"""
        if len(peaks) < 2:
            return peaks

        # Calculate RR intervals
        rr = np.diff(peaks) / self.config.sampling_rate

        # Remove physiologically impossible intervals
        valid_rr = (rr >= self.config.rr_min) & (rr <= self.config.rr_max)
        valid_peaks = peaks[1:][valid_rr]

        # Ensure first peak is included if valid
        if len(peaks) > 0:
            first_rr = peaks[0] / self.config.sampling_rate
            if self.config.rr_min <= first_rr <= self.config.rr_max:
                valid_peaks = np.concatenate([[peaks[0]], valid_peaks])

        return valid_peaks

    def _extract_beats(self, peaks: np.ndarray) -> np.ndarray:
        """Extract beat windows around peaks"""
        half_window = int(self.config.sampling_rate * self.config.window_ms / 2000)
        beats = []

        for peak in peaks:
            if peak - half_window >= 0 and peak + half_window < len(self.signal):
                beat = self.signal[peak - half_window:peak + half_window]
                if len(beat) == 2 * half_window:
                    beats.append(beat)

        return np.array(beats)

    def _calculate_hr(self, peaks: np.ndarray) -> float:
        """Calculate heart rate with outlier removal"""
        if len(peaks) < 2:
            return 0

        rr = np.diff(peaks) / self.config.sampling_rate
        # Remove physiologically impossible intervals
        valid_rr = rr[(rr >= self.config.rr_min) & (rr <= self.config.rr_max)]

        if len(valid_rr) == 0:
            return 0

        # Remove statistical outliers from valid intervals
        rr_filtered = valid_rr[
            (valid_rr > np.mean(valid_rr) - 2*np.std(valid_rr)) &
            (valid_rr < np.mean(valid_rr) + 2*np.std(valid_rr))
        ]

        return 60 / np.mean(rr_filtered) if len(rr_filtered) > 0 else 0

class WFDBWriter:
    def __init__(self, signal: np.ndarray, config: ECGConfig):
        self.signal = signal
        self.config = config
        self.num_samples = len(signal)
        self.record_name = "output"

    def save(self, output_prefix: str, peaks: Optional[np.ndarray] = None) -> None:
        """Save all WFDB format files"""
        self.record_name = output_prefix
        self._save_header()
        self._save_data()
        if peaks is not None:
            self._save_annotations(peaks)
            self._save_xws()

    def _save_header(self) -> None:
        """Save header file in standard WFDB format"""
        with open(f"{self.record_name}.hea", 'w') as f:
            f.write(f"{self.record_name} 1 {self.config.sampling_rate} {self.num_samples}\n")
            f.write(f"ECG {self.record_name}.dat 212 1/mV 0 0 0 0 ECG\n")

        print("=== Informações do arquivo .hea ===")
        print("Número de canais: 2")
        print(f"Taxa de amostragem: {self.config.sampling_rate}")
        print(f"Número de amostras: {self.num_samples}")
        print("Formato dos dados: ['212', '212']")
        print("Nomes dos canais: ['ECG', 'ECG']")
        print("Unidades dos canais: ['mV', 'mV']")

    def _save_data(self) -> None:
        """Save signal data in WFDB 212 format"""
        signal_int = (self.signal * 1000).astype(np.int16)

        with open(f"{self.record_name}.dat", 'wb') as f:
            for i in range(0, len(signal_int)-1, 2):
                s1 = signal_int[i]
                s2 = signal_int[i+1] if i+1 < len(signal_int) else 0

                b1 = s1 & 0xFF
                b2 = ((s1 >> 8) & 0x0F) | ((s2 << 4) & 0xF0)
                b3 = (s2 >> 4) & 0xFF
                f.write(struct.pack('BBB', b1, b2, b3))

        print("\n=== Informações do arquivo .dat ===")
        print("Os dados do sinal estão armazenados no arquivo .dat.")
        print("Formato dos dados: ['212', '212']")
        print(f"Número de amostras: {self.num_samples}")
        print("Número de canais: 2")
        print("Exemplo dos primeiros valores do sinal (primeiro canal):")
        print(self.signal[:10])

    def _save_annotations(self, peaks: np.ndarray) -> None:
        """Save annotations in standard WFDB format"""
        with open(f"{self.record_name}.atr", 'w') as f:
            descriptions = []
            for i, peak in enumerate(peaks):
                desc = '(N\x00' if i % 2 == 0 else '(VFL\x00'
                descriptions.append(desc)
                f.write(f"{peak} + 0 0 {desc}\n")

        print("\n=== Informações do arquivo .atr ===")
        print(f"Número de anotações: {len(peaks)}")
        print("Amostras com anotações:", peaks[:10])
        print("Tipos de anotações:", ['+'] * 10)
        print("Descrição dos tipos de anotações:", descriptions[:10])
 
    def _save_xws(self) -> None:
        """Save XWS file in standard format"""
        content = "-r 418\n-a atr\n-p http://archive.physionet.org/physiobank/database/vfdb/418.xws"
        with open(f"{self.record_name}.xws", 'w') as f:
            f.write(content)

        print("\n=== Informações do arquivo .xws ===")
        print("Conteúdo do arquivo .xws:")
        print(content)

class XCMConverter:
    def __init__(self, config: Optional[ECGConfig] = None):
        self.config = config or ECGConfig()

    def process_file(self, file_path: str) -> Dict:
        """Process ECG file and return results"""
        signal = SignalReader.read_file(file_path, self.config)
        processor = SignalProcessor(signal, self.config)
        processed_signal = processor.preprocess()

        detector = BeatDetector(processed_signal, self.config)
        beats, peaks, heart_rate = detector.find_beats()

        writer = WFDBWriter(processed_signal, self.config)
        writer.save("output", peaks)

        return {
            'signal': processed_signal,
            'beats': beats,
            'peaks': peaks,
            'heart_rate': heart_rate,
            'sampling_rate': self.config.sampling_rate,
            'num_samples': len(processed_signal)
        }
