# Risco alimentar e vulnerabilidade social no Brasil

Análise exploratória com objetivo de identificar áreas do Brasil de maior risco alimentar e vulnerabilidade social

## Bases de dados utilizadas

| Entrada                      | Arquivo em`dados/pesquisa/`                                                                         | Referência                            |     Registros | Obtenção                                            |
| ---------------------------- | --------------------------------------------------------------------------------------------------- | ------------------------------------- | ------------: | --------------------------------------------------- |
| IVS e IDHM                   | [atlasivs_municipios_2010.csv](dados/pesquisa/ivs_idhm/atlasivs_municipios_2010.csv)                | 2010                                  |         5.565 | Cozinhas Solidárias; fontes originais Ipea/PNUD/FJP |
| CadInsan                     | [CADINSAN_2025_dados_municipais.csv](dados/pesquisa/cadinsan/CADINSAN_2025_dados_municipais.csv)    | Janeiro/2025                          |         5.570 | Cozinhas Solidárias; relatório original MDS         |
| SISVAN - Altura X Idade      | [CSV de altura](dados/pesquisa/sisvan/sisvan_municipios_altura_por_idade_0_a_menor_5_anos_2025.csv) | 2025; Crianças de 0 a menos de 5 anos |         5.571 | Relatórios públicos do Ministério da Saúde; 27 UFs  |
| SISVAN - Peso X Idade        | [CSV de peso](dados/pesquisa/sisvan/sisvan_municipios_peso_por_idade_0_a_menor_5_anos_2025.csv)     | 2025; Crianças de 0 a menos de 5 anos |         5.571 | Relatórios públicos do Ministério da Saúde; 27 UFs  |
| Malha municipal simplificada | [GeoJSON municipal](dados/pesquisa/apoio/ibge/malha_municipal_simplificada.geojson)                 | Ano não informado pela API            | 5.571 feições | IBGE, API de malhas v4; apoio ilustrativo           |

## Estratégia e indicadores

### Indicadores utilizados

- **IVS:** vulnerabilidade das condições de vida; valores maiores indicam maior vulnerabilidade social.
- **IDHM:** desenvolvimento humano em longevidade, educação e renda; valores menores indicam menor desenvolvimento.
- **CadInsan (%):** percentual de famílias do Cadastro Único com risco alimentar estimado, considerando o efeito do Programa Bolsa Família (PBF).
- **DAI (%):** percentual de crianças avaliadas com altura baixa ou muito baixa para a idade.
- **DPI (%):** percentual de crianças avaliadas com peso baixo ou muito baixo para a idade.

### Dimensões e critérios

| Dimensão    | O que representa                                                                   | Critério adotado                                                    |
| ----------- | ---------------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| Social      | Vulnerabilidade estrutural e baixo desenvolvimento humano                          | IVS ≥0,401**e** IDHM <0,600                                         |
| Alimentar   | Concentração municipal de risco alimentar estimado                                 | CadInsan ≥P75 nacional, cenário`com_PBF`                            |
| Nutricional | Déficits de crescimento em crianças menores de cinco anos acompanhadas pelo SISVAN | DAI ≥6,7%**e** DPI ≥1,8%; mínimo de 20 avaliações em cada relatório |

Os cortes sociais correspondem às faixas alta/muito alta do IVS e baixa/muito
baixa do IDHM.

Os cortes de DAI (6,7%) e DPI (1,8%) e o mínimo de 20 avaliaçõesforam adaptados do [Mapa InSAN 2017–2022, p. 11, tabela 2](https://aplicacoes.mds.gov.br/fomento-questionario/pdf/MapaInSAN_20172022.pdf#page=11). Esses percentuais correspondem às prevalências nacionais estimadas pela Pesquisa Nacional de Demografia e Saúde (PNDS 2006), adotadas como referência pelo Mapa.

O P75 (75º percentil nacional) é uma escolha exploratória, não um corte oficial.

### Análise realizada

As bases foram integradas por município para identificar a sobreposição
simultânea das três dimensões. Foram analisados os mapas, a distribuição
territorial e a sensibilidade aos critérios. A análise é
exploratória, sem ranking ou inferência causal. Detalhes metodológicos,
auditorias e limitações estão no [notebook](experimento.ipynb).

## Resultados

Das **5.571 unidades municipais**, **5.561 são elegíveis** para a análise das
três dimensões e **10 têm dados insuficientes**. A convergência principal
identifica **508 unidades**, ou **9,14% dos elegíveis**.

O **Nordeste** concentra o maior número absoluto de unidades selecionadas: 371. O **Norte** tem a maior proporção entre os elegíveis da própria região:
123 de 449, ou 27,39%.

![Unidades municipais com convergência dos critérios sociais, alimentares e nutricionais](resultados/resultados/execucao_20261007T010623635013Z/figuras/11_convergencia_total.png)

Arquivos para consulta e download:

- [Base municipal final](resultados/resultados/execucao_20261007T010623635013Z/base_municipal_final.csv) e [unidades com convergência principal](resultados/resultados/execucao_20261007T010623635013Z/municipios_convergencia_total.csv).
- Resumos [nacional](resultados/resultados/execucao_20261007T010623635013Z/resumo_nacional.csv), [regional](resultados/resultados/execucao_20261007T010623635013Z/resumo_regional.csv) e [por UF](resultados/resultados/execucao_20261007T010623635013Z/resumo_uf.csv).
- [Sensibilidade dos critérios](resultados/resultados/execucao_20261007T010623635013Z/sensibilidade.csv) e [estabilidade da seleção](resultados/resultados/execucao_20261007T010623635013Z/estabilidade.csv).
- [Cortes utilizados](resultados/resultados/execucao_20261007T010623635013Z/cortes.csv) e [dicionário de variáveis](resultados/resultados/execucao_20261007T010623635013Z/dicionario_variaveis.csv).
- [Síntese gerada pelo notebook](resultados/resultados/execucao_20261007T010623635013Z/resumo.md) e [manifesto com parâmetros, fontes, hashes das entradas e ambiente](resultados/resultados/execucao_20261007T010623635013Z/manifesto_execucao.json).
- [Execução completa em ZIP](resultados/resultados/execucao_20261007T010623635013Z.zip).

## Organização

```text
experimento.ipynb            análise completa com resultados
dados/pesquisa/              entradas congeladas, catálogos e metadados
dados/brutos/                XLSX SISVAN utilizados
metadados/manifestos/        registros das duas coletas
resultados/                 entradas, figuras, execuções e ZIPs gerados pelo notebook
scripts/                    coletor e cliente SISVAN
requirements.txt            dependências diretas para execução local
```

## Referências

- [Atlas IVS/Ipea](https://repositorio.ipea.gov.br/handle/11058/4381).
- [Atlas Brasil/PNUD](https://www.undp.org/pt/brazil/desenvolvimento-humano/atlas-do-desenvolvimento-humano-no-brasil).
- [CadInsan 2025/MDS](https://www.gov.br/mds/pt-br/Sisan/vigilancia-do-sisan/CADINSAN2025.pdf).
- [Relatórios públicos SISVAN](https://sisaps.saude.gov.br/sisvan/relatoriopublico/).
- [IBGE — API de malhas v4](https://servicodados.ibge.gov.br/api/docs/malhas?versao=4).
- [Mapa InSAN 2017–2022, p. 11, tabela 2](https://aplicacoes.mds.gov.br/fomento-questionario/pdf/MapaInSAN_20172022.pdf#page=11): origem dos cortes nutricionais, baseados na PNDS 2006, e do mínimo de acompanhamentos.
