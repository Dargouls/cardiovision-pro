# config.py
class ECGConfig:
    """
    Configurações globais para análise de ECG.
    """
    SAMPLE_RATE = 250  # Taxa de amostragem padrão
    FILTER_LOW_PASS = 40  # Frequência de corte do filtro passa-baixa
    FILTER_HIGH_PASS = 0.5  # Frequência de corte do filtro passa-alta
    QRS_MIN_DISTANCE = 0.2  # Distância mínima entre picos R (em segundos)
    GRID_COLOR_MAJOR = '#FF9999'  # Cor da grade principal
    GRID_COLOR_MINOR = '#FFB2B2'  # Cor da grade secundária
    BACKGROUND_COLOR = '#FFE4E1'  # Cor de fundo do papel ECG
