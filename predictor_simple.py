#!/usr/bin/env python3
"""
ArboMol Classificator — módulo de predição (arquitetura de dois estágios).

A classificação acontece em duas etapas encadeadas:

    Etapa 1 — "porteiro"      modelo_porteiro.pkl
        Decide se a molécula tem características de compostos em desenvolvimento
        contra arbovírus. Foi treinado com arbovírus contra influenza.

    Etapa 2 — "especialista"  modelo_especialista.pkl
        Só é executado se o porteiro aprovar. Distribui a molécula entre dengue,
        zika e chikungunya.

Os limites de decisão do porteiro vêm de config_modelo.json e definem três
respostas possíveis: provável, possível (baixa confiança) e improvável.

IMPORTANTE: os descritores são calculados exatamente como no treinamento
(rdkit.Chem.Descriptors._descList, via MolecularDescriptorCalculator). Qualquer
divergência nesse cálculo altera silenciosamente as predições.
"""

import json
import os
import warnings

import joblib
import numpy as np
import pandas as pd
from rdkit import Chem, RDLogger
from rdkit.Chem import Descriptors
from rdkit.ML.Descriptors import MoleculeDescriptors

warnings.filterwarnings("ignore")
RDLogger.DisableLog("rdApp.*")

# SHAP é opcional: sem ele a plataforma funciona, apenas sem a explicação.
try:
    import shap
except ImportError:
    shap = None

# Faixa de massa molecular aceita (mantida num único lugar para não divergir
# entre backend, frontend e documentação).
MASSA_MINIMA = 200
MASSA_MAXIMA = 700

_DIR = os.path.dirname(os.path.abspath(__file__))
_CACHE = {}

# Lista de descritores: a mesma do treinamento, na mesma ordem.
_NOMES_DESC = [n for n, _ in Descriptors._descList]
_CALC = MoleculeDescriptors.MolecularDescriptorCalculator(_NOMES_DESC)

# Valores finitos mas grandes demais para float32 fazem o scikit-learn recusar
# a entrada. Alguns descritores (Ipc) chegam lá em moléculas grandes.
_LIMITE_FLOAT32 = float(np.finfo(np.float32).max)


def _caminho(nome):
    return os.path.join(_DIR, nome)


def load_models():
    """Carrega (uma única vez) os dois modelos, o encoder e a configuração."""
    if _CACHE:
        return _CACHE

    _CACHE["porteiro"] = joblib.load(_caminho("modelo_porteiro.pkl"))
    _CACHE["especialista"] = joblib.load(_caminho("modelo_especialista.pkl"))
    _CACHE["le"] = joblib.load(_caminho("label_encoder.pkl"))
    _CACHE["colunas"] = list(joblib.load(_caminho("colunas.pkl")))

    with open(_caminho("config_modelo.json"), encoding="utf-8") as fh:
        cfg = json.load(fh)
    _CACHE["limite_provavel"] = float(cfg.get("limite_provavel", 0.50))
    _CACHE["limite_possivel"] = float(cfg.get("limite_possivel", 0.35))

    # Explicadores SHAP, um por etapa. São "melhor esforço": se algo falhar,
    # a predição continua funcionando, só sem a explicação.
    for chave, pipe in (("porteiro", _CACHE["porteiro"]),
                        ("especialista", _CACHE["especialista"])):
        try:
            _CACHE[f"shap_{chave}"] = (
                shap.TreeExplainer(pipe.named_steps["model"]) if shap else None)
        except Exception as e:  # pragma: no cover
            _CACHE[f"shap_{chave}"] = None
            print(f"Aviso: explicação SHAP desativada para o {chave}: {e}")

    return _CACHE


def calc_descriptors(entrada):
    """
    Calcula os descritores 2D do RDKit para um ou vários SMILES.

    Aceita um DataFrame com coluna 'Smiles', uma lista de SMILES ou um SMILES
    único. Devolve um DataFrame com uma linha por molécula.
    """
    if hasattr(entrada, "Smiles"):
        smiles_list = entrada["Smiles"].tolist()
    elif isinstance(entrada, str):
        smiles_list = [entrada]
    else:
        smiles_list = list(entrada)

    linhas = []
    for smi in smiles_list:
        mol = Chem.MolFromSmiles(smi) if isinstance(smi, str) else None
        linhas.append(dict(zip(_NOMES_DESC, _CALC.CalcDescriptors(mol))) if mol else {})

    df = pd.DataFrame(linhas, columns=_NOMES_DESC)
    df = df.replace([np.inf, -np.inf], np.nan)
    return df.mask(df.abs() > _LIMITE_FLOAT32)


def _matriz(smiles_list):
    """Descritores alinhados às colunas do treinamento, sem valores ausentes."""
    cols = load_models()["colunas"]
    X = calc_descriptors(smiles_list).reindex(columns=cols)
    return X.fillna(0.0)


