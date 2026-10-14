# ArboMol Classificator — Classificação Molecular

Uma aplicação web full-stack que recebe moléculas em notação SMILES e indica se
elas se parecem com compostos em desenvolvimento contra arbovírus e, em caso
positivo, com qual deles — Dengue, Zika ou Chikungunya.

## 🧭 Como a classificação funciona (dois estágios)

A partir da versão 2.0 a resposta vem de **dois modelos encadeados**, e não de
um único classificador de três classes:

| Etapa | Arquivo | O que decide |
|---|---|---|
| 1 — porteiro | `modelo_porteiro.pkl` | A molécula se parece com um composto de programa anti-arbovírus? (treinado contra compostos de influenza, pareados por massa molecular) |
| 2 — especialista | `modelo_especialista.pkl` | Só roda se a etapa 1 aprovar: distribui entre dengue, zika e chikungunya |

O porteiro devolve uma **confiança de 0 a 1**, e os limites de decisão ficam em
`config_modelo.json`:

| Confiança | Veredito | O que aparece na tela |
|---|---|---|
| ≥ 0,50 | `provavel` | "Likely an arbovirus-associated compound" + a classe |
| 0,35 – 0,50 | `possivel` | "Possibly..." (baixa confiança) + a classe |
| < 0,35 | `improvavel` | "Unlikely..." — **nenhuma classe é atribuída** |

Esse é o ponto principal da mudança: antes, qualquer molécula recebia
obrigatoriamente um dos três rótulos, até sacarose. Agora, uma molécula fora do
domínio é barrada na etapa 1 e a plataforma diz que ela não se parece com um
composto anti-arbovírus, em vez de inventar uma classe.

O limite de 0,35 foi escolhido porque preserva 96% dos compostos de arbovírus
conhecidos (contra 81% em 0,50), ao custo de deixar passar alguns compostos de
outras doenças para a etapa 2 — um erro menos grave, já que a resposta vem
marcada como de baixa confiança.

> **O que o rótulo significa.** As classes vêm do campo `Condition` dos
> registros do Cortellis, isto é, "composto que aparece em um programa de
> desenvolvimento indexado para este vírus" — e **não** atividade antiviral
> medida em ensaio. O `improvavel` da etapa 1 significa "não se parece com os
> compostos desses programas", e não "esta molécula é inativa".

O estudo completo — curadoria dos dados, escolha dos negativos, as quatro formas
de validação e a escolha dos limites — está no notebook `treino_arbomol_v2.ipynb`,
que não acompanha o repositório.

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
1. Extraia/baixe a pasta do projeto (ex.: `arbomol-main`) numa pasta local,
   como `C:\ArboMol` (evite pastas de rede ou compartilhadas, como as do
   Parallels/OneDrive), e abra um terminal
   (PowerShell) **dentro dela** — é a pasta onde estão os arquivos `README.md`,
   `backend/`, `frontend/` e os `.pkl`.

**Janela 1 — Backend** (a partir da pasta raiz do projeto):

```powershell
cd backend
python -m venv venv
venv\Scripts\python.exe -m pip install -r requirements.txt
venv\Scripts\python.exe main_working.py
```

Deixe essa janela aberta. O backend fica em `http://localhost:8000`
(documentação interativa em `http://localhost:8000/docs`).

> Usamos `venv\Scripts\python.exe` direto, em vez de `venv\Scripts\activate`,
> porque o PowerShell costuma bloquear o `activate` com o erro *"a execução de
> scripts foi desabilitada neste sistema"*. Assim funciona sem mudar nenhuma
> configuração do Windows.

> **Importante:** não use `uvicorn main:app` nem `python -m uvicorn main:app`
> — o arquivo da API se chama `main_working.py`, e ele já sobe o próprio
> servidor internamente. O comando certo é sempre `python main_working.py`.

**Janela 2 — Frontend** (abra um novo terminal/PowerShell, a partir da pasta raiz do projeto):

```powershell
cd frontend
npm.cmd install
npm.cmd start
```

> No PowerShell, use `npm.cmd` (e não só `npm`): o `npm` comum é bloqueado pelo
> mesmo motivo acima (*"npm.ps1 não pode ser carregado"*). Se preferir liberar
> de vez, rode uma única vez `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`
> e responda **S** — depois disso `npm` funciona normalmente.

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

