#!/usr/bin/env python3
"""
Script de teste para verificar o funcionamento do backend
"""

import requests
import pandas as pd
import json
import time

def test_backend():
    """Testa os endpoints do backend"""
    base_url = "http://localhost:8000"
    
    print("🧪 Testando Backend do ArboMol Classificator")
    print("=" * 60)
    
    # Testar se o backend está online
    try:
        response = requests.get(f"{base_url}/")
        if response.status_code == 200:
            print("✅ Backend está online!")
            print(f"   Mensagem: {response.json()}")
        else:
            print("❌ Backend não está respondendo corretamente")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Não foi possível conectar ao backend")
        print("   Certifique-se de que o backend está rodando em http://localhost:8000")
        return False
    
    print()
    
    # Testar predição individual com SMILES válido
    print("🔬 Testando predição individual...")
    test_smiles = "CCO"  # Etanol
    
    try:
        response = requests.post(
            f"{base_url}/predict",
            json={"smiles": test_smiles}
        )
        
        if response.status_code == 200:
            result = response.json()
            if "erro" in result:
                print(f"⚠️  Erro esperado (massa fora do intervalo): {result['erro']}")
            else:
                print(f"✅ Predição individual funcionou!")
                print(f"   SMILES: {result['smiles']}")
                print(f"   Classe: {result['classe']}")
                print(f"   Massa: {result['massa']:.2f} Da")
        else:
            print(f"❌ Erro na predição individual: {response.status_code}")
            print(f"   Detalhes: {response.text}")
    except Exception as e:
        print(f"❌ Erro ao testar predição individual: {e}")
    
    print()
    
    # Testar predição individual com massa válida
    print("🔬 Testando predição com massa válida...")
    # Usando uma molécula mais complexa que deve ter massa no intervalo
    test_smiles_valid = "CC(C)C(=O)OC[C@@H]1[C@H]([C@H]([C@@H](O1)n2ccc(nc2=O)NO)O)O"
    
    try:
        response = requests.post(
            f"{base_url}/predict",
            json={"smiles": test_smiles_valid}
        )
        
        if response.status_code == 200:
            result = response.json()
            if "erro" in result:
                print(f"⚠️  Erro: {result['erro']}")
            else:
                print(f"✅ Predição com massa válida funcionou!")
                print(f"   SMILES: {result['smiles'][:50]}...")
                print(f"   Classe: {result['classe']}")
                print(f"   Massa: {result['massa']:.2f} Da")
        else:
            print(f"❌ Erro na predição: {response.status_code}")
            print(f"   Detalhes: {response.text}")
    except Exception as e:
        print(f"❌ Erro ao testar predição: {e}")
    
    print()
    
    # Criar arquivo de teste para batch processing
    print("📁 Criando arquivo de teste para processamento em lote...")
    test_data = {
        'Smiles': [
            "CCO",  # Etanol - massa muito baixa
            "CC(C)C(=O)OC[C@@H]1[C@H]([C@H]([C@@H](O1)n2ccc(nc2=O)NO)O)O",  # Molécula complexa
            "CC[C@H](C)C(=O)O[C@H]1C[C@H](C=C2[C@H]1[C@H]([C@H](C=C2)C)CC[C@@H]3C[C@H](CC(=O)O3)O)C",  # Outra molécula complexa
            "INVALID_SMILES",  # SMILES inválido
            "c1c(c2c([nH]1)c(ncn2)N)[C@H]3[C@@H]([C@@H]([C@H](N3)CO)O)O"  # Molécula válida
        ]
    }
    
    df_test = pd.DataFrame(test_data)
    csv_file = "test_molecules.csv"
    df_test.to_csv(csv_file, index=False)
    print(f"✅ Arquivo '{csv_file}' criado com {len(df_test)} moléculas")
    
    print()
    
    # Testar processamento em lote
    print("📊 Testando processamento em lote...")
    try:
        with open(csv_file, 'rb') as f:
            response = requests.post(
                f"{base_url}/predict_batch",
                files={'file': f}
            )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Processamento em lote funcionou!")
            print(f"   Mensagem: {result['message']}")
            print(f"   Válidas: {result['validas']}")
            print(f"   Inválidas: {result['invalidas']}")
            
            if result.get('download_url'):
                print(f"   URL de download: {result['download_url']}")
                
                # Testar download
                print()
                print("⬇️  Testando download dos resultados...")
                download_response = requests.get(f"{base_url}{result['download_url']}")
                if download_response.status_code == 200:
                    print("✅ Download funcionou!")
                    # Salvar arquivo de resultados
                    with open("resultados_teste.xlsx", "wb") as f:
                        f.write(download_response.content)
                    print("   Arquivo salvo como 'resultados_teste.xlsx'")
                else:
                    print(f"❌ Erro no download: {download_response.status_code}")
            
            if result.get('erros'):
                print("   Erros encontrados:")
                for erro in result['erros'][:3]:  # Mostrar apenas os 3 primeiros
                    print(f"     - {erro}")
                if len(result['erros']) > 3:
                    print(f"     ... e mais {len(result['erros']) - 3} erros")
        else:
            print(f"❌ Erro no processamento em lote: {response.status_code}")
            print(f"   Detalhes: {response.text}")
    except Exception as e:
        print(f"❌ Erro ao testar processamento em lote: {e}")
    
    print()
    print("🎉 Testes concluídos!")
    print("=" * 60)
    
    # Limpar arquivos de teste
    import os
    try:
        os.remove(csv_file)
        print("🧹 Arquivo de teste removido")
    except:
        pass

if __name__ == "__main__":
    test_backend()
