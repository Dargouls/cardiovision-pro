# API de Análise de ECG com FastAPI

Esta API foi desenvolvida para realizar a análise de registros de ECG (Eletrocardiograma) utilizando a biblioteca `wfdb` para leitura dos arquivos e FastAPI para expor a API. O sistema permite dividir o ECG em partes e realizar análises personalizadas.

## Funcionalidades

- **Análise de ECG**: Recebe um caminho para o arquivo de ECG e retorna métricas e segmentos do ECG após análise.
- **Configuração Personalizável**: Você pode definir o número de partes e a quantidade de amostras por parte.

## Estrutura do Projeto

1. **FastAPI**: Framework usado para criar a API.
2. **wfdb**: Biblioteca utilizada para ler registros de ECG.
3. **Uvicorn**: Servidor ASGI para rodar o FastAPI.
4. **requests**: Para fazer requisições HTTP e testar a API localmente.

## Como Rodar o Projeto

### 1. Instalar Dependências

Primeiro, instale as dependências necessárias. Você pode fazer isso criando um ambiente virtual e instalando as dependências com o `pip`:

```bash
pip install fastapi uvicorn wfdb requests
```

### 2. Rodar o Servidor

Execute o arquivo Python que contém a definição da API para iniciar o servidor FastAPI.

```bash
python app.py
```

Isso irá rodar o servidor na porta `8001`. O servidor estará disponível em `http://0.0.0.0:8001/`.

### 3. Testar a API

Você pode testar a API localmente utilizando o código do cliente abaixo, que envia uma requisição POST para a API com dados de entrada:

```python
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
```

Este código enviará uma requisição para o endpoint `/analyze_ecg` com os dados especificados e imprimirá a resposta recebida.

## Estrutura do Código

- **`app.py`**: Arquivo principal que contém a definição da API e o servidor FastAPI. 
  - A API tem um endpoint POST `/analyze_ecg` que processa os dados do ECG e retorna os resultados.
  - O servidor roda em um thread separado, permitindo que a API seja acessada sem bloquear a execução do código.

### Exemplo de Request

#### POST `/analyze_ecg`

**Dados de entrada (JSON)**:
```json
{
  "record_path": "/content/pasta/418",
  "num_parts": 2,
  "samples_per_part": 5000
}
```

**Resposta (JSON)**:
```json
{
  "message": "Análise completa. Arquivos salvos.",
  "output_files": ["ecg_metrics.json", "ecg_segments.json"]
}
```

## Licença

Este projeto está licenciado sob a [MIT License](LICENSE).