> Para rodar esta seção você precisa das planilhas em `data/`, que **não**
> acompanham o repositório (ver a observação em "Estrutura do Projeto"). Sem
> elas, a plataforma funciona normalmente com os modelos já treinados.

```bash
cd backend && source venv/bin/activate && cd ..   # usa o mesmo ambiente do backend
python train_model.py
```

O script lê as planilhas de `data/`, refaz toda a curadoria (rótulo a partir do
campo `Condition`, amostragem dos negativos de influenza pareada por massa
molecular em decis, validação dos SMILES, remoção de duplicatas e de SMILES
ambíguos, cálculo dos 217 descritores RDKit), avalia por divisão por scaffold
de Murcko e regrava `modelo_porteiro.pkl`, `modelo_especialista.pkl`,
`label_encoder.pkl`, `colunas.pkl` e `config_modelo.json`.

Todas as etapas aleatórias usam `random_state = 42`, então duas execuções
produzem modelos **byte a byte idênticos** (conferível pelo `sha256` que o
script imprime).

Desempenho esperado (divisão por scaffold em 5 partições — o cenário realista,
em que o modelo só vê esqueletos químicos que não estavam no treino):

| Etapa | Métrica | Valor |
|---|---|---|
| 1 — é arbovírus? | Acurácia | 0,802 |
| 2 — qual dos três? | Acurácia | 0,703 |
| 2 — qual dos três? | Macro-F1 | 0,679 |

A divisão por scaffold dá números mais baixos — e mais honestos — do que a
divisão aleatória, porque moléculas de um mesmo programa de pesquisa
compartilham o esqueleto e, numa divisão aleatória, aparecem dos dois lados.

Conjunto resultante: 1.530 moléculas (751 influenza, 467 dengue, 163
chikungunya, 149 zika). As 124 moléculas com dois arbovírus no `Condition`
ficam fora do treino.

Passos opcionais:

```bash
python train_model.py --skip-eval    # só regrava os artefatos, sem avaliar
python test_modelos.py               # teste de fumaça dos dois estágios
```

## 🏗️ Arquitetura

- **Backend**: FastAPI (Python)
- **Frontend**: React
- **Comunicação**: API REST
- **Validação**: Massa molecular entre 200-700 Da
- **Modelos**: dois `Pipeline` do imbalanced-learn (RandomUnderSampler →
  RobustScaler → SelectKBest → ExtraTreesClassifier) sobre 217 descritores 2D
  do RDKit
- **Explicabilidade**: SHAP (`TreeExplainer`), aplicado ao estágio que tomou a
  decisão final

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
├── predictor_simple.py        # Descritores + os dois estágios (modelos cacheados em memória)
├── modelo_porteiro.pkl        # Etapa 1 — é arbovírus?
├── modelo_especialista.pkl    # Etapa 2 — dengue, zika ou chikungunya
├── label_encoder.pkl          # Classes da etapa 2
├── colunas.pkl                # Ordem dos 217 descritores
├── config_modelo.json         # Limites de decisão do porteiro
├── data/                      # Planilhas do Cortellis (local, fora do repositório)
├── train_model.py             # Treino reprodutível (gera todos os artefatos acima)
├── test_modelos.py            # Teste de fumaça dos dois estágios
├── requirements.txt           # Atalho para backend/requirements.txt
├── docker-compose.yml
└── README.md                  # Este arquivo
```

Duas observações sobre distribuição:

- **Fora do repositório** (`.gitignore`): a pasta `data/` e os notebooks
  (`*.ipynb`). As planilhas são exportações do Cortellis/Clarivate, cuja licença
  não permite redistribuição; os notebooks do estudo ficam só na máquina. Em
  consequência, quem clonar o repositório recebe os modelos já treinados e pode
  rodar a plataforma, mas precisará das próprias planilhas para refazer o treino
  com o `train_model.py`.
- **No repositório, mas fora do `.zip` de download**: `train_model.py` e o
  `index.html` da página de divulgação, marcados como `export-ignore` no
  `.gitattributes`. Quem baixa a plataforma recebe só o que precisa para rodá-la.

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
- Sistema valida o SMILES e a massa molecular (200-700 Da)
- Mostra a **confiança de arbovírus** (barra de 0 a 100%) e o veredito da etapa 1
- Se a molécula for aprovada, mostra a classe (Dengue, Zika ou Chikungunya) e a
  probabilidade de cada uma
- Se for barrada, **não** atribui classe — e a explicação SHAP responde "por que
  foi descartada?"

### Classificação em Lote
- Upload de arquivos CSV ou Excel
- Coluna obrigatória: "Smiles"
- Processamento de múltiplas moléculas em uma única passada (modelos carregados
  uma vez, descritores calculados de uma vez)
- Resumo dos vereditos (quantas prováveis, possíveis e improváveis)
- Download dos resultados em Excel, com as colunas `Arbovirus_Confidence`,
  `Verdict`, `Prediction` (vazia nas moléculas barradas), `Mass` e as três
  `Prob_*`
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

**Response — molécula aprovada pela etapa 1:**
```json
{
  "smiles": "CC(C)C(=O)OC[C@@H]1[C@H]([C@H]([C@@H](O1)n2ccc(nc2=O)NO)O)O",
  "massa": 300.31,
  "confianca_arbovirus": 0.9850,
  "veredito": "provavel",
  "veredito_texto": "Likely an arbovirus-associated compound",
  "modelo": "dois_estagios",
  "classe": "dengue",
  "probabilidades": { "chikungunya": 0.07, "dengue": 0.78, "zika": 0.15 },
  "explicacao": [
    { "descritor": "TPSA", "valor": 63.6, "contribuicao": 0.42, "direcao": "increases" },
    { "descritor": "MolLogP", "valor": 1.31, "contribuicao": -0.28, "direcao": "decreases" }
  ]
}
```

**Response — molécula barrada pela etapa 1** (note a ausência de `classe` e de
`probabilidades`):
```json
{
  "smiles": "OC[C@H]1O[C@@](CO)(O[C@H]2O[C@H](CO)[C@@H](O)[C@H](O)[C@H]2O)[C@@H](O)[C@@H]1O",
  "massa": 342.30,
  "confianca_arbovirus": 0.0900,
  "veredito": "improvavel",
  "veredito_texto": "Unlikely to be an arbovirus-associated compound",
  "modelo": "dois_estagios",
  "explicacao": [ "..." ]
}
```

`confianca_arbovirus`, `veredito` e `veredito_texto` vêm **sempre**; `classe` e
`probabilidades` só aparecem quando o veredito é `provavel` ou `possivel`.

`explicacao` traz os descritores do RDKit que mais pesaram na decisão,
calculados com [SHAP](https://shap.readthedocs.io/) (`TreeExplainer`) — sobre o
porteiro quando a molécula foi barrada, sobre o especialista quando ela passou.
Tanto `probabilidades` quanto `explicacao` são "melhor esforço": se o cálculo
falhar, a predição principal ainda é retornada, só sem essas chaves.

**Em caso de entrada inválida** (SMILES malformado ou massa fora da faixa) a
resposta é `{"erro": "..."}`, com código HTTP 200.

### POST /predict_batch
Processa múltiplas moléculas de um arquivo.

**Request:** FormData com arquivo CSV/Excel

**Response:**
```json
{
  "message": "Processed 45 of 50 molecules",
  "validas": 45,
  "invalidas": 5,
  "erros": ["Row 10: Molecular weight out of range (200-700 Da). Value: 46.07"],
  "download_url": "/download_resultados/resultado_<id>.xlsx",
  "modelo": "dois_estagios",
  "resumo_vereditos": { "provavel": 28, "possivel": 6, "improvavel": 11 },
  "predicoes": ["... as cinco primeiras, para pré-visualização ..."]
}
```

O arquivo Excel de resultados (`download_url`) preserva as colunas originais da
planilha enviada e acrescenta:

| Coluna | Conteúdo |
|---|---|
| `Arbovirus_Confidence` | saída da etapa 1, de 0 a 1 |
| `Verdict` | o texto do veredito (`Invalid` nas linhas recusadas) |
| `Prediction` | dengue, zika ou chikungunya — **vazia** nas moléculas barradas |
| `Mass` | massa molecular |
| `Prob_Chikungunya`, `Prob_Dengue`, `Prob_Zika` | probabilidades da etapa 2 |

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
- Cores por veredito da etapa 1: verde (provável), âmbar (possível, baixa
  confiança) e cinza (improvável), com a barra de confiança no mesmo tom

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
Esse erro acontece quando os arquivos `.pkl` (salvos com numpy >= 2.0 / scikit-learn
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
