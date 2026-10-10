import os
import re
import sys
import uuid

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import io
from rdkit import Chem
from rdkit.Chem import Descriptors

# Permite encontrar predictor_simple.py tanto em desenvolvimento local
# (onde ele fica na raiz do projeto, um nível acima de backend/) quanto
# dentro do container Docker (onde é copiado para o mesmo diretório de
# main_working.py). Tentamos os dois locais.
_here = os.path.dirname(os.path.abspath(__file__))
_parent = os.path.dirname(_here)
for _path in (_here, _parent):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from predictor_simple import (  # noqa: E402
    predict_smiles,
    predict_smiles_batch,
    load_models,
    MASSA_MINIMA,
    MASSA_MAXIMA,
)

app = FastAPI(title="ArboMol Classificator API", version="1.1.0")

# Origens permitidas para CORS. Em produção, defina a variável de ambiente
# CORS_ORIGINS com a(s) URL(s) real(is) do frontend, separadas por vírgula
# (ex: "https://plataforma.rafaelvieira.org"). Por padrão, aceita apenas
# localhost (ambiente de desenvolvimento).
_cors_origins = os.getenv(
    "CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors_origins if o.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Diretório onde os resultados de predição em lote são gravados. Cada
# processamento gera um arquivo com nome único (UUID) para que múltiplos
# usuários/execuções simultâneas não sobrescrevam o resultado uns dos outros.
RESULTS_DIR = os.path.join(_here, "resultados")
os.makedirs(RESULTS_DIR, exist_ok=True)
_RESULT_FILENAME_RE = re.compile(r"^resultado_[0-9a-f]{32}\.xlsx$")


class SmilesInput(BaseModel):
    smiles: str


@app.on_event("startup")
def _preload_models():
    """Carrega os modelos uma única vez na subida do servidor, para que o
    primeiro pedido de predição não pague o custo de carregar os .pkl e para
    falhar cedo (com um erro claro nos logs) se os arquivos de modelo não
    forem encontrados."""
    try:
        load_models()
    except Exception as e:
        print(f"⚠️  Aviso: não foi possível pré-carregar os modelos no startup: {e}")


def validar_massa(smiles):
    """Valida a massa molecular da molécula."""
    mol = Chem.MolFromSmiles(smiles)

    if mol is None:
        return False, "Invalid SMILES"

    massa = Descriptors.MolWt(mol)

    if massa < MASSA_MINIMA or massa > MASSA_MAXIMA:
        return False, f"Molecular weight out of range ({MASSA_MINIMA}-{MASSA_MAXIMA} Da). Value: {massa:.2f}"

    return True, massa


@app.get("/")
def read_root():
    return {"message": "ArboMol Classificator API", "status": "online", "modelo": "real"}


@app.post("/predict")
def predict(data: SmilesInput):
    """Classifica uma única molécula usando os modelos reais."""

    valido, info = validar_massa(data.smiles)
    if not valido:
        return {"erro": info}

    try:
        resultado = predict_smiles(data.smiles)
        return resultado
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")


@app.post("/predict_batch")
async def predict_batch(file: UploadFile = File(...)):
    """Classifica múltiplas moléculas de um arquivo usando os modelos reais."""

    if not file.filename.endswith(('.csv', '.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="File must be CSV or Excel")

    try:
        contents = await file.read()

        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
        else:
            df = pd.read_excel(io.BytesIO(contents))

        if 'Smiles' not in df.columns:
            raise HTTPException(status_code=400, detail="File must contain a 'Smiles' column")

        smiles_list = df['Smiles'].tolist()

        smiles_validos = []
        indices_validos = []
        erros = []

        for idx, smiles in enumerate(smiles_list):
            valido, info = validar_massa(smiles)
            if valido:
                smiles_validos.append(smiles)
                indices_validos.append(idx)
            else:
                erros.append(f"Row {idx+2}: {info}")

        if not smiles_validos:
            raise HTTPException(status_code=400, detail="No valid molecules found")

        # Predição do lote inteiro em uma única chamada (modelo carregado
        # uma vez, descritores calculados de uma vez, um único predict()).
        batch_result = predict_smiles_batch(smiles_validos)

        if "erro" in batch_result:
            raise HTTPException(status_code=500, detail=batch_result["erro"])

        df_resultado = df.copy()
        df_resultado['Prediction'] = 'Invalid'
        df_resultado['Mass'] = 0
        df_resultado['Prob_Chikungunya'] = None
        df_resultado['Prob_Dengue'] = None
        df_resultado['Prob_Zika'] = None

        for i, idx in enumerate(indices_validos):
            if i < len(batch_result["resultados"]):
                resultado = batch_result["resultados"][i]
                df_resultado.loc[idx, 'Prediction'] = resultado.get("classe", "Error")
                df_resultado.loc[idx, 'Mass'] = resultado.get("massa", 0)
                probs = resultado.get("probabilidades") or {}
                df_resultado.loc[idx, 'Prob_Chikungunya'] = probs.get('chikungunya')
                df_resultado.loc[idx, 'Prob_Dengue'] = probs.get('dengue')
                df_resultado.loc[idx, 'Prob_Zika'] = probs.get('zika')

        # Nome de arquivo único por execução (evita que duas pessoas usando
        # a plataforma ao mesmo tempo sobrescrevam o resultado uma da outra).
        output_filename = f"resultado_{uuid.uuid4().hex}.xlsx"
        output_path = os.path.join(RESULTS_DIR, output_filename)
        df_resultado.to_excel(output_path, index=False)

        return {
            "message": f"Processed {len(smiles_validos)} of {len(df)} molecules",
            "validas": len(smiles_validos),
            "invalidas": len(df) - len(smiles_validos),
            "erros": erros if erros else None,
            "download_url": f"/download_resultados/{output_filename}",
            "modelo": "real",
            "predicoes": batch_result.get("resultados", [])[:5]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")


@app.get("/download_resultados/{filename}")
def download_resultados(filename: str):
    """Downloads the results file for a specific run."""
    if not _RESULT_FILENAME_RE.match(filename):
        raise HTTPException(status_code=400, detail="Invalid file name")

    file_path = os.path.join(RESULTS_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(
            file_path,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename="prediction_results.xlsx"
        )
    else:
        raise HTTPException(status_code=404, detail="Results file not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
