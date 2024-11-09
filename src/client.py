import requests

# Dados de entrada
data = {
    "record_path": "/content/pasta/418",  # Substitua pelo caminho real do arquivo ECG
    "num_parts": 2,
    "samples_per_part": 5000
}

# Endereço local do FastAPI no Colab
url = "http://0.0.0.0:8001/analyze_ecg"

# Enviar a requisição POST
response = requests.post(url, json=data)

# Exibir a resposta
print(response.json())
