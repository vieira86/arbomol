# Conjunto de dados — ArboMol Classificator

Três coleções de moléculas pequenas, uma por arbovírus, usadas para treinar o
classificador. Cada planilha tem duas colunas: `Entry Number` (identificador da
molécula na base de origem) e `Smiles` (estrutura química em notação SMILES).

| Arquivo | Moléculas (bruto) | Classe |
|---|---|---|
| `dengue.xlsx` | 655 | dengue |
| `zika_virus.xlsx` | 245 | zika |
| `chikungunya.xlsx` | 186 | chikungunya |

## Curadoria aplicada pelo `train_model.py`

1. Cada SMILES é validado e canonizado com o RDKit; estruturas que não são
   interpretadas são descartadas.
2. Duplicatas dentro de cada classe são removidas pelo SMILES canônico.
3. Duplicatas **entre** classes são resolvidas dando prioridade à classe de
   menor cardinalidade (chikungunya, depois zika, depois dengue), para que as
   classes raras não sejam esvaziadas por moléculas também reportadas para um
   vírus mais representado. Cada estrutura fica com exatamente um rótulo.
4. Moléculas para as quais algum descritor não pode ser calculado são removidas.

Resultado: **912 moléculas** — 486 dengue, 240 zika, 186 chikungunya.

## Procedência

PENDENTE DE PREENCHIMENTO. Documentar aqui, antes da publicação:

- a base de origem de cada coleção (ChEMBL, PubChem BioAssay, curadoria própria
  da literatura, etc.) e a data de extração;
- o tipo de ensaio biológico a que cada rótulo se refere (inibição da replicação
  viral em ensaio celular, inibição enzimática de uma proteína viral específica,
  etc.);
- o critério quantitativo ou qualitativo usado para considerar um composto
  "associado" a cada vírus (ponto de corte de IC50/EC50, sinalizador binário de
  atividade, ou relato na literatura).

## Limitação conhecida

O conjunto não contém uma classe "inativo". O modelo responde qual dos três
vírus é o mais provável para uma dada estrutura, e nunca "nenhum dos três".
