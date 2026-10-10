#!/usr/bin/env python3
"""
Módulo de predição - usa rdkit.Chem.Descriptors para calcular todos os descritores.

Este módulo é importado diretamente pelo backend (backend/main_working.py),
tanto em execução local quanto dentro do container Docker. Os modelos (.pkl)
são carregados uma única vez e mantidos em cache em memória (evita recarregar
~3.7MB de pickle a cada predição, que era o maior gargalo de performance do
processamento em lote).
"""

import pandas as pd
import numpy as np
import joblib
import sys
import os
import json
from rdkit import Chem
from rdkit.Chem import Descriptors, rdMolDescriptors
import warnings
warnings.filterwarnings("ignore")

# SHAP é opcional: se não estiver instalado (ex: venv antigo que ainda não
# rodou "pip install -r requirements.txt" com a versão atualizada), a
# plataforma continua funcionando normalmente, só sem a explicação da
# predição (ver explain_prediction / _get_explain_components abaixo).
try:
    import shap
except ImportError:
    shap = None

# Faixa de massa molecular aceita pela plataforma (mantida em um único lugar
# para não haver divergência entre backend, frontend e documentação).
MASSA_MINIMA = 200
MASSA_MAXIMA = 700

# Cache dos modelos carregados (pipeline, label encoder, colunas esperadas,
# e os componentes derivados usados para probabilidades/explicação).
_MODELS_CACHE = {}


def load_models():
    """Carrega (uma única vez) e retorna (pipeline, label_encoder, colunas)."""
    if not _MODELS_CACHE:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        pipeline = joblib.load(os.path.join(script_dir, "modelo_final.pkl"))
        le = joblib.load(os.path.join(script_dir, "label_encoder.pkl"))
        colunas = joblib.load(os.path.join(script_dir, "colunas.pkl"))

        _MODELS_CACHE["pipeline"] = pipeline
        _MODELS_CACHE["le"] = le
        _MODELS_CACHE["colunas"] = colunas

        # Componentes internos do pipeline usados para gerar a explicação
        # (SHAP) da predição. Isso é um extra "nice to have": se o pipeline
        # não tiver exatamente essa estrutura (scaler + selector + model) ou
        # o SHAP não estiver disponível, a explicação simplesmente fica
        # desativada e a predição principal segue funcionando normalmente.
        try:
            model_step = pipeline.named_steps.get("model") or pipeline.steps[-1][1]
            scaler_step = pipeline.named_steps.get("scaler")
            selector_step = pipeline.named_steps.get("selector")

            if selector_step is not None:
                support = selector_step.get_support()
                selected_columns = [c for c, keep in zip(colunas, support) if keep]
            else:
                selected_columns = list(colunas)

            _MODELS_CACHE["scaler_step"] = scaler_step
            _MODELS_CACHE["selector_step"] = selector_step
            _MODELS_CACHE["selected_columns"] = selected_columns
            _MODELS_CACHE["explainer"] = shap.TreeExplainer(model_step) if shap else None
        except Exception as e:
            _MODELS_CACHE["scaler_step"] = None
            _MODELS_CACHE["selector_step"] = None
            _MODELS_CACHE["selected_columns"] = None
            _MODELS_CACHE["explainer"] = None
            print(f"Aviso: explicação da predição (SHAP) desativada: {e}")

    return _MODELS_CACHE["pipeline"], _MODELS_CACHE["le"], _MODELS_CACHE["colunas"]


def _get_explain_components():
    load_models()
    return (
        _MODELS_CACHE.get("scaler_step"),
        _MODELS_CACHE.get("selector_step"),
        _MODELS_CACHE.get("selected_columns"),
        _MODELS_CACHE.get("explainer"),
    )


def explain_prediction(X_row_df, classe_idx, top_n=5):
    """
    Retorna os descritores moleculares que mais influenciaram a predição da
    classe `classe_idx` para a molécula em X_row_df (um DataFrame de 1 linha,
    já no formato de saída de calc_descriptors), usando SHAP (TreeExplainer)
    sobre o classificador final do pipeline.

    Retorna None se a explicabilidade não estiver disponível (SHAP não
    instalado, ou pipeline com estrutura diferente da esperada).
    """
    scaler_step, selector_step, selected_columns, explainer = _get_explain_components()
    if explainer is None or selector_step is None or scaler_step is None:
        return None

    X_scaled = scaler_step.transform(X_row_df)
    X_selected = selector_step.transform(X_scaled)

    shap_values = explainer.shap_values(X_selected)
    # Para classificação multiclasse, shap_values tem formato
    # (n_amostras, n_features, n_classes).
    contrib = np.asarray(shap_values)[0, :, classe_idx]

    raw_values = X_row_df[selected_columns].iloc[0]
    order = np.argsort(-np.abs(contrib))[:top_n]

    return [
        {
            "descritor": selected_columns[i],
            "valor": round(float(raw_values.iloc[i]), 4),
            "contribuicao": round(float(contrib[i]), 5),
            "direcao": "increases" if contrib[i] > 0 else "decreases",
        }
        for i in order
    ]


