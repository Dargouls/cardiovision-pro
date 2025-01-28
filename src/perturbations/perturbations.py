import wfdb
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import json
import datetime
from scipy.signal import welch, butter, filtfilt, hilbert
from scipy import stats

plt.rcParams['axes.titlesize'] = 10
plt.rcParams['axes.labelsize'] = 8

class AnalisadorInterferencia:
    PARAMS = {
        'interferencia_rede': {
            'freq': [50, 60],     # Frequências da rede elétrica em Hz
            'limiar': 5.0         # Limiar para considerar interferência significativa
        },
        'ruido_base': {
            'janela': 100,        # Tamanho da janela para análise de ruído de base
            'limiar': 2.0         # Limiar em desvios padrão
        },
        'mau_contato': {
            'limiar_var': 0.001,  # Variância mínima para detectar mau contato
            'duracao_min': 0.1    # Duração mínima em segundos
        },
        'tremor_muscular': {
            'freq_min': 20,       # Frequência mínima para tremor muscular
            'freq_max': 50,       # Frequência máxima para tremor muscular
            'limiar': 3.0         # Limiar para detecção
        },
        'desconexao': {
            'limiar_amp': 0.05,   # Amplitude mínima para considerar desconexão
            'duracao_min': 0.2    # Duração mínima em segundos
        }
    }

    def __init__(self, caminho_base):
        self.caminho_base = Path(caminho_base)

    def carregar_sinal(self, nome_registro, canal=0):
        try:
            caminho_registro = self.caminho_base / nome_registro
            registro = wfdb.rdrecord(str(caminho_registro))
            return registro.p_signal[:, canal], registro.fs
        except Exception as e:
            raise ValueError(f"Erro ao carregar registro: {str(e)}")

    def detectar_interferencia_rede(self, sinal, fs):
        """Detecta interferência da rede elétrica."""
        freq, psd = welch(sinal, fs=fs, nperseg=int(fs))
        scores = {}

        for freq_rede in self.PARAMS['interferencia_rede']['freq']:
            idx = np.argmin(np.abs(freq - freq_rede))
            potencia = psd[idx]
            potencia_vizinha = np.mean(psd[max(0, idx-2):idx] + psd[idx+1:idx+3])
            scores[freq_rede] = potencia / potencia_vizinha if potencia_vizinha > 0 else 0

        return scores, freq, psd

    def detectar_mau_contato(self, sinal, fs):
        """Detecta regiões com mau contato do eletrodo."""
        amostras_min = int(self.PARAMS['mau_contato']['duracao_min'] * fs)
        var_local = np.array([np.var(sinal[i:i+amostras_min])
                            for i in range(0, len(sinal)-amostras_min)])

        regioes_mau_contato = np.where(var_local < self.PARAMS['mau_contato']['limiar_var'])[0]
        return regioes_mau_contato

    def detectar_tremor_muscular(self, sinal, fs):
        """Detecta interferência por tremor muscular."""
        freq, psd = welch(sinal, fs=fs, nperseg=int(fs))

        # Região de frequência do tremor muscular
        mask = (freq >= self.PARAMS['tremor_muscular']['freq_min']) & \
               (freq <= self.PARAMS['tremor_muscular']['freq_max'])

        potencia_tremor = np.mean(psd[mask])
        potencia_total = np.mean(psd)

        return potencia_tremor / potencia_total if potencia_total > 0 else 0

    def detectar_desconexao(self, sinal, fs):
        """Detecta momentos de desconexão total do eletrodo."""
        amostras_min = int(self.PARAMS['desconexao']['duracao_min'] * fs)
        amplitude = np.abs(sinal)

        # Encontra regiões com amplitude muito baixa
        regioes_desconexao = np.where(amplitude < self.PARAMS['desconexao']['limiar_amp'])[0]

        # Agrupa regiões contínuas
        if len(regioes_desconexao) > 0:
            gaps = np.diff(regioes_desconexao)
            breaks = np.where(gaps > 1)[0]

            grupos = []
            inicio = 0
            for b in breaks:
                if b - inicio >= amostras_min:
                    grupos.append((regioes_desconexao[inicio], regioes_desconexao[b]))
                inicio = b + 1

            if len(regioes_desconexao) - inicio >= amostras_min:
                grupos.append((regioes_desconexao[inicio], regioes_desconexao[-1]))

            return grupos
        return []

    def analisar_interferencias(self, nome_registro, duracao=10, canal=0):
        """Analisa interferências e problemas técnicos no sinal."""
        try:
            sinal, fs = self.carregar_sinal(nome_registro, canal)

            # Janela de análise
            janela_sinal = sinal[:int(duracao * fs)]
            tempo = np.arange(len(janela_sinal)) / fs

            # Análises
            scores_rede, freq, psd = self.detectar_interferencia_rede(janela_sinal, fs)
            regioes_mau_contato = self.detectar_mau_contato(janela_sinal, fs)
            score_tremor = self.detectar_tremor_muscular(janela_sinal, fs)
            desconexoes = self.detectar_desconexao(janela_sinal, fs)

            # Dados para o cliente
            dados_cliente = {
                'sinal': janela_sinal.tolist(),
                'tempo': tempo.tolist(),
                'frequencias': freq.tolist(),
                'psd': psd.tolist(),
                'interferencia_rede': scores_rede,
                'mau_contato': len(regioes_mau_contato),
                'score_tremor': score_tremor,
                'desconexoes': len(desconexoes)
            }

            return dados_cliente

        except Exception as e:
            print(f"Erro ao analisar sinal: {str(e)}")
            return None
