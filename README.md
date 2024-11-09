# Cardiovision Pro

O **Cardiovision Pro** é um projeto que utiliza a FastAPI e Python para análise e processamento de sinais de ECG. Ele permite a análise de sinais de ECG, cálculo de métricas e visualização, além de fornecer uma API para realizar essa análise de forma simples e eficiente.

## Estrutura do Projeto

A estrutura do projeto é a seguinte:

```
/cardiovision-pro
│
├── /data                    # Dados de entrada
│   └── 418.xws              # Exemplo de arquivo de ECG
│
├── /src                     # Código-fonte da aplicação
│   ├── app.py               # API FastAPI
│   ├── client.py            # Código para enviar requisições à API
│   ├── signal_processor.py  # Processamento de sinais ECG
│   ├── metrics_calculator.py # Cálculo das métricas do ECG
│   ├── plotter.py           # Funções de visualização do ECG
│   └── main.py              # Arquivo principal para iniciar a execução
│
├── README.md                # Documentação do projeto
├── requirements.txt         # Dependências do projeto
└── .gitignore               # Arquivo para ignorar arquivos desnecessários
```

## Como Usar

### 1. Clonar o Repositório

Clone o repositório em seu ambiente local:

```bash
git clone https://github.com/dheiver2/cardiovision-pro.git
cd cardiovision-pro
```

### 2. Instalar Dependências

Instale as dependências necessárias listadas no arquivo `requirements.txt`:

```bash
pip install -r requirements.txt
```

### 3. Executar a API

Para iniciar a API FastAPI, execute o seguinte comando:

```bash
uvicorn src.app:app --reload
```

A API estará disponível em `http://127.0.0.1:8000`.

### 4. Enviar Requisições para Análise de ECG

Para enviar uma requisição POST para a API, você pode usar o arquivo `client.py`. Exemplo de código para enviar uma requisição:

```python
import requests

data = {
    "record_path": "data/418.xws",
    "num_parts": 2,
    "samples_per_part": 5000
}

url = "http://127.0.0.1:8000/analyze_ecg"
response = requests.post(url, json=data)
print(response.json())
```

### 5. Visualizar o ECG

O arquivo `plotter.py` contém funções para plotar o gráfico do sinal ECG. Você pode usá-lo para gerar visualizações a partir do sinal de ECG processado.

### 6. Processamento do Sinal e Cálculo das Métricas

O arquivo `signal_processor.py` contém a lógica de processamento do sinal ECG, enquanto `metrics_calculator.py` realiza o cálculo das métricas associadas ao ECG, como frequência cardíaca e variabilidade.

## Dependências

Este projeto utiliza as seguintes dependências:

- FastAPI
- uvicorn
- requests
- wfdb
- matplotlib
- numpy
- pandas

Você pode instalar todas as dependências utilizando o arquivo `requirements.txt`:

```bash
pip install -r requirements.txt
```

## Arquivos

### `data/418.xws`

Este é um arquivo de exemplo de sinal de ECG utilizado para testes.

### `src/app.py`

Define a API FastAPI que recebe requisições para analisar os sinais de ECG.

### `src/client.py`

Código para enviar requisições à API FastAPI.

### `src/signal_processor.py`

Contém as funções responsáveis pelo processamento do sinal ECG.

### `src/metrics_calculator.py`

Cálcula as métricas associadas ao ECG, como a frequência cardíaca.

### `src/plotter.py`

Funções para gerar visualizações do sinal ECG e das métricas calculadas.

### `src/main.py`

Arquivo principal para iniciar o servidor FastAPI e processar a execução.

## Contribuição

Sinta-se à vontade para contribuir para o projeto, seja corrigindo bugs, adicionando novos recursos ou melhorando a documentação. Para contribuir, siga estas etapas:

1. Faça um fork do repositório.
2. Crie uma nova branch (`git checkout -b nova-feature`).
3. Faça as modificações necessárias e adicione os arquivos modificados (`git add .`).
4. Faça um commit das suas mudanças (`git commit -m 'Nova feature'`).
5. Envie as alterações para o seu fork (`git push origin nova-feature`).
6. Abra um Pull Request no repositório original.

## Licença

Este projeto é licenciado sob a MIT License - consulte o arquivo [LICENSE](LICENSE) para mais detalhes.

---

### Explicações:

- **Nome do Repositório**: O repositório agora está referenciado corretamente como **cardiovision-pro**.
- **Dependências**: As dependências são descritas de forma clara e estão listadas no `requirements.txt`.
- **Execução e API**: O fluxo de execução para rodar a API e enviar requisições está bem descrito.
- **Contribuição**: Informações para contribuir com o projeto estão disponíveis.

Esse `README.md` vai ajudar tanto os desenvolvedores quanto outros usuários a entender como configurar e utilizar o projeto de forma simples e eficiente.
