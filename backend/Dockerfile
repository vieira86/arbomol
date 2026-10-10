# Este Dockerfile é construído com o contexto na RAIZ do projeto
# (veja docker-compose.yml: build.context = ".", dockerfile = "backend/Dockerfile"),
# porque main_working.py depende de arquivos que vivem na raiz do projeto
# (predictor_simple.py e os modelos .pkl), não apenas dentro de backend/.
#
# Python 3.10+ é necessário porque modelo_final.pkl foi salvo com
# numpy>=2.0 / scikit-learn 1.7.2 (ambos exigem Python >= 3.10).
FROM python:3.10-slim

WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    libffi-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar dependências Python
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o módulo de predição e os modelos treinados (raiz do projeto)
COPY predictor_simple.py .
COPY modelo_final.pkl label_encoder.pkl colunas.pkl ./

# Copiar código da API
COPY backend/main_working.py .

# Expor porta
EXPOSE 8000

# Comando para iniciar a aplicação
CMD ["uvicorn", "main_working:app", "--host", "0.0.0.0", "--port", "8000"]
