#!/usr/bin/env python3
"""
Teste de fumaça dos modelos do ArboMol (arquitetura de dois estágios).

Verifica, sem subir o servidor, que:
  1. os quatro artefatos carregam;
  2. o cálculo de descritores devolve as 217 colunas esperadas;
  3. uma molécula de arbovírus é aprovada pelo porteiro e classificada;
  4. uma molécula claramente fora do domínio é barrada;
  5. a validação de massa e de SMILES inválido funciona;
  6. o processamento em lote devolve um resultado por molécula válida.

Uso (a partir da pasta raiz do projeto):
    python test_modelos.py
"""
import sys
import traceback

FALHAS = []


def checar(descricao, condicao, detalhe=""):
    marca = "ok  " if condicao else "FALHA"
    print(f"  [{marca}] {descricao}" + (f"  — {detalhe}" if detalhe else ""))
    if not condicao:
        FALHAS.append(descricao)
    return condicao


def main():
    print("=== 1. Carregando os artefatos ===")
    try:
        from predictor_simple import (load_models, calc_descriptors, predict_smiles,
                                      predict_smiles_batch, MASSA_MINIMA, MASSA_MAXIMA)
        c = load_models()
    except Exception:
        traceback.print_exc()
        print("\nNão foi possível carregar os modelos. Rode 'python train_model.py' antes.")
        return 1

    checar("porteiro carregado", c.get("porteiro") is not None)
    checar("especialista carregado", c.get("especialista") is not None)
    checar("label encoder com 3 classes", len(c["le"].classes_) == 3,
           str(list(c["le"].classes_)))
    checar("217 descritores", len(c["colunas"]) == 217, f"{len(c['colunas'])}")
    checar("limites coerentes", 0 < c["limite_possivel"] <= c["limite_provavel"] < 1,
           f"possível {c['limite_possivel']}, provável {c['limite_provavel']}")

    print("\n=== 2. Cálculo de descritores ===")
    X = calc_descriptors(["CC(=O)Nc1ccc(O)cc1"])
    checar("uma linha por molécula", len(X) == 1)
    checar("colunas na ordem do treino", list(X.columns) == list(c["colunas"]))

    print("\n=== 3. Molécula de arbovírus (deve passar) ===")
    # composto do conjunto de treino, associado a chikungunya
    smi_arbo = "CC(C)C(=O)OC[C@H]1O[C@@H](n2ccc(NO)nc2=O)[C@H](O)[C@@H]1O"
    r = predict_smiles(smi_arbo)
    checar("sem erro", "erro" not in r, r.get("erro", ""))
    if "erro" not in r:
        checar("porteiro aprovou", r["veredito"] in ("provavel", "possivel"),
               f"confiança {r['confianca_arbovirus']:.2f} -> {r['veredito']}")
        checar("devolveu uma classe", bool(r.get("classe")), str(r.get("classe")))
        p = r.get("probabilidades") or {}
        checar("três probabilidades que somam 1", len(p) == 3 and abs(sum(p.values()) - 1) < 0.02,
               str(p))

    print("\n=== 4. Molécula fora do domínio (deve ser barrada) ===")
    sacarose = "OC[C@H]1O[C@@](CO)(O[C@H]2O[C@H](CO)[C@@H](O)[C@H](O)[C@H]2O)[C@@H](O)[C@@H]1O"
    r = predict_smiles(sacarose)
    checar("sem erro", "erro" not in r, r.get("erro", ""))
    if "erro" not in r:
        checar("porteiro barrou", r["veredito"] == "improvavel",
               f"confiança {r['confianca_arbovirus']:.2f} -> {r['veredito']}")
        checar("não inventou uma classe", r.get("classe") is None,
               str(r.get("classe")))

    print("\n=== 5. Entradas inválidas ===")
    checar("massa fora da faixa é recusada",
           "erro" in predict_smiles("CC(=O)Nc1ccc(O)cc1"),
           f"faixa aceita: {MASSA_MINIMA}-{MASSA_MAXIMA} Da")
    checar("SMILES inválido é recusado", "erro" in predict_smiles("XYZ123"))

    print("\n=== 6. Lote ===")
    b = predict_smiles_batch([smi_arbo, sacarose, "CCO", "XYZ123"])
    checar("duas moléculas válidas", len(b["resultados"]) == 2, str(len(b["resultados"])))
    checar("duas recusadas", len(b["invalidos"]) == 2, str(len(b["invalidos"])))
    vereditos = [x["veredito"] for x in b["resultados"]]
    checar("lote reproduz os vereditos individuais",
           "improvavel" in vereditos and any(v != "improvavel" for v in vereditos),
           str(vereditos))

    print("\n" + "=" * 54)
    if FALHAS:
        print(f"{len(FALHAS)} verificação(ões) falharam:")
        for f in FALHAS:
            print(f"  - {f}")
        return 1
    print("Todas as verificações passaram.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
