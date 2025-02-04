import wfdb
import numpy as np
import json
from pathlib import Path
from scipy.signal import welch

class AnalisadorInterferencia:
    PARAMS = {
        'interferencia_rede': {
            'freq': [50, 60],
            'limiar': 5.0
        },
        'ruido_base': {
            'janela': 100,
            'limiar': 2.0
        },
        'mau_contato': {
            'limiar_var': 0.001,
            'duracao_min': 0.1
        },
        'tremor_muscular': {
            'freq_min': 20,
            'freq_max': 50,
            'limiar': 3.0
        },
        'desconexao': {
            'limiar_amp': 0.05,
            'duracao_min': 0.2
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
        freq, psd = welch(sinal, fs=fs, nperseg=int(fs))
        freq = np.round(freq).astype(int)
        interferencias = []

        for freq_rede in self.PARAMS['interferencia_rede']['freq']:
            idx = np.argmin(np.abs(freq - freq_rede))
            potencia = psd[idx]
            potencia_vizinha = np.mean(psd[max(0, idx-2):idx] + psd[idx+1:idx+3])
            score = potencia / potencia_vizinha if potencia_vizinha > 0 else 0
            interferencias.append({"frequencia": int(freq_rede), "score": score})

        return interferencias, freq.tolist(), psd.tolist()

    def detectar_mau_contato(self, sinal, fs):
        amostras_min = int(self.PARAMS['mau_contato']['duracao_min'] * fs)
        var_local = np.array([np.var(sinal[i:i+amostras_min])
                            for i in range(0, len(sinal)-amostras_min)])

        regioes_mau_contato = np.where(var_local < self.PARAMS['mau_contato']['limiar_var'])[0]
        return regioes_mau_contato.tolist()

    def detectar_tremor_muscular(self, sinal, fs):
        freq, psd = welch(sinal, fs=fs, nperseg=int(fs))
        mask = (freq >= self.PARAMS['tremor_muscular']['freq_min']) & \
               (freq <= self.PARAMS['tremor_muscular']['freq_max'])
        
        potencia_tremor = np.mean(psd[mask])
        potencia_total = np.mean(psd)
        return {
            'score': float(potencia_tremor / potencia_total) if potencia_total > 0 else 0.0,
            'frequencias': [self.PARAMS['tremor_muscular']['freq_min'], 
                               self.PARAMS['tremor_muscular']['freq_max']],
            'limiar': self.PARAMS['tremor_muscular']['limiar']
        }

    def detectar_desconexao(self, sinal, fs):
        amostras_min = int(self.PARAMS['desconexao']['duracao_min'] * fs)
        amplitude = np.abs(sinal)
        regioes = np.where(amplitude < self.PARAMS['desconexao']['limiar_amp'])[0]

        grupos = []
        if len(regioes) > 0:
            gaps = np.diff(regioes)
            breaks = np.where(gaps > 1)[0] + 1
            segmentos = np.split(regioes, breaks)

            for seg in segmentos:
                if len(seg) >= amostras_min:
                    grupos.append({
                        'inicio': int(seg[0]),
                        'fim': int(seg[-1]),
                        'duracao': len(seg)/fs
                    })
        return grupos

    def analisar_interferencias(self, nome_registro, duracao=10, canal=0):
        try:
            sinal, fs = self.carregar_sinal(nome_registro, canal)
            janela_sinal = sinal[:int(duracao * fs)]
            # Variancia local
            var_local = np.array([np.var(janela_sinal[i:i+100]) for i in range(0, len(janela_sinal)-100)])
            tempo_var = np.arange(len(var_local)) / fs
            
             # Cálculo do histograma
            histograma, bins = np.histogram(janela_sinal, bins=100, density=True)
            amplitudes = (bins[:-1] + bins[1:]) / 2  # Valores médios dos bins para o eixo X
            densidade = histograma.tolist()  # Valores do histograma (densidade) para o eixo Y

            # Executa todas as análises
            interferencia_rede, freq, psd = self.detectar_interferencia_rede(janela_sinal, fs)
            
            dados_cliente = {
                'sinal': janela_sinal.tolist(),
                'frequencias': freq,
                'psd': psd,
                'interferencia_rede': interferencia_rede,
                'mau_contato': self.detectar_mau_contato(janela_sinal, fs),
                'tremor_muscular': self.detectar_tremor_muscular(janela_sinal, fs),
                'desconexao': self.detectar_desconexao(janela_sinal, fs),
                'parametros': self.PARAMS,
                'varianciaLocal': {
                  'variancia': var_local.tolist(),
                  'tempo': tempo_var.tolist()
                },
                'histograma': {
                  'amplitudes': amplitudes.tolist(),  # Eixo X
                  'densidade': densidade  # Eixo Y
                }
            }

            return dados_cliente

        except Exception as e:
            print(f"Erro ao analisar sinal: {str(e)}")
            return None