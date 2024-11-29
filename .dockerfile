# img python
FROM python:3.10.11-slim as builder

# Dir de trabalho
WORKDIR /app

# cp re.txt para cont.
COPY requirements.txt /app/

# Install dep.
RUN pip install --no-cache-dir -r requirements.txt

# cp app para cont
COPY . /app/

# exp porta
EXPOSE 5432

# init app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5432"]
