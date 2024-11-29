# Use uma imagem base do Python
FROM python:3.10-slim

# Instalar dependências de compilação necessárias para pandas
RUN apt-get update && \
    apt-get install -y build-essential gcc gfortran \
    libatlas-base-dev liblapack-dev libblas-dev

WORKDIR /app

# Copiar o arquivo requirements.txt para o container
COPY requirements.txt .

COPY pandas-1.5.3-cp310-cp310-win_amd64.whl /app/

RUN pip install /app/pandas-1.5.3-cp310-cp310-win_amd64.whl

# Instalar as demais dependências do requirements.txt
RUN pip install --prefer-binary -r requirements.txt

# Copiar o restante do código da aplicação para dentro do container
COPY . .

# Comando para rodar a aplicação
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
