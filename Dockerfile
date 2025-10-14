FROM python:3.10-slim

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    build-essential \
    libopenblas-dev \
    python3-dev \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Instalar o uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:${PATH}"

WORKDIR /app

# Copiar apenas o que é necessário para instalar dependências
COPY pyproject.toml uv.lock* ./

# Instalar dependências do projeto (usando uv)
RUN uv sync --no-dev

# Copiar o resto do código
COPY . .

# Executar o app
CMD ["uv", "run", "uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000"]
