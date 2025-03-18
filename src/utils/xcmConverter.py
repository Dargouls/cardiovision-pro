import os
import numpy as np
import wfdb
from scipy.signal import butter, filtfilt, savgol_filter, find_peaks
import pywt

# Função para ler o arquivo .xcm (binário)
def read_xcm_file(file_path: str, header_size: int = 0, dtype: str = 'int8') -> np.ndarray:
    """
    Lê um arquivo .xcm binário e retorna o sinal de ECG como um array numpy.
    
    Parâmetros:
        file_path (str): Caminho do arquivo .xcm.
        header_size (int): Tamanho do cabeçalho a ser ignorado (em bytes).
        dtype (str): Tipo de dado para interpretar os bytes (ex: 'int8', 'int16').
    
    Retorna:
        np.ndarray: Sinal de ECG.
    """
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read()
        if header_size > 0:
            raw_data = raw_data[header_size:]
        dtype_size = np.dtype(dtype).itemsize
        if len(raw_data) % dtype_size != 0:
            raise ValueError(f"Tamanho do buffer ({len(raw_data)}) não é múltiplo do tamanho do tipo de dado ({dtype_size}).")
        signal = np.frombuffer(raw_data, dtype=dtype)
        return signal
    except Exception as e:
        raise ValueError(f"Erro ao ler o arquivo .xcm: {str(e)}")

# Função para pré-processar o sinal (filtro passa-banda e remoção de baseline wander)
def preprocess_signal(signal: np.ndarray, fs: float, lowcut: float = 0.5, highcut: float = 40.0) -> np.ndarray:
    """
    Aplica um filtro passa-banda ao sinal e remove o baseline (desvio médio).
    
    Parâmetros:
        signal (np.ndarray): Sinal de ECG.
        fs (float): Frequência de amostragem (Hz).
        lowcut (float): Frequência mínima do filtro passa-banda.
        highcut (float): Frequência máxima do filtro passa-banda.
    
    Retorna:
        np.ndarray: Sinal filtrado.
    """
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
    """
    Aplica a transformada de wavelet e reconstrói o sinal.
    
    Parâmetros:
        signal (np.ndarray): Sinal de ECG.
        wavelet (str): Nome do wavelet a ser utilizado (padrão: 'db4').
        level (int): Nível de decomposição.
    
    Retorna:
        np.ndarray: Sinal reconstruído a partir da decomposição wavelet.
    """
    coeffs = pywt.wavedec(signal, wavelet, level=level)
    reconstructed_signal = pywt.waverec(coeffs, wavelet)
    return reconstructed_signal[:len(signal)]  # Garante que o sinal tenha o mesmo comprimento

# Função para detectar picos R com método avançado
def detect_r_peaks_advanced(signal: np.ndarray, fs: float) -> np.ndarray:
    """
    Detecta picos R usando um método avançado com limiar adaptativo e validação dos intervalos.
    
    Parâmetros:
        signal (np.ndarray): Sinal de ECG (pré-processado).
        fs (float): Frequência de amostragem (Hz).
    
    Retorna:
        np.ndarray: Índices dos picos R detectados.
    """
    # Suavização do sinal para reduzir ruídos
    smoothed_signal = savgol_filter(signal, window_length=21, polyorder=3)
    # Aplicação da transformada de wavelet
    wavelet_signal = apply_wavelet_transform(smoothed_signal)
    # Definição de limiar adaptativo
    mean_signal = np.mean(wavelet_signal)
    std_signal = np.std(wavelet_signal)
    threshold = mean_signal + 0.5 * std_signal
    peaks, properties = find_peaks(wavelet_signal, height=threshold, distance=int(0.6 * fs))
    
    # Validação dos picos detectados
    valid_peaks = []
    for i in range(len(peaks)):
        if properties["peak_heights"][i] < threshold:
            continue
        if i > 0:
            rr_interval = (peaks[i] - peaks[i - 1]) / fs * 1000  # em milissegundos
            if not (400 < rr_interval < 1200):
                continue
        if i > 0 and (peaks[i] - peaks[i - 1]) < int(0.3 * fs):
            continue
        valid_peaks.append(peaks[i])
    
    return np.array(valid_peaks)

# Função para salvar os arquivos WFDB (.dat, .hea e .atr)
def save_wfdb_files(signal: np.ndarray, r_peaks: np.ndarray, record_name: str, output_dir: str, fs: float):
    """
    Salva o sinal de ECG e as anotações dos picos R no formato WFDB.
    
    Parâmetros:
        signal (np.ndarray): Sinal de ECG (pré-processado).
        r_peaks (np.ndarray): Índices dos picos R.
        record_name (str): Caminho e nome base para os arquivos WFDB (sem extensão e sem ponto).
        fs (float): Frequência de amostragem (Hz).
    """
    try:
        # Garante que record_name não contenha ponto (removendo a extensão, se houver)
        record_name_split = os.path.splitext(record_name)[0]

        # Salvar o sinal em arquivos .dat e .hea
        wfdb.wrsamp(
            record_name=record_name_split,
            fs=fs,
            units=['mV'],
            sig_name=['ECG'],
            p_signal=signal.reshape(-1, 1),
            write_dir=output_dir,
            fmt=['16']
        )
        
        # Salvar as anotações dos picos R em arquivo .atr
        atr_file_path = output_dir + "/" +record_name + ".atr"
        with open(atr_file_path, "w") as atr_file:
            for sample in r_peaks:
                if 0 <= sample < len(signal):
                    symbol = '+'  # Símbolo padrão para anotação
                    aux_note = '(N'  # Notação para batimento normal
                    atr_file.write(f"{sample} {symbol} 0 0 0 {aux_note}\n")
        print(f"Arquivos WFDB salvos com sucesso na pasta: {os.path.dirname(record_name)}")
        
    except Exception as e:
        raise ValueError(f"Erro ao salvar os arquivos WFDB: {str(e)}")

# Bloco principal
def converter_xcm(xcm_file_path, output_folder):
    # Define o nome base para o registro WFDB (incluindo a pasta de saída)
    record_name = 'ecg-signal'
    
    # Parâmetros de conversão
    fs = 250.0         # Frequência de amostragem (ajuste conforme necessário)
    header_size = 128  # Tamanho do cabeçalho do arquivo XCM (em bytes)
    dtype = 'int8'     # Tipo de dado (ajuste conforme o formato do seu arquivo XCM)
    
    try:
        print('Etapa 1: Leitura do arquivo XCM')
        signal = read_xcm_file(xcm_file_path, header_size=header_size, dtype=dtype)
        
        print('Etapa 2: Pré-processamento do sinal')
        filtered_signal = preprocess_signal(signal, fs)
        
        print('Etapa 3: Detecção avançada de picos R')
        r_peaks = detect_r_peaks_advanced(filtered_signal, fs)
        
        print('Etapa 4: Salvamento dos arquivos WFDB (.dat, .hea e .atr)')
        save_wfdb_files(filtered_signal, r_peaks, record_name, output_folder, fs)
        
        print('Conversão concluida com sucesso!')

    except Exception as e:
        print(f"Erro durante o processo de conversão: {str(e)}")