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

# Adicionar o binário do uv ao PATH
ENV PATH="/root/.local/bin:${PATH}"

WORKDIR /app

# Copiar apenas os arquivos de dependência
COPY pyproject.toml uv.lock* ./

# Instalar dependências do projeto
RUN uv sync --no-dev

# Copiar o restante do código
COPY . .

ENV PATH="/app/.venv/bin:${PATH}"
CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000"]