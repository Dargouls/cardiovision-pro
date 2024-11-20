# Etapa 1: Escolher uma imagem base leve com Python
FROM python:3.10-slim

# Etapa 2: Configurar o diretório de trabalho
WORKDIR /app

# Etapa 3: Instalar dependências do sistema necessárias
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Etapa 4: Copiar os arquivos do projeto
COPY . .

# Etapa 5: Instalar dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Etapa 6: Expor a porta da aplicação
EXPOSE 8000

# Etapa 7: Comando para rodar a aplicação
CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000"]