def validar_massa(smiles):
    """Valida o SMILES e a faixa de massa molecular."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return False, "Invalid SMILES"
    massa = Descriptors.MolWt(mol)
    if massa < MASSA_MINIMA or massa > MASSA_MAXIMA:
        return False, (f"Molecular weight out of range "
                       f"({MASSA_MINIMA}-{MASSA_MAXIMA} Da). Value: {massa:.2f}")
    return True, massa


def _explicar(chave, X_linha, indice_classe, top_n=5):
    """Top descritores que mais pesaram, via SHAP, para uma etapa."""
    c = load_models()
    explainer = c.get(f"shap_{chave}")
    if explainer is None:
        return None
    try:
        pipe = c[chave]
        scaler = pipe.named_steps["scaler"]
        selector = pipe.named_steps["selector"]
        nomes = [n for n, k in zip(c["colunas"], selector.get_support()) if k]

        X_sel = selector.transform(scaler.transform(X_linha))
        sv = np.asarray(explainer.shap_values(X_sel))
        contrib = sv[0, :, indice_classe] if sv.ndim == 3 else sv[0]

        brutos = X_linha[nomes].iloc[0]
        ordem = np.argsort(-np.abs(contrib))[:top_n]
        return [
            {
                "descritor": nomes[i],
                "valor": round(float(brutos.iloc[i]), 4),
                "contribuicao": round(float(contrib[i]), 5),
                "direcao": "increases" if contrib[i] > 0 else "decreases",
            }
            for i in ordem
        ]
    except Exception:
        return None


def _veredito(p_arbo):
    c = load_models()
    if p_arbo >= c["limite_provavel"]:
        return "provavel", "Likely an arbovirus-associated compound"
    if p_arbo >= c["limite_possivel"]:
        return "possivel", "Possibly an arbovirus-associated compound (low confidence)"
    return "improvavel", "Unlikely to be an arbovirus-associated compound"


def predict_smiles(smiles):
    """
    Classifica uma molécula. Devolve sempre 'confianca_arbovirus' e 'veredito';
    'classe' e 'probabilidades' só vêm quando o porteiro aprova a molécula.
    """
    try:
        valido, info = validar_massa(smiles)
        if not valido:
            return {"erro": info}

        c = load_models()
        X = _matriz([smiles])

        p_arbo = float(c["porteiro"].predict_proba(X)[0, 1])
        veredito, texto = _veredito(p_arbo)

        resultado = {
            "smiles": smiles,
            "massa": info,
            "confianca_arbovirus": round(p_arbo, 4),
            "veredito": veredito,
            "veredito_texto": texto,
            "modelo": "dois_estagios",
        }

        if veredito == "improvavel":
            resultado["explicacao"] = _explicar("porteiro", X, 0)
            return resultado

        esp, le = c["especialista"], c["le"]
        pred = esp.predict(X)
        resultado["classe"] = str(le.inverse_transform(pred)[0])
        try:
            proba = esp.predict_proba(X)[0]
            resultado["probabilidades"] = {
                str(k): round(float(v), 4) for k, v in zip(le.classes_, proba)
            }
        except Exception:
            pass
        resultado["explicacao"] = _explicar("especialista", X, int(pred[0]))
        return resultado

    except Exception as e:
        return {"erro": f"Prediction error: {str(e)}"}


def predict_smiles_batch(smiles_list):
    """Versão em lote: calcula descritores e roda as duas etapas de uma vez."""
    c = load_models()
    resultados, invalidos, validos, massas = [], [], [], []

    for smi in smiles_list:
        ok, info = validar_massa(smi)
        if ok:
            validos.append(smi)
            massas.append(info)
        else:
            invalidos.append({"smiles": smi, "erro": info})

    if validos:
        X = _matriz(validos)
        p_arbo = c["porteiro"].predict_proba(X)[:, 1]

        classes = np.array([None] * len(validos), dtype=object)
        probas = None
        passou = p_arbo >= c["limite_possivel"]
        if passou.any():
            esp, le = c["especialista"], c["le"]
            Xp = X[passou]
            classes[passou] = le.inverse_transform(esp.predict(Xp))
            try:
                pp = esp.predict_proba(Xp)
                probas = {i: {str(k): round(float(v), 4)
                              for k, v in zip(le.classes_, pp[j])}
                          for j, i in enumerate(np.where(passou)[0])}
            except Exception:
                probas = None

        for i, (smi, massa) in enumerate(zip(validos, massas)):
            veredito, texto = _veredito(float(p_arbo[i]))
            item = {
                "smiles": smi,
                "massa": massa,
                "confianca_arbovirus": round(float(p_arbo[i]), 4),
                "veredito": veredito,
                "veredito_texto": texto,
                "modelo": "dois_estagios",
            }
            if classes[i] is not None:
                item["classe"] = str(classes[i])
                if probas and i in probas:
                    item["probabilidades"] = probas[i]
            resultados.append(item)

    return {"resultados": resultados, "invalidos": invalidos,
            "modelo": "dois_estagios"}


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--single" and len(sys.argv) > 2:
        print(json.dumps(predict_smiles(sys.argv[2]), ensure_ascii=False))
    else:
        exemplos = [
            ("sacarose", "OC[C@H]1O[C@@](CO)(O[C@H]2O[C@H](CO)[C@@H](O)[C@H](O)[C@H]2O)[C@@H](O)[C@@H]1O"),
            ("quercetina", "O=c1c(O)c(-c2ccc(O)c(O)c2)oc2cc(O)cc(O)c12"),
            ("paracetamol", "CC(=O)Nc1ccc(O)cc1"),
        ]
        for nome, smi in exemplos:
            r = predict_smiles(smi)
            print(f"\n{nome}")
            print(json.dumps(r, indent=2, ensure_ascii=False)[:600])
