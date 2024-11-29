# Use uma imagem base do Python
FROM python:3.10-slim

# Instalar dependências do sistema necessárias (como build-essential)
RUN apt-get update && apt-get install -y build-essential gcc gfortran

# Defina o diretório de trabalho dentro do container
WORKDIR /app

# Copie o arquivo requirements.txt para o container
COPY requirements.txt .

# Instalar dependências
RUN pip install --upgrade pip && pip install --prefer-binary -r requirements.txt

# Copiar todo o código da aplicação para o container
COPY . .

# Defina o comando para rodar a aplicação (substitua "app:app" pelo nome correto)
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