def calc_descriptors(df_smiles):
    """
    Calcula descritores moleculares usando rdkit.Chem.Descriptors
    para uma lista/coluna de SMILES de uma só vez.
    """

    # Se for um DataFrame com coluna 'Smiles', extrair a lista
    if hasattr(df_smiles, 'Smiles'):
        smiles_list = df_smiles['Smiles'].tolist()
    elif hasattr(df_smiles, '__iter__') and not isinstance(df_smiles, str):
        smiles_list = list(df_smiles)
    else:
        smiles_list = [df_smiles]

    descriptors_list = []

    # Lista de todos os descritores disponíveis no rdkit.Chem.Descriptors
    # (calculada uma vez fora do loop, não a cada molécula)
    descriptor_functions = [name for name in dir(Descriptors) if not name.startswith('_')]

    for smiles in smiles_list:
        try:
            mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                descriptors_list.append({})
                continue

            desc_dict = {}

            for desc_name in descriptor_functions:
                try:
                    if callable(getattr(Descriptors, desc_name)):
                        value = getattr(Descriptors, desc_name)(mol)
                        desc_dict[desc_name] = value
                except Exception:
                    desc_dict[desc_name] = 0

            # Adicionar descritores adicionais do rdMolDescriptors
            try:
                bcut_desc = rdMolDescriptors.CalcBCUTDescriptors(mol)
                bcut_names = ['BCUT2D_MWHI', 'BCUT2D_MWLOW', 'BCUT2D_CHGHI', 'BCUT2D_CHGLO',
                              'BCUT2D_LOGPHI', 'BCUT2D_LOGPLOW', 'BCUT2D_MRHI', 'BCUT2D_MRLOW']
                for i, name in enumerate(bcut_names):
                    if i < len(bcut_desc):
                        desc_dict[name] = bcut_desc[i]
            except Exception:
                pass

            try:
                chi_desc = rdMolDescriptors.CalcChiDescriptors(mol)
                chi_names = ['Chi0', 'Chi0n', 'Chi0v', 'Chi1', 'Chi1n', 'Chi1v',
                             'Chi2n', 'Chi2v', 'Chi3n', 'Chi3v', 'Chi4n', 'Chi4v']
                for i, name in enumerate(chi_names):
                    if i < len(chi_desc):
                        desc_dict[name] = chi_desc[i]
            except Exception:
                pass

            try:
                kappa_desc = rdMolDescriptors.CalcKappaDescriptors(mol)
                kappa_names = ['Kappa1', 'Kappa2', 'Kappa3']
                for i, name in enumerate(kappa_names):
                    if i < len(kappa_desc):
                        desc_dict[name] = kappa_desc[i]
            except Exception:
                pass

            try:
                desc_dict['FractionCSP3'] = rdMolDescriptors.CalcFractionCSP3(mol)
                desc_dict['HallKierAlpha'] = rdMolDescriptors.CalcHallKierAlpha(mol)
                desc_dict['Ipc'] = rdMolDescriptors.CalcIpc(mol)
                desc_dict['AvgIpc'] = rdMolDescriptors.CalcAvgIpc(mol)
                desc_dict['BalabanJ'] = rdMolDescriptors.CalcBalabanJ(mol)
                desc_dict['BertzCT'] = rdMolDescriptors.CalcBertzCT(mol)
                desc_dict['LabuteASA'] = rdMolDescriptors.CalcLabuteASA(mol)
            except Exception:
                pass

            try:
                desc_dict['NumAliphaticCarbocycles'] = rdMolDescriptors.CalcNumAliphaticCarbocycles(mol)
                desc_dict['NumAliphaticHeterocycles'] = rdMolDescriptors.CalcNumAliphaticHeterocycles(mol)
                desc_dict['NumAliphaticRings'] = rdMolDescriptors.CalcNumAliphaticRings(mol)
                desc_dict['NumAmideBonds'] = rdMolDescriptors.CalcNumAmideBonds(mol)
                desc_dict['NumAromaticCarbocycles'] = rdMolDescriptors.CalcNumAromaticCarbocycles(mol)
                desc_dict['NumAromaticHeterocycles'] = rdMolDescriptors.CalcNumAromaticHeterocycles(mol)
                desc_dict['NumAromaticRings'] = rdMolDescriptors.CalcNumAromaticRings(mol)
                desc_dict['NumAtomStereoCenters'] = rdMolDescriptors.CalcNumAtomStereoCenters(mol)
                desc_dict['NumBridgeheadAtoms'] = rdMolDescriptors.CalcNumBridgeheadAtoms(mol)
                desc_dict['NumHeterocycles'] = rdMolDescriptors.CalcNumHeterocycles(mol)
                desc_dict['NumSaturatedCarbocycles'] = rdMolDescriptors.CalcNumSaturatedCarbocycles(mol)
                desc_dict['NumSaturatedHeterocycles'] = rdMolDescriptors.CalcNumSaturatedHeterocycles(mol)
                desc_dict['NumSaturatedRings'] = rdMolDescriptors.CalcNumSaturatedRings(mol)
                desc_dict['NumSpiroAtoms'] = rdMolDescriptors.CalcNumSpiroAtoms(mol)
                desc_dict['NumUnspecifiedAtomStereoCenters'] = rdMolDescriptors.CalcNumUnspecifiedAtomStereoCenters(mol)
                desc_dict['RingCount'] = rdMolDescriptors.CalcNumRings(mol)
                desc_dict['Phi'] = rdMolDescriptors.CalcPhi(mol)
            except Exception:
                pass

            try:
                fragments = rdMolDescriptors.CalcFragmentDescriptors(mol)
                for key, value in fragments.items():
                    desc_dict[key] = value
            except Exception:
                pass

            try:
                peoe_vsa = rdMolDescriptors.CalcPEOE_VSA_(mol)
                smr_vsa = rdMolDescriptors.CalcSMR_VSA_(mol)
                slogp_vsa = rdMolDescriptors.CalcSlogP_VSA_(mol)
                estate_vsa = rdMolDescriptors.CalcEState_VSA_(mol)
                vsa_estate = rdMolDescriptors.CalcVSA_EState_(mol)

                for i, val in enumerate(peoe_vsa):
                    desc_dict[f'PEOE_VSA{i+1}'] = val
                for i, val in enumerate(smr_vsa):
                    desc_dict[f'SMR_VSA{i+1}'] = val
                for i, val in enumerate(slogp_vsa):
                    desc_dict[f'SlogP_VSA{i+1}'] = val
                for i, val in enumerate(estate_vsa):
                    desc_dict[f'EState_VSA{i+1}'] = val
                for i, val in enumerate(vsa_estate):
                    desc_dict[f'VSA_EState{i+1}'] = val
            except Exception:
                pass

            try:
                from rdkit.Chem import EState
                estate = EState.EStateIndices(mol)
                if estate and len(estate) > 0:
                    desc_dict['MaxEStateIndex'] = max(estate)
                    desc_dict['MinEStateIndex'] = min(estate)
                    desc_dict['MaxAbsEStateIndex'] = max(abs(e) for e in estate)
                    desc_dict['MinAbsEStateIndex'] = min(abs(e) for e in estate)
            except Exception:
                pass

            try:
                from rdkit.Chem import rdPartialCharges
                rdPartialCharges.ComputeGasteigerCharges(mol)
                charges = [float(atom.GetProp('_GasteigerCharge')) for atom in mol.GetAtoms()]
                if charges:
                    desc_dict['MaxPartialCharge'] = max(charges)
                    desc_dict['MinPartialCharge'] = min(charges)
                    desc_dict['MaxAbsPartialCharge'] = max(abs(c) for c in charges)
                    desc_dict['MinAbsPartialCharge'] = min(abs(c) for c in charges)
            except Exception:
                pass

            try:
                from rdkit.Chem import QED
                desc_dict['qed'] = QED.qed(mol)
            except Exception:
                desc_dict['qed'] = 0

            try:
                fp1 = rdMolDescriptors.GetMorganFingerprintAsBitVect(mol, 1, nBits=1024)
                fp2 = rdMolDescriptors.GetMorganFingerprintAsBitVect(mol, 2, nBits=1024)
                fp3 = rdMolDescriptors.GetMorganFingerprintAsBitVect(mol, 3, nBits=1024)

                num_atoms = mol.GetNumAtoms()
                if num_atoms > 0:
                    desc_dict['FpDensityMorgan1'] = np.sum(fp1) / num_atoms
                    desc_dict['FpDensityMorgan2'] = np.sum(fp2) / num_atoms
                    desc_dict['FpDensityMorgan3'] = np.sum(fp3) / num_atoms
            except Exception:
                pass

            try:
                from rdkit.Contrib.SynthesisS import sascorer
                desc_dict['SPS'] = sascorer.calculateScore(mol)
            except Exception:
                desc_dict['SPS'] = 0

            descriptors_list.append(desc_dict)

        except Exception:
            descriptors_list.append({})

    df_result = pd.DataFrame(descriptors_list)
    return df_result


def validar_massa(smiles):
    """Valida a massa molecular da molécula (faixa: MASSA_MINIMA-MASSA_MAXIMA Da)."""
    mol = Chem.MolFromSmiles(smiles)

    if mol is None:
        return False, "Invalid SMILES"

    massa = Descriptors.MolWt(mol)

    if massa < MASSA_MINIMA or massa > MASSA_MAXIMA:
        return False, f"Molecular weight out of range ({MASSA_MINIMA}-{MASSA_MAXIMA} Da). Value: {massa:.2f}"

    return True, massa


def predict_smiles(smiles):
    """Faz predição para um único SMILES usando os modelos reais (cacheados).

    Além da classe prevista, tenta incluir:
    - "probabilidades": probabilidade de cada classe (via predict_proba)
    - "explicacao": os descritores moleculares que mais pesaram na decisão
      (via SHAP), para dar transparência/interpretabilidade à predição.

    Essas duas chaves são melhores-esforço: se não puderem ser calculadas por
    qualquer motivo, a predição principal (classe/massa/smiles) é retornada
    normalmente mesmo assim.
    """
    try:
        valido, info = validar_massa(smiles)
        if not valido:
            return {"erro": info}

        pipeline, le, colunas = load_models()

        df_teste = pd.DataFrame({'Smiles': [smiles]})
        X_new = calc_descriptors(df_teste)
        X_new = X_new.reindex(columns=colunas, fill_value=0)

        pred = pipeline.predict(X_new)
        classe_idx = int(pred[0])
        classe = le.inverse_transform(pred)[0]

        resultado = {
            "classe": classe,
            "massa": info,
            "smiles": smiles,
            "modelo": "real"
        }

        try:
            proba = pipeline.predict_proba(X_new)[0]
            resultado["probabilidades"] = {
                str(c): round(float(p), 4) for c, p in zip(le.classes_, proba)
            }
        except Exception:
            pass

        try:
            explicacao = explain_prediction(X_new, classe_idx)
            if explicacao:
                resultado["explicacao"] = explicacao
        except Exception:
            pass

        return resultado

    except Exception as e:
        return {"erro": f"Prediction error: {str(e)}"}


