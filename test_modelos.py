#!/usr/bin/env python3
"""
Script para testar se os modelos estão funcionando igual ao código original
"""

import pandas as pd
import joblib
import sys
import os

# predictor_simple.py vive na raiz do projeto (mesmo diretório deste script)

def test_modelos_originais():
    """Testa usando exatamente o código original fornecido pelo usuário"""
    print("=== Teste com Código Original ===")
    
    # Mesmos SMILES do exemplo original
    smiles = [
        "CC(C)C(=O)OC[C@@H]1[C@H]([C@H]([C@@H](O1)n2ccc(nc2=O)NO)O)O",
        "CC[C@H](C)C(=O)O[C@H]1C[C@H](C=C2[C@H]1[C@H]([C@H](C=C2)C)CC[C@@H]3C[C@H](CC(=O)O3)O)C",
        "c1c(c2c([nH]1)c(ncn2)N)[C@H]3[C@@H]([C@@H]([C@H](N3)CO)O)O"
    ]
    
    df_teste = pd.DataFrame({'Smiles': smiles})
    print(f"DataFrame de teste criado com {len(df_teste)} moléculas")
    print(df_teste.head())
    
    try:
        # Carregar modelos - exatamente como no código original
        print("\nCarregando modelos...")
        pipeline = joblib.load("modelo_final.pkl")
        le = joblib.load("label_encoder.pkl")
        colunas = joblib.load("colunas.pkl")
        print("Modelos carregados com sucesso!")
        
        # Importar função de cálculo de descritores
        # (antes apontava para "main_real", módulo que não existe mais desde
        # que o código foi migrado para predictor_simple.py)
        from predictor_simple import calc_descriptors
        
        # Calcular descritores - exatamente como no código original
        print("\nCalculando descritores...")
        X_new = calc_descriptors(df_teste)
        print(f"Descritores calculados: {X_new.shape}")
        
        # garantir mesmas colunas - exatamente como no código original
        print("Ajustando colunas...")
        X_new = X_new.reindex(columns=colunas, fill_value=0)
        print(f"Shape após ajuste: {X_new.shape}")
        
        # Aplicar modelo - exatamente como no código original
        print("\nFazendo predições...")
        pred = pipeline.predict(X_new)
        classe = le.inverse_transform(pred)
        
        # Exibir resultados
        print("\n=== RESULTADOS ===")
        df_resultado = df_teste.copy()
        df_resultado['predicao'] = classe
        print(df_resultado)
        
        print("\nPredições individuais:")
        for i, (smiles, pred_class) in enumerate(zip(smiles, classe)):
            print(f"{i+1}. {smiles[:50]}... -> {pred_class}")
        
        return True, df_resultado
        
    except Exception as e:
        print(f"Erro: {e}")
        return False, None

def test_api_endpoint():
    """Testa via API para comparar resultados"""
    print("\n\n=== Teste via API ===")
    
    import requests
    
    # Testar uma molécula
    smiles_test = "CC(C)C(=O)OC[C@@H]1[C@H]([C@H]([C@@H](O1)n2ccc(nc2=O)NO)O)O"
    
    try:
        response = requests.post(
            "http://localhost:8000/predict",
            json={"smiles": smiles_test}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"API Result: {result}")
            return True, result
        else:
            print(f"API Error: {response.status_code} - {response.text}")
            return False, None
            
    except Exception as e:
        print(f"Erro na API: {e}")
        return False, None

if __name__ == "__main__":
    print("Testando modelos de classificação molecular...")
    
    # Testar código original
    sucesso_original, resultado_original = test_modelos_originais()
    
    # Testar API
    sucesso_api, resultado_api = test_api_endpoint()
    
    print("\n=== COMPARAÇÃO ===")
    if sucesso_original and sucesso_api:
        print("Ambos os testes funcionaram!")
        print(f"Resultado original: {resultado_original['predicao'].iloc[0]}")
        print(f"Resultado API: {resultado_api.get('classe', 'N/A')}")
        
        if resultado_original['predicao'].iloc[0] == resultado_api.get('classe'):
            print("Resultados CONGRUENTES! ")
        else:
            print("Resultados DIFERENTES - verificar implementação!")
    else:
        print("Houve problemas nos testes")
