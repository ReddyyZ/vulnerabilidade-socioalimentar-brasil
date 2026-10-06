# Dados utilizados no experimento

As instruções completas, fontes, critérios e limitações estão no README.md
da raiz do repositório e no notebook `experimento.ipynb`.

Esta pasta contém os quatro CSVs utilizados, dois metadados SISVAN, a malha
IBGE e seus metadados, o catálogo original, seu extrato de duas fontes e o
manifesto de procedência. `SHA256SUMS` verifica esses onze arquivos.

| Fonte | Caminho |
|---|---|
| IVS/IDHM, 2010 | `ivs_idhm/atlasivs_municipios_2010.csv` |
| CadInsan, janeiro/2025 | `cadinsan/CADINSAN_2025_dados_municipais.csv` |
| SISVAN altura, menores de 5 anos, 2025 | `sisvan/sisvan_municipios_altura_por_idade_0_a_menor_5_anos_2025.csv` |
| SISVAN peso, mesmo recorte | `sisvan/sisvan_municipios_peso_por_idade_0_a_menor_5_anos_2025.csv` |
| Malha municipal de apoio | `apoio/ibge/malha_municipal_simplificada.geojson` |

IVS/IDHM e CadInsan são cópias obtidas de TriangulosTecnologia/cozsolidarias;
SISVAN vem dos relatórios públicos do Ministério da Saúde; a malha vem do IBGE.
O manifesto registra as fontes exatas, os hashes e os 54 XLSX preservados.
Os dados são congelados; novas consultas ao portal não reproduzem necessariamente
o mesmo snapshot.

Altura conserva as células do exportador, incluindo artefatos decimais. Peso
veio de uma conversão histórica que conciliou contagens. CSVs e metadados
históricos não são reescritos. DAI e DPI são calculados somente na análise.
Ler os CSVs SISVAN como texto com `utf-8-sig`; códigos territoriais são texto.

Para verificar, na raiz:

```bash
python -m scripts.reproduzir_experimento --verificar
```

Para reconstruir cópias dos CSVs a partir dos XLSX, sem rede:

```bash
python -m scripts.reconstruir_sisvan --destino resultados_reconstrucao
```

Novas coletas ficam em `dados/coletas/`, fora desta seleção.
