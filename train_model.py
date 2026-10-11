#!/usr/bin/env python3
"""
ArboMol Classificator — treinamento reprodutível (arquitetura de dois estágios).

Reconstrói, a partir das exportações do Cortellis em data/, os artefatos usados
pela plataforma:

    modelo_porteiro.pkl      etapa 1 — é arbovírus? (treinado contra influenza)
    modelo_especialista.pkl  etapa 2 — dengue, zika ou chikungunya
    label_encoder.pkl        classes da etapa 2
    colunas.pkl              ordem dos 217 descritores
    config_modelo.json       limites de decisão do porteiro

Todas as etapas estocásticas usam random_state = RANDOM_STATE, de modo que duas
execuções produzem modelos byte a byte idênticos.

O notebook treino_arbomol_v2.ipynb percorre o mesmo caminho passo a passo, com
as justificativas de cada decisão e os gráficos. Este script é a versão enxuta,
para reproduzir os artefatos de uma vez.

Uso (a partir da raiz do projeto):
    python train_model.py
"""
import argparse
import hashlib
import json
import os
import warnings

import joblib
import numpy as np
import pandas as pd
from rdkit import Chem, RDLogger
from rdkit.Chem import Descriptors
from rdkit.ML.Descriptors import MoleculeDescriptors

from sklearn.ensemble import ExtraTreesClassifier
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import GroupKFold, StratifiedKFold
from sklearn.preprocessing import LabelEncoder, RobustScaler
from imblearn.pipeline import Pipeline
from imblearn.under_sampling import RandomUnderSampler

warnings.filterwarnings("ignore")
RDLogger.DisableLog("rdApp.*")

RANDOM_STATE = 42
N_ESTIMATORS = 200
LIMITE_PROVAVEL = 0.50   # acima disso: provável arbovírus
LIMITE_POSSIVEL = 0.35   # entre os dois: possível, baixa confiança

ARQUIVOS = {
    "arbovirus": ["Oct_10_2026_dengue.xlsx",
                  "Oct_10_2026_zika.xlsx",
                  "Oct_10_2026_chikungunya.xlsx"],
    "influenza": ["Oct_10_2026_influenza-2.xlsx",
                  "Oct_10_2026_influenza-3.xlsx",
                  "Oct_10_2026_influenza-4.xlsx"],
}

COND_DENGUE = {"Infection, dengue virus", "Dengue hemorrhagic fever", "Dengue shock syndrome"}
COND_ZIKA = {"Infection, Zika virus"}
COND_CHIK = {"Infection, chikungunya virus"}
COND_ARBO = COND_DENGUE | COND_ZIKA | COND_CHIK

_NOMES_DESC = [n for n, _ in Descriptors._descList]
_CALC = MoleculeDescriptors.MolecularDescriptorCalculator(_NOMES_DESC)
_LIMITE_F32 = float(np.finfo(np.float32).max)


def condicoes(s):
    return {x.strip() for x in str(s).split("\n") if x.strip()}


def arbovirus_de(s):
    L = condicoes(s)
    r = []
    if L & COND_DENGUE: r.append("dengue")
    if L & COND_ZIKA:   r.append("zika")
    if L & COND_CHIK:   r.append("chikungunya")
    return r


def canonizar(smiles):
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    try:
        Chem.SanitizeMol(mol)
        return Chem.MolToSmiles(mol)
    except Exception:
        return None


def calcular_descritores(smiles_series):
    linhas = []
    for smi in smiles_series:
        mol = Chem.MolFromSmiles(smi)
        linhas.append(dict(zip(_NOMES_DESC, _CALC.CalcDescriptors(mol))) if mol else {})
    d = pd.DataFrame(linhas, columns=_NOMES_DESC).replace([np.inf, -np.inf], np.nan)
    return d.mask(d.abs() > _LIMITE_F32)


def carregar(data_dir, arquivos):
    d = pd.concat([pd.read_excel(os.path.join(data_dir, a), sheet_name=0)
                   for a in arquivos], ignore_index=True)
    d = d.drop_duplicates(subset=["Entry Number"])
    m = (d["Drug Type"].astype(str).str.startswith("Small Molecules")
         & (d["Has Structure"] == "Yes") & d["Smiles"].notna())
    d = d[m].copy()
    d["mw"] = pd.to_numeric(d["Molecular Weight"], errors="coerce")
    return d.dropna(subset=["mw"])


def parear_por_massa(alvo, fonte, seed=RANDOM_STATE):
    """Amostra de `fonte` seguindo a distribuicao de massa de `alvo` (decis).

    Sem isso, uma diferenca de tamanho entre as classes permite que o modelo as
    separe pela massa molecular, sem usar informacao estrutural.
    """
    q = np.quantile(alvo["mw"], np.linspace(0, 1, 11)); q[0] = -np.inf; q[-1] = np.inf
    a = alvo.assign(_b=pd.cut(alvo["mw"], q, labels=False))
    f = fonte.assign(_b=pd.cut(fonte["mw"], q, labels=False))
    sel = []
    for b, g in a.groupby("_b"):
        cand = f[f["_b"] == b]
        sel.append(cand.sample(min(len(g), len(cand)), random_state=seed))
    return pd.concat(sel).drop(columns="_b")


