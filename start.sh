#!/bin/bash

# Script para iniciar a aplicação completa

echo "🚀 Iniciando Plataforma de Classificação Molecular"
echo "=================================================="

# Verificar se estamos na pasta correta
if [ ! -f "modelo_final.pkl" ]; then
    echo "❌ Erro: Execute este script da pasta raiz do projeto"
    echo "   (onde estão os arquivos .pkl)"
    exit 1
fi

# Iniciar backend
echo "🔧 Iniciando backend..."
cd backend

# O modelo (.pkl) foi salvo com numpy>=2.0 / scikit-learn 1.7.2, que exigem
# Python 3.10+. Um venv criado com Python mais antigo não consegue instalar
# essas versões e o backend falha ao carregar o modelo com o erro
# "No module named 'numpy._core'".
PY_OK=$(python3 -c 'import sys; print(1 if sys.version_info >= (3, 10) else 0)' 2>/dev/null)
if [ "$PY_OK" != "1" ]; then
    echo "❌ Erro: é necessário Python 3.10 ou superior (encontrado: $(python3 --version 2>&1))."
    echo "   Instale uma versão mais nova (ex: via Homebrew 'brew install python@3.11'"
    echo "   ou usando o Python do Anaconda, se ele for >= 3.10) e rode este script"
    echo "   novamente, por exemplo: PYTHON_BIN=/opt/anaconda3/bin/python3 bash start.sh"
    exit 1
fi
PYTHON_BIN=${PYTHON_BIN:-python3}

# Verificar se existe ambiente virtual
if [ ! -d "venv" ]; then
    echo "📦 Criando ambiente virtual..."
    "$PYTHON_BIN" -m venv venv
fi

# Ativar ambiente virtual
source venv/bin/activate

# Instalar/atualizar dependências (pip atualiza pacotes já instalados com
# versão diferente da fixada em requirements.txt, então basta rodar de novo
# se o venv já existir de uma instalação anterior)
echo " Instalando dependências do backend..."
pip install -r requirements.txt

# Iniciar servidor backend em background
echo "Iniciando servidor backend..."
python main_working.py &
BACKEND_PID=$!

# Esperar um pouco para o backend iniciar
sleep 5

# Voltar para pasta raiz
cd ..

# Iniciar frontend
echo "🎨 Iniciando frontend..."
cd frontend

# Instalar dependências do frontend
echo "📦 Instalando dependências do frontend..."
npm install

# Iniciar servidor frontend
echo "🚀 Iniciando servidor frontend..."
npm start &
FRONTEND_PID=$!

echo ""
echo "✅ Aplicação iniciada com sucesso!"
echo "=================================================="
echo "📍 Backend: http://localhost:8000"
echo "📍 Frontend: http://localhost:3000"
echo "📍 API Docs: http://localhost:8000/docs"
echo ""
echo "📝 Para testar o backend: python test_backend.py"
echo ""
echo "⚠️  Pressione Ctrl+C para parar os servidores"

# Função para limpar processos ao sair
cleanup() {
    echo ""
    echo "🛑 Parando servidores..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    echo "✅ Servidores parados"
    exit 0
}

# Capturar sinal de interrupção
trap cleanup SIGINT

# Manter script rodando
wait