def predict_smiles_batch(smiles_list):
    """
    Faz predição para uma lista de SMILES de uma só vez: carrega o modelo uma
    única vez, calcula os descritores do lote inteiro em um único DataFrame e
    chama pipeline.predict() uma única vez, em vez de um processo/predição
    por molécula (o que tornava o processamento em lote muito lento).
    """
    pipeline, le, colunas = load_models()

    resultados = []
    invalidos = []
    smiles_validos = []
    massas_validas = []

    for smiles in smiles_list:
        valido, info = validar_massa(smiles)
        if valido:
            smiles_validos.append(smiles)
            massas_validas.append(info)
        else:
            invalidos.append({"smiles": smiles, "erro": info})

    if smiles_validos:
        df_teste = pd.DataFrame({'Smiles': smiles_validos})
        X_new = calc_descriptors(df_teste)
        X_new = X_new.reindex(columns=colunas, fill_value=0)

        preds = pipeline.predict(X_new)
        classes = le.inverse_transform(preds)

        try:
            probas = pipeline.predict_proba(X_new)
        except Exception:
            probas = None

        for i, (smiles, massa, classe) in enumerate(zip(smiles_validos, massas_validas, classes)):
            item = {
                "classe": classe,
                "massa": massa,
                "smiles": smiles,
                "modelo": "real"
            }
            if probas is not None:
                item["probabilidades"] = {
                    str(c): round(float(p), 4) for c, p in zip(le.classes_, probas[i])
                }
            resultados.append(item)

    return {
        "resultados": resultados,
        "invalidos": invalidos,
        "modelo": "real"
    }


if __name__ == "__main__":
    # Teste do módulo
    if len(sys.argv) > 1:
        if sys.argv[1] == "--test":
            smiles_test = [
                "CC(C)C(=O)OC[C@@H]1[C@H]([C@H]([C@@H](O1)n2ccc(nc2=O)NO)O)O",
                "CC[C@H](C)C(=O)O[C@H]1C[C@H](C=C2[C@H]1[C@H]([C@H](C=C2)C)CC[C@@H]3C[C@H](CC(=O)O3)O)C",
                "c1c(c2c([nH]1)c(ncn2)N)[C@H]3[C@@H]([C@@H]([C@H](N3)CO)O)O"
            ]

            print("=== Teste do Módulo de Predição ===")
            for smiles in smiles_test:
                resultado = predict_smiles(smiles)
                print(f"SMILES: {smiles[:50]}...")
                print(f"Resultado: {resultado}")
                print()
        elif sys.argv[1] == "--single":
            if len(sys.argv) > 2:
                smiles = sys.argv[2]
                resultado = predict_smiles(smiles)
                print(json.dumps(resultado))
            else:
                print("Uso: python predictor_simple.py --single SMILES")
    else:
        print("Uso: python predictor_simple.py --test | --single SMILES")
