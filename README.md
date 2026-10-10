# ArboMol Classificator — Classificação Molecular

Uma aplicação web full-stack para classificação de moléculas usando SMILES, indicando potencial atividade contra Dengue, Zika ou Chikungunya.

## ✅ Pré-requisitos (instalar antes de tudo)

Esse projeto tem duas partes que rodam separadas: o **backend** (Python) e o
**frontend** (Node.js/React). Você precisa ter os dois instalados na máquina
**antes** de seguir qualquer guia abaixo.

| O que instalar | Versão necessária | Link de download | Como confirmar que instalou |
|---|---|---|---|
| **Python** | 3.10 ou superior | [python.org/downloads](https://www.python.org/downloads/) | `python --version` |
| **Node.js** (já vem com `npm`) | 18 ou superior (LTS recomendado) | [nodejs.org](https://nodejs.org/) | `node --version` e `npm --version` |

Notas para quem nunca instalou nada disso:

- **Windows:** ao instalar o Python, marque a caixinha **"Add python.exe to PATH"**
  na primeira tela do instalador — se não marcar, o comando `python` não vai
  funcionar no terminal depois. No Node.js, pode usar as opções padrão do
  instalador.
- Depois de instalar os dois, **feche e abra o terminal de novo** antes de
  testar os comandos de verificação (`python --version`, `node --version`),
  senão o PATH pode não ter sido recarregado ainda.
- Você também precisa do **código deste projeto na sua máquina** — se já tem a
  pasta baixada/extraída (como parece ser o seu caso), pode ignorar este
  ponto. Caso contrário, baixe o `.zip` do repositório e extraia, ou clone com
  `git clone` se tiver o [Git](https://git-scm.com/downloads) instalado.
- Instalar o Python/Node.js é feito **uma única vez** na máquina. Os passos de
  `venv`/`pip install`/`npm install` abaixo também só precisam ser refeitos se
  você apagar as pastas `venv` ou `node_modules`, ou se as dependências do
  projeto mudarem.

## ⚡ Guia rápido (primeira vez / depois de clonar)

### macOS / Linux

Passo a passo completo, do zero, rodando local (sem Docker):

```bash
# 1. Prepare o ambiente do backend (só precisa fazer isso uma vez)
cd backend
python3 -m venv venv          # confirme que esse python3 é 3.10 ou superior
source venv/bin/activate
pip install -r requirements.txt
cd ..

# 2. Suba tudo (backend + frontend) a partir da PASTA RAIZ do projeto
bash start.sh
```

O `start.sh` só funciona rodado da pasta raiz (onde estão os arquivos `.pkl`) —
ele reaproveita o `venv` criado no passo 1, reinstala as dependências (rápido,
pois já estão lá), sobe o backend em `http://localhost:8000` e o frontend em
`http://localhost:3000`. Pressione `Ctrl+C` no terminal para encerrar os dois.

Se aparecer o erro **"address already in use"** na porta 8000, é sinal de que
já existe um backend rodando de uma execução anterior que não foi encerrada
direito. Mate esse processo antigo e tente de novo:

```bash
lsof -ti:8000 | xargs kill -9
```

### Windows (PowerShell ou cmd — sem Git Bash/WSL)

`start.sh` é um script **bash** e não roda nativamente no `cmd.exe` nem no
PowerShell — por isso é preciso subir backend e frontend **manualmente, em
duas janelas de terminal separadas** (deixe as duas abertas e rodando ao mesmo
tempo). Siga a ordem abaixo do zero:

0. Instale o **Python 3.10+** e o **Node.js** — veja a seção
   [Pré-requisitos](#-pré-requisitos-instalar-antes-de-tudo) acima. Confirme
   com `python --version` e `node --version` antes de continuar.
1. Extraia/baixe a pasta do projeto (ex.: `arbomol-main`) e abra um terminal
   (PowerShell) **dentro dela** — é a pasta onde estão os arquivos `README.md`,
   `backend/`, `frontend/` e os `.pkl`.

**Janela 1 — Backend** (a partir da pasta raiz do projeto):

```powershell
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main_working.py
```

Deixe essa janela aberta. O backend fica em `http://localhost:8000`
(documentação interativa em `http://localhost:8000/docs`). Se aparecer
`(venv)` no início do prompt, o ambiente virtual está ativo corretamente.

> **Importante:** não use `uvicorn main:app` nem `python -m uvicorn main:app`
> — o arquivo da API se chama `main_working.py`, e ele já sobe o próprio
> servidor internamente. O comando certo é sempre `python main_working.py`.

**Janela 2 — Frontend** (abra um novo terminal/PowerShell, a partir da pasta raiz do projeto):

```powershell
cd frontend
npm install
npm start
```

Isso abre automaticamente `http://localhost:3000` no navegador padrão (se não
abrir sozinho, abra manualmente esse endereço). É nessa página que você usa o
app — cole um SMILES ou envie um arquivo CSV/Excel.

Para encerrar tudo, aperte `Ctrl+C` em cada uma das duas janelas.

Se aparecer o erro **"address already in use"** / **porta 8000 ocupada**, tem
um backend antigo ainda rodando. Descubra e mate o processo:

```powershell
netstat -ano | findstr :8000
taskkill /PID <numero_do_PID_mostrado_acima> /F
```

> Se preferir rodar `start.sh` mesmo assim, instale o [Git for Windows](https://git-scm.com/download/win)
> (vem com o Git Bash) e execute o comando dentro do **Git Bash**, não no `cmd`/PowerShell.

## 🔁 Retreinar o modelo

Os arquivos `.pkl` já vêm prontos no repositório; esta seção só é necessária
para reproduzir o treino ou treinar com dados novos.

```bash
cd backend && source venv/bin/activate && cd ..   # usa o mesmo ambiente do backend
python train_model.py
```

O script lê as planilhas de `data/`, refaz toda a curadoria (validação dos
SMILES, deduplicação dentro e entre classes, cálculo dos 217 descritores
RDKit), avalia por validação cruzada estratificada e regrava
`modelo_final.pkl`, `label_encoder.pkl` e `colunas.pkl`.

Todas as etapas aleatórias usam `random_state = 42`, então duas execuções
produzem um modelo **byte a byte idêntico**. Desempenho esperado (validação
cruzada estratificada de 5 partições, 5 repetições, n = 912):

| Métrica | Valor |
|---|---|
| Acurácia | 0,728 ± 0,027 |
| Macro-F1 | 0,718 ± 0,026 |
| Linha de base (classe majoritária) | 0,533 |

## 🏗️ Arquitetura

- **Backend**: FastAPI (Python)
- **Frontend**: React
- **Comunicação**: API REST
- **Validação**: Massa molecular entre 200-700 Da
- **Modelos**: Machine Learning com descritores RDKit

## 📁 Estrutura do Projeto

```
Plataforma_Tropical/
├── backend/
│   ├── main_working.py     # API FastAPI
│   ├── Dockerfile          # Build da API (contexto = raiz do projeto)
│   └── requirements.txt    # Dependências Python
├── frontend/
│   ├── src/
│   │   ├── App.js          # Componente principal React
│   │   ├── App.css         # Estilos
│   │   └── index.js        # Ponto de entrada
│   ├── public/
│   │   └── index.html      # Template HTML
│   ├── package.json        # Dependências Node.js
│   └── Dockerfile
├── predictor_simple.py     # Cálculo de descritores + predição (modelos cacheados em memória)
├── modelo_final.pkl        # Modelo treinado
├── label_encoder.pkl       # Encoder de classes
├── colunas.pkl             # Colunas dos descritores
├── data/                   # Planilhas de SMILES usadas no treino (ver data/README.md)
├── train_model.py          # Treino reprodutível do modelo (gera os .pkl acima)
├── requirements.txt        # Atalho para backend/requirements.txt
├── docker-compose.yml
└── README.md                # Este arquivo
```

## 🚀 Como Executar

### Opção rápida (local, sem Docker)

Da pasta raiz do projeto:

```bash
bash start.sh
```

Isso cria o ambiente virtual do backend, instala as dependências de backend e frontend, e sobe os dois servidores.

> **Windows:** `start.sh` é um script bash e não funciona no `cmd`/PowerShell
> nativo (só dentro do Git Bash). Siga a seção **Windows** do guia rápido
> acima, que sobe backend e frontend manualmente em duas janelas.

### Manualmente

#### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate
pip install -r requirements.txt
python main_working.py
```

O backend estará rodando em `http://localhost:8000` (documentação interativa em `/docs`).

#### Frontend

```bash
cd frontend
npm install
npm start
```

O frontend estará rodando em `http://localhost:3000`.

### Com Docker

Da pasta raiz do projeto (o `docker-compose.yml` já usa a raiz como contexto de build, para que o backend tenha acesso aos arquivos `.pkl` e a `predictor_simple.py`):

```bash
docker compose up --build
```

### Variáveis de ambiente

| Variável | Onde | Descrição | Padrão |
|---|---|---|---|
| `CORS_ORIGINS` | backend | Origens do frontend autorizadas a chamar a API (separadas por vírgula) | `http://localhost:3000,http://127.0.0.1:3000` |
| `REACT_APP_API_URL` | frontend | URL base da API usada pelo frontend | `http://localhost:8000` |

Em um deploy real (backend e frontend em domínios/portas diferentes de `localhost`), essas duas variáveis **precisam** ser configuradas, senão o frontend não conseguirá falar com o backend.

## 📋 Funcionalidades

### Classificação Individual
- Insira um SMILES no campo de texto
- Sistema valida a massa molecular (200-700 Da)
- Retorna a classificação: Dengue, Zika ou Chikungunya
- Mostra informações adicionais como massa molecular

### Classificação em Lote
- Upload de arquivos CSV ou Excel
- Coluna obrigatória: "Smiles"
- Processamento de múltiplas moléculas em uma única passada (modelo carregado uma vez, não recarregado por molécula)
- Download dos resultados com predições
- Relatório de erros para SMILES inválidos

### Validação
- Verificação de SMILES válido via RDKit
- Validação de massa molecular (200-700 Da)
- Tratamento de erros com feedback claro

## 🔬 Endpoints da API

### POST /predict
Classifica uma única molécula.

**Request:**
```json
{
  "smiles": "CC(C)C(=O)OC[C@@H]1[C@H]([C@H]([C@@H](O1)n2ccc(nc2=O)NO)O)O"
}
```

**Response:**
```json
{
  "classe": "Dengue",
  "massa": 300.31,
  "smiles": "CC(C)C(=O)OC[C@@H]1[C@H]([C@H]([C@@H](O1)n2ccc(nc2=O)NO)O)O",
  "modelo": "real",
  "probabilidades": {
    "Chikungunya": 0.07,
    "Dengue": 0.78,
    "Zika": 0.15
  },
  "explicacao": [
    { "descritor": "TPSA", "valor": 63.6, "contribuicao": 0.42, "direcao": "aumenta" },
    { "descritor": "MolLogP", "valor": 1.31, "contribuicao": -0.28, "direcao": "diminui" }
  ]
}
```

`probabilidades` traz a probabilidade de cada classe (via `predict_proba`) e
`explicacao` traz os descritores moleculares (RDKit) que mais pesaram na
decisão do modelo, calculados com [SHAP](https://shap.readthedocs.io/)
(`TreeExplainer`). Ambas as chaves são "melhor esforço": se o cálculo falhar
por qualquer motivo, a predição principal (`classe`/`massa`/`smiles`) ainda é
retornada normalmente, só sem essas duas chaves extras.

### POST /predict_batch
Processa múltiplas moléculas de um arquivo.

**Request:** FormData com arquivo CSV/Excel

**Response:**
```json
{
  "message": "Processado 45 de 50 moléculas",
  "validas": 45,
  "invalidas": 5,
  "erros": ["Linha 10: Massa molecular fora do intervalo"],
  "download_url": "/download_resultados/resultado_<id>.xlsx"
}
```

O arquivo Excel de resultados (`download_url`) inclui, além de `Predicao` e
`Massa`, as colunas `Prob_Chikungunya`, `Prob_Dengue` e `Prob_Zika` com a
probabilidade de cada classe para cada molécula.

### GET /download_resultados/{filename}
Baixa o arquivo Excel com os resultados de uma execução específica (o nome do
arquivo é único por execução, retornado em `download_url`).

## 🎨 Design

- Interface clara e moderna (fundo off-white, cards com sombra suave, gradiente indigo/violeta/teal)
- Responsivo para desktop e mobile
- Feedback visual claro (loading, sucesso, erro)
- Cores diferenciadas para cada classe:
  - Dengue: Vermelho/rosa
  - Zika: Amarelo
  - Chikungunya: Roxo

## 🔧 Tecnologias

### Backend
- FastAPI: Framework web moderno
- RDKit: Química computacional
- Pandas: Manipulação de dados
- Scikit-learn: Machine Learning
- Joblib: Serialização de modelos

### Frontend
- React: Biblioteca UI
- Axios: Requisições HTTP
- Lucide React: Ícones

## 📝 Exemplos de Uso

### SMILES para Teste
```
CC(C)C(=O)OC[C@@H]1[C@H]([C@H]([C@@H](O1)n2ccc(nc2=O)NO)O)O  # Molécula complexa (dentro da faixa de massa)
CCO  # Etanol - massa: 46.07 Da (fora da faixa, deve retornar erro de validação)
```

### Formato do Arquivo CSV
```csv
Smiles
CC(C)C(=O)OC[C@@H]1[C@H]([C@H]([C@@H](O1)n2ccc(nc2=O)NO)O)O
CC[C@H](C)C(=O)O[C@H]1C[C@H](C=C2[C@H]1[C@H]([C@H](C=C2)C)CC[C@@H]3C[C@H](CC(=O)O3)O)C
```

## 🚨 Considerações Importantes

1. **Validação de Massa**: Todas as moléculas devem ter massa entre 200-700 Da
2. **Formato SMILES**: Use notação SMILES padrão
3. **Arquivos**: Coluna obrigatória "Smiles" (case-sensitive)
4. **Performance**: os modelos ficam em cache em memória após a primeira predição; para arquivos muito grandes, o cálculo de descritores RDKit ainda é o principal custo de tempo

## 🐛 Troubleshooting

### Backend não inicia
- Verifique se os arquivos `.pkl` estão na pasta raiz do projeto
- Confirme se o RDKit foi instalado corretamente (`pip install -r backend/requirements.txt`)
- É necessário **Python 3.10 ou superior** para instalar as dependências do backend

### Erro "No module named 'numpy._core'"
Esse erro acontece quando o `modelo_final.pkl` (salvo com numpy >= 2.0 / scikit-learn
1.7.2) é carregado por um ambiente com numpy mais antigo. O `backend/requirements.txt`
já fixa as versões corretas — se o erro aparecer, o `venv` provavelmente foi criado
antes dessa correção (ou com um Python < 3.10). Resolva apagando o ambiente virtual
antigo e recriando:

```bash
# macOS/Linux
cd backend
rm -rf venv
python3 -m venv venv   # certifique-se de que este python3 é >= 3.10
source venv/bin/activate
pip install -r requirements.txt
```

```powershell
# Windows
cd backend
rmdir /s /q venv
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### Frontend não conecta ao backend / "Erro ao conectar com o servidor"
- Confirme se o backend realmente está no ar: abra `http://localhost:8000` direto no navegador — deve aparecer um JSON. Se não abrir, o backend não subiu.
- Rode o backend manualmente, numa janela à parte (sem `start.sh`, que roda em background e pode esconder o erro), para ver a mensagem de erro real:
  - macOS/Linux: `cd backend && source venv/bin/activate && python main_working.py`
  - Windows: `cd backend`, depois `venv\Scripts\activate`, depois `python main_working.py`
- Se a porta 8000 já estiver em uso por um processo antigo, mate-o e suba o backend de novo:
  - macOS/Linux: `lsof -ti:8000 | xargs kill -9`
  - Windows: `netstat -ano | findstr :8000` (anota o PID na última coluna) e depois `taskkill /PID <PID> /F`
- Se estiver rodando fora de `localhost`, confirme se `REACT_APP_API_URL` (frontend) e `CORS_ORIGINS` (backend) estão configuradas corretamente

### Erros de predição
- Valide o formato SMILES
- Verifique a massa molecular da molécula (faixa aceita: 200-700 Da)
- Confirme se o arquivo está no formato correto

### Resultado não mostra probabilidades / explicação ("Por que essa classificação?")
Essas duas seções dependem da biblioteca `shap`, adicionada ao
`backend/requirements.txt`. Se você criou o `venv` antes dessa atualização,
instale a dependência nova no ambiente já existente (não precisa recriar o
venv):

```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
```

Depois, reinicie o backend. O frontend não precisa de nada extra — só
recarregar a página no navegador.

## 📄 Licença

Este projeto é para fins educacionais e de pesquisa.
