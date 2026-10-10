#!/usr/bin/env python3
"""
ArboMol Classificator — treinamento reprodutível do modelo.

Reproduz, do zero, os artefatos usados pela plataforma:
    modelo_final.pkl, label_encoder.pkl, colunas.pkl

Todas as etapas estocásticas usam random_state=RANDOM_STATE, de modo que
duas execuções produzem exatamente o mesmo modelo.

Uso (a partir da raiz do projeto):
    python train_model.py

Por padrao lê as planilhas de ./data e grava os .pkl na pasta atual.
Para usar outros caminhos:
    python train_model.py --data-dir CAMINHO/PARA/PLANILHAS --out-dir .
"""
import argparse, os, sys, hashlib
import numpy as np
import pandas as pd
import joblib

from rdkit import Chem, RDLogger
from rdkit.Chem import Descriptors
from rdkit.ML.Descriptors import MoleculeDescriptors

from sklearn.preprocessing import LabelEncoder, RobustScaler
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.model_selection import train_test_split, RepeatedStratifiedKFold
from sklearn.metrics import accuracy_score, f1_score, classification_report
from imblearn.under_sampling import RandomUnderSampler
from imblearn.pipeline import Pipeline

RDLogger.DisableLog("rdApp.*")

RANDOM_STATE = 42
N_FEATURES = 20
N_ESTIMATORS = 200
TEST_SIZE = 0.2

SOURCES = [("dengue", "dengue.xlsx"),
           ("zika", "zika_virus.xlsx"),
           ("chikungunya", "chikungunya.xlsx")]


def canonical(smiles):
    """Valida, sanitiza e canoniza um SMILES. Retorna None se inválido."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    try:
        Chem.SanitizeMol(mol)
        return Chem.MolToSmiles(mol)
    except Exception:
        return None


def load_dataset(data_dir):
    """Carrega, limpa e rotula as três coleções, com deduplicação cruzada."""
    frames = {}
    for label, fname in SOURCES:
        df = pd.read_excel(os.path.join(data_dir, fname))
        df["smiles_clean"] = df["Smiles"].apply(canonical)
        df = df.dropna(subset=["smiles_clean"]).drop_duplicates(subset=["smiles_clean"])
        frames[label] = df
        print(f"  {label:12s} {len(df):4d} moléculas válidas e únicas")

    # Classes menores têm prioridade: uma molécula presente em mais de uma
    # coleção é atribuída à classe de menor cardinalidade, para não esvaziar
    # as classes raras.
    seen, final = set(), {}
    for label, df in sorted(frames.items(), key=lambda kv: len(kv[1])):
        keep = df[~df["smiles_clean"].isin(seen)].copy()
        seen.update(keep["smiles_clean"])
        keep["label"] = label
        final[label] = keep
        print(f"  {label:12s} {len(keep):4d} após deduplicação cruzada")
    return pd.concat(final.values(), ignore_index=True)


def compute_descriptors(df):
    """Calcula os descritores 2D do RDKit (Descriptors._descList)."""
    names = [n for n, _ in Descriptors._descList]
    calc = MoleculeDescriptors.MolecularDescriptorCalculator(names)
    rows = []
    for smi in df["Smiles"]:
        mol = Chem.MolFromSmiles(smi)
        rows.append(dict(zip(names, calc.CalcDescriptors(mol))) if mol else {})
    out = pd.concat([df.reset_index(drop=True), pd.DataFrame(rows)], axis=1)
    return out.dropna().reset_index(drop=True)


def build_pipeline():
    """Pipeline de produção. Todas as etapas são ajustadas apenas no treino."""
    return Pipeline([
        ("rus", RandomUnderSampler(random_state=RANDOM_STATE)),
        ("scaler", RobustScaler()),
        ("selector", SelectKBest(f_classif, k=N_FEATURES)),
        ("model", ExtraTreesClassifier(n_estimators=N_ESTIMATORS,
                                       random_state=RANDOM_STATE,
                                       n_jobs=-1)),
    ])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="data",
                    help="pasta com dengue.xlsx, zika_virus.xlsx e chikungunya.xlsx")
    ap.add_argument("--out-dir", default=".")
    ap.add_argument("--skip-eval", action="store_true")
    args = ap.parse_args()

    print("1. Carregando e curando os dados")
    df_all = load_dataset(args.data_dir)
    print(f"   total após deduplicação: {len(df_all)}")

    print("2. Calculando descritores moleculares")
    df = compute_descriptors(df_all)
    X = df.select_dtypes(include="number").drop(columns=["Entry Number"])
    le = LabelEncoder()
    y = le.fit_transform(df["label"])
    print(f"   {X.shape[0]} moléculas x {X.shape[1]} descritores")
    print(f"   {dict(zip(le.classes_, np.bincount(y).tolist()))}")

    if not args.skip_eval:
        print("3. Avaliação (validação cruzada estratificada 5x5)")
        cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=5, random_state=RANDOM_STATE)
        accs, f1s = [], []
        for tr, te in cv.split(X, y):
            p = build_pipeline()
            p.fit(X.iloc[tr], y[tr])
            pred = p.predict(X.iloc[te])
            accs.append(accuracy_score(y[te], pred))
            f1s.append(f1_score(y[te], pred, average="macro"))
        print(f"   acurácia  {np.mean(accs):.3f} +/- {np.std(accs):.3f}")
        print(f"   macro-F1  {np.mean(f1s):.3f} +/- {np.std(f1s):.3f}")

        print("4. Partição de teste retida")
        Xtr, Xte, ytr, yte = train_test_split(
            X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y)
        p = build_pipeline()
        p.fit(Xtr, ytr)
        print(classification_report(yte, p.predict(Xte),
                                    target_names=le.classes_, digits=3))

    print("5. Ajustando o modelo final sobre todas as moléculas")
    pipeline = build_pipeline()
    pipeline.fit(X, y)

    os.makedirs(args.out_dir, exist_ok=True)
    for obj, name in [(pipeline, "modelo_final.pkl"),
                      (le, "label_encoder.pkl"),
                      (X.columns.tolist(), "colunas.pkl")]:
        path = os.path.join(args.out_dir, name)
        joblib.dump(obj, path)
        h = hashlib.sha256(open(path, "rb").read()).hexdigest()
        print(f"   {name:20s} {os.path.getsize(path):>9,} bytes  sha256={h[:16]}...")

    sel = pipeline.named_steps["selector"].get_support()
    print("   descritores selecionados:", list(X.columns[sel]))


if __name__ == "__main__":
    main()
