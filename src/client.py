# import requests

# # Dados adicionais de entrada (parâmetros de análise)
# data = {
#     "num_parts": 2,  # Número de partes para dividir o arquivo
#     "samples_per_part": 5000  # Número de amostras por parte
# }

# # Caminho da pasta onde os arquivos estão localizados
# record_path = "/content/pasta/418"

# # Coletando os arquivos da pasta
# files = {
#     "files": [
#         ("file", (f"file_{i}.dat", open(f"{record_path}/file_{i}.dat", "rb")))  # Cada arquivo é enviado aqui
#         for i in range(1, 4)  # Exemplo: 3 arquivos, ajuste conforme necessário
#     ]
# }

# # Endereço da API FastAPI
# url = "http://0.0.0.0:8001/analyze_ecg"

# # Enviando a requisição POST com os arquivos e parâmetros
# response = requests.post(url, files=files, data=data)

# # Exibindo a resposta da API
# print(response.json())