def criar_pipeline(modelo=None, seed=RANDOM_STATE, n_cols=None):
    return Pipeline([
        ("rus", RandomUnderSampler(random_state=seed)),
        ("scaler", RobustScaler()),
        ("selector", SelectKBest(f_classif, k=n_cols or len(_NOMES_DESC))),
        ("model", modelo if modelo is not None else
                  ExtraTreesClassifier(n_estimators=N_ESTIMATORS,
                                       random_state=seed, n_jobs=-1)),
    ])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--out-dir", default=".")
    ap.add_argument("--skip-eval", action="store_true")
    args = ap.parse_args()

    print("1. Carregando as exportações do Cortellis")
    arb = carregar(args.data_dir, ARQUIVOS["arbovirus"])
    flu = carregar(args.data_dir, ARQUIVOS["influenza"])
    print(f"   arbovírus {len(arb):5d} | influenza {len(flu):5d} pequenas moléculas com SMILES")

    print("2. Rotulando pelo campo Condition")
    arb["arbo"] = arb["Condition"].apply(arbovirus_de)
    mono = arb[arb["arbo"].str.len() == 1].copy()
    mono["label"] = mono["arbo"].str[0]
    print(f"   rótulo único: {len(mono)}  {mono['label'].value_counts().to_dict()}")
    print(f"   dois arbovírus (fora do treino): {(arb['arbo'].str.len() == 2).sum()}")

    # negativos: nada que tenha arbovirus no Condition
    flu = flu[~flu["Condition"].apply(lambda s: bool(condicoes(s) & COND_ARBO))]
    neg = parear_por_massa(mono, flu)
    print(f"3. Negativos (influenza) pareados por massa: {len(neg)}")

    print("4. Limpeza química")
    D = pd.concat([mono.assign(label=mono["label"]), neg.assign(label="influenza")],
                  ignore_index=True)
    D["smiles_clean"] = D["Smiles"].apply(canonizar)
    D = D.dropna(subset=["smiles_clean"]).drop_duplicates(subset=["smiles_clean", "label"])
    amb = D.groupby("smiles_clean")["label"].nunique()
    D = D[~D["smiles_clean"].isin(set(amb[amb > 1].index))].reset_index(drop=True)

    print("5. Calculando descritores")
    desc = calcular_descritores(D["smiles_clean"])
    colidem = [c for c in desc.columns if c in D.columns]
    if colidem:
        D = D.drop(columns=colidem)
    df = pd.concat([D.reset_index(drop=True), desc], axis=1)
    df = df[~df[_NOMES_DESC].isna().any(axis=1)].reset_index(drop=True)
    print(f"   {len(df)} moléculas x {len(_NOMES_DESC)} descritores")
    print(f"   {df['label'].value_counts().to_dict()}")

    X = df[_NOMES_DESC]
    eh_arbo = (df["label"] != "influenza").astype(int).values
    arb3 = df[df["label"] != "influenza"].reset_index(drop=True)
    X3 = arb3[_NOMES_DESC]
    le = LabelEncoder(); y3 = le.fit_transform(arb3["label"])

    if not args.skip_eval:
        print("6. Avaliação (divisão por scaffold — o caso realista)")
        try:
            from rdkit.Chem.Scaffolds import MurckoScaffold
            sc = [MurckoScaffold.MurckoScaffoldSmiles(mol=Chem.MolFromSmiles(s))
                  for s in df["smiles_clean"]]
        except Exception:
            sc = list(df["smiles_clean"])
        g = pd.factorize(pd.Series(sc))[0]
        a1 = []
        for tr, te in GroupKFold(n_splits=5).split(X, eh_arbo, groups=g):
            p = criar_pipeline(); p.fit(X.iloc[tr], eh_arbo[tr])
            a1.append(accuracy_score(eh_arbo[te], p.predict(X.iloc[te])))
        g3 = pd.factorize(pd.Series(sc)[df["label"] != "influenza"].values)[0]
        a2, f2 = [], []
        for tr, te in GroupKFold(n_splits=5).split(X3, y3, groups=g3):
            p = criar_pipeline(); p.fit(X3.iloc[tr], y3[tr]); pr = p.predict(X3.iloc[te])
            a2.append(accuracy_score(y3[te], pr)); f2.append(f1_score(y3[te], pr, average="macro"))
        print(f"   etapa 1 (é arbovírus?)   acurácia {np.mean(a1):.3f}")
        print(f"   etapa 2 (qual dos três?) acurácia {np.mean(a2):.3f}  macro-F1 {np.mean(f2):.3f}")

    print("7. Treinando os modelos finais")
    porteiro = criar_pipeline(); porteiro.fit(X, eh_arbo)
    especialista = criar_pipeline(); especialista.fit(X3, y3)

    os.makedirs(args.out_dir, exist_ok=True)
    for obj, nome in [(porteiro, "modelo_porteiro.pkl"),
                      (especialista, "modelo_especialista.pkl"),
                      (le, "label_encoder.pkl"),
                      (list(_NOMES_DESC), "colunas.pkl")]:
        caminho = os.path.join(args.out_dir, nome)
        joblib.dump(obj, caminho)
        h = hashlib.sha256(open(caminho, "rb").read()).hexdigest()
        print(f"   {nome:26s} {os.path.getsize(caminho):>10,} bytes  sha256 {h[:16]}...")

    cfg = {"limite_provavel": LIMITE_PROVAVEL,
           "limite_possivel": LIMITE_POSSIVEL,
           "classes_etapa2": list(le.classes_),
           "negativo_usado_no_treino": "influenza",
           "n_treino_porteiro": int(len(eh_arbo)),
           "n_treino_especialista": int(len(y3))}
    with open(os.path.join(args.out_dir, "config_modelo.json"), "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, indent=2, ensure_ascii=False)
    print(f"   config_modelo.json         {cfg}")


if __name__ == "__main__":
    main()
