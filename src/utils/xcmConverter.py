import os
import numpy as np
import wfdb
from scipy.signal import butter, filtfilt, savgol_filter, find_peaks
import pywt

# Função para ler o arquivo .xcm (binário)
def read_xcm_file(file_path: str, header_size: int = 0, dtype: str = 'int8') -> np.ndarray:
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read()
        if header_size > 0:
            raw_data = raw_data[header_size:]
        dtype_size = np.dtype(dtype).itemsize
        if len(raw_data) % dtype_size != 0:
            raise ValueError(f"Tamanho do buffer ({len(raw_data)}) não é múltiplo do tipo de dado ({dtype_size}).")
        signal = np.frombuffer(raw_data, dtype=dtype)
        return signal
    except Exception as e:
        raise ValueError(f"Erro ao ler o arquivo .xcm: {str(e)}")

# Função para pré-processar o sinal
def preprocess_signal(signal: np.ndarray, fs: float, lowcut: float = 0.5, highcut: float = 40.0) -> np.ndarray:
    nyquist = 0.5 * fs
    low = lowcut / nyquist
    high = highcut / nyquist
    b, a = butter(N=5, Wn=[low, high], btype='band')
    filtered_signal = filtfilt(b, a, signal)
    baseline = np.mean(filtered_signal)
    filtered_signal -= baseline
    return filtered_signal

# Função para aplicar a transformada de wavelet
def apply_wavelet_transform(signal: np.ndarray, wavelet: str = 'db4', level: int = 3) -> np.ndarray:
    coeffs = pywt.wavedec(signal, wavelet, level=level)
    reconstructed_signal = pywt.waverec(coeffs, wavelet)
    return reconstructed_signal[:len(signal)]

# Função para detectar picos R
def detect_r_peaks_advanced(signal: np.ndarray, fs: float) -> np.ndarray:
    smoothed_signal = savgol_filter(signal, window_length=21, polyorder=3)
    wavelet_signal = apply_wavelet_transform(smoothed_signal)
    mean_signal = np.mean(wavelet_signal)
    std_signal = np.std(wavelet_signal)
    threshold = mean_signal + 0.5 * std_signal
    peaks, properties = find_peaks(wavelet_signal, height=threshold, distance=int(0.6 * fs))
    
    valid_peaks = [p for i, p in enumerate(peaks) if properties['peak_heights'][i] >= threshold]
    return np.array(valid_peaks)

# Função para salvar os arquivos WFDB
def save_wfdb_files(signal: np.ndarray, r_peaks: np.ndarray, record_name: str, output_dir: str, fs: float):
    try:
        record_name_split = os.path.splitext(record_name)[0]
        wfdb.wrsamp(
            record_name=record_name_split,
            fs=fs,
            units=['mV'],
            sig_name=['ECG'],
            p_signal=signal.reshape(-1, 1),
            write_dir=output_dir,
            fmt=['16']
        )
        atr_file_path = os.path.join(output_dir, f"{record_name}.atr")
        with open(atr_file_path, "w") as atr_file:
            for sample in r_peaks:
                if 0 <= sample < len(signal):
                    atr_file.write(f"{sample} + 0 0 0 (N\n")
        print(f"Arquivos WFDB salvos em: {output_dir}")
    except Exception as e:
        raise ValueError(f"Erro ao salvar os arquivos WFDB: {str(e)}")

# Bloco principal
def converter_xcm(xcm_file_path, output_folder):
    record_name = 'ecg-signal'
    fs = 250.0
    header_size = 128
    dtype = 'int8'
    try:
        print('Etapa 1: Leitura do arquivo XCM')
        signal = read_xcm_file(xcm_file_path, header_size=header_size, dtype=dtype)
        
        print('Etapa 2: Pré-processamento do sinal')
        filtered_signal = preprocess_signal(signal, fs)
        
        # Conversão de µV para mV
        filtered_signal = filtered_signal / 1000.0
        
        print('Etapa 3: Detecção de picos R')
        r_peaks = detect_r_peaks_advanced(filtered_signal, fs)
        
        print('Etapa 4: Salvamento dos arquivos WFDB')
        save_wfdb_files(filtered_signal, r_peaks, record_name, output_folder, fs)
        
        print('Conversão concluída com sucesso!')
    except Exception as e:
        print(f"Erro durante a conversão: {str(e)}")
