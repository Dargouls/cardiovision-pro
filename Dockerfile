# Usar imagem Debian completa para compatibilidade com libatlas
FROM python:3.10-bullseye

# Evitar prompts durante instalação
ENV DEBIAN_FRONTEND=noninteractive

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    build-essential \
    libatlas-base-dev \
    python3-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Diretório de trabalho
WORKDIR /app

# Copiar requirements e instalar dependências Python
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

# Copiar toda a aplicação
COPY . .

# Comando para rodar a aplicação
CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000"]