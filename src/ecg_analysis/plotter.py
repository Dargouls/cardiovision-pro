# plotter.py
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
from .config import ECGConfig

class ECGPlotter:
    """
    Classe para plotagem de ECG em formato clínico.
    """
    def __init__(self):
        self.config = ECGConfig()
    
    def setup_grid(self, ax):
        """
        Configura a grade do ECG.
        """
        ax.set_facecolor(self.config.BACKGROUND_COLOR)
        ax.grid(True, which='major', color=self.config.GRID_COLOR_MAJOR, linewidth=0.8)
        ax.grid(True, which='minor', color=self.config.GRID_COLOR_MINOR, linewidth=0.3)
        
        # Configurar divisões da grade
        major_ticks_x = np.arange(0, 10, 0.2)  # Divisões a cada 0.2s
        minor_ticks_x = np.arange(0, 10, 0.04)  # Divisões a cada 0.04s
        major_ticks_y = np.arange(-2, 2, 0.5)  # Divisões a cada 0.5mV
        minor_ticks_y = np.arange(-2, 2, 0.1)  # Divisões a cada 0.1mV
        
        ax.set_xticks(major_ticks_x)
        ax.set_xticks(minor_ticks_x, minor=True)
        ax.set_yticks(major_ticks_y)
        ax.set_yticks(minor_ticks_y, minor=True)
        
        # Remover rótulos
        ax.set_xticklabels([])
        ax.set_yticklabels([])
    
    def add_calibration_marker(self, ax):
        """
        Adiciona marcador de calibração.
        """
        # Posicionar o marcador de calibração no canto inferior esquerdo
        cal_x = 0
        cal_y = -1.5
        
        # Desenhar marcador
        ax.plot([cal_x, cal_x], [cal_y, cal_y + 1], 'k-', linewidth=1.5)
        ax.plot([cal_x, cal_x + 0.2], [cal_y, cal_y], 'k-', linewidth=1.5)
        
        # Adicionar texto
        ax.text(cal_x - 0.05, cal_y + 0.5, '1mV',
               horizontalalignment='right',
               verticalalignment='center',
               fontsize=8)
        ax.text(cal_x + 0.1, cal_y - 0.1, '200ms',
               horizontalalignment='center',
               verticalalignment='top',
               fontsize=8)
    
    def plot_segment(self, signals_data, segment_info, show_peaks=True):
        """
        Plota um segmento do ECG.
        """
        # Criar figura com proporções otimizadas
        fig = plt.figure(figsize=(15, 5))  # Ajustado para melhor proporção
        
        # Criar subplot com margens mínimas
        ax = plt.subplot(111)
        plt.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.05)
        
        # Configurar grade
        self.setup_grid(ax)
        
        # Plotar cada derivação
        for idx, (lead_name, data) in enumerate(signals_data.items()):
            # Converter dados para numpy arrays
            signal = np.array(data['signal'])
            time_points = np.array(data['time_points'])
            
            # Plotar sinal principal
            plt.plot(time_points/self.config.SAMPLE_RATE, signal, 'k-', linewidth=0.8)
            
            # Adicionar rótulo da derivação
            plt.text(-0.1, 0, lead_name,
                    horizontalalignment='right',
                    verticalalignment='center',
                    fontsize=8)
            
            # Plotar picos R se solicitado
            if show_peaks and 'r_peaks' in data:
                r_peaks = np.array(data['r_peaks'])
                plt.plot(time_points[r_peaks]/self.config.SAMPLE_RATE,
                        signal[r_peaks],
                        'rx', markersize=4)
        
        # Adicionar marcador de calibração
        self.add_calibration_marker(ax)
        
        # Adicionar informações do segmento
        self._add_segment_info(fig, segment_info)
        
        # Ajustar limites do gráfico
        max_time = len(time_points)/self.config.SAMPLE_RATE
        plt.xlim(-0.2, max_time + 0.2)
        plt.ylim(-2, 2)
        
        # Mostrar gráfico
        plt.show()
        return fig
    
    def _add_segment_info(self, fig, info):
        """
        Adiciona informações do segmento ao gráfico.
        """
        info_text = [
            f"Segmento: {info['segment_number']}/{info['total_segments']}",
            f"Tempo: {info['start_time']:.1f}s - {info['end_time']:.1f}s",
            f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        ]
        
        fig.text(0.02, 0.98, '\n'.join(info_text),
                fontsize=8, va='top', fontfamily='monospace')
