# SISVAN — Altura X Idade, menores de cinco anos, 2025

Esta é a entrada SISVAN ativa da pesquisa. Contém apenas as categorias do
relatório **Altura X Idade**, sem DAI, DPI, dados de peso ou colunas de filtro
acrescentadas. Fonte: [relatórios públicos do Ministério da Saúde](https://sisaps.saude.gov.br/sisvan/relatoriopublico/).

## Coleta e procedência

- Nova coleta nas 27 UFs em **4 de outubro de 2026**, com coletor versão 5.0.
- Ano: 2025; mês: todos; municípios: todos; fase: criança; idade: 0 a <5 anos.
- Índice SISVAN: `nu_indice_cri=3`; `nu_ciclo_vida=1`;
  `nu_idade_inicio=0`; `nu_idade_fim=5`; demais filtros: todos.
- 5.571 linhas municipais; códigos SISVAN de seis dígitos, únicos.
- Uma linha com `Total=0`: Boa Esperança do Norte/MT (`510183`).

O CSV e seu arquivo `.metadados.json` são cópias byte a byte dos produtos de
`dados/intermediarios/sisvan/coleta_20261004T205844Z/altura_por_idade/`.
Os **27 XLSX originais exatos**, sem alteração, estão em
`dados/brutos/sisvan/coleta_20261004T205844Z/altura_por_idade/0_a_menor_5_anos/2025/ufs/`.
O manifesto é `metadados/manifestos/sisvan_coleta_20261004T205844Z.csv`.
Esses caminhos são relativos à raiz do projeto.

O sidecar registra parâmetros, data, versão, hash do CSV, hashes e filtros de
cada XLSX. A análise confere o CSV e o recorte antes de processá-los.

## Colunas e fidelidade

| Colunas | Conteúdo |
|---|---|
| `Região`, `Código UF`, `UF`, `Código IBGE`, `Município` | Identificação territorial do SISVAN |
| `Altura Muito Baixa para a Idade - Quantidade`, `Altura Muito Baixa para a Idade - %` | Valores de quantidade e percentual da categoria oficial |
| `Altura Baixa para a Idade - Quantidade`, `Altura Baixa para a Idade - %` | Valores de quantidade e percentual da categoria oficial |
| `Altura Adequada para a Idade - Quantidade`, `Altura Adequada para a Idade - %` | Valores de quantidade e percentual da categoria oficial |
| `Total` | Valor do total da linha oficial |

São **12 colunas**. Os cabeçalhos multinível do XLSX são achatados para CSV
com os sufixos ` - Quantidade` e ` - %`. Portanto, o CSV é uma conversão
documentada, **não o arquivo original literalmente idêntico**. Para fidelidade
integral de arquivo e formatação, usar os XLSX preservados. Não foram criadas
categorias, corrigidas contagens ou recalculados percentuais nesta entrada.
Ano, faixa etária e fase são filtros no sidecar, não novas colunas do CSV.

CSV: vírgula, UTF-8 com BOM (`utf-8-sig`). Percentuais mantêm `%` e os símbolos
de zero apresentados na fonte. Ler como texto para conservar as células:

```python
pd.read_csv(caminho, dtype="string", encoding="utf-8-sig", keep_default_na=False)
```

## Interpretação numérica e cálculo no notebook

O exportador XLSX registra algumas contagens como números decimais: a primeira
linha de RO contém `26`, `62`, `1.02` e total `1.108`, correspondendo na
interpretação analítica a 26, 62, 1.020 e 1.108. **Esses valores decimais não
foram corrigidos na coleta nem neste CSV.**

O notebook testa escalas compatíveis, exige soma das categorias igual ao total
e concordância com percentuais oficiais com tolerância de 0,011 ponto percentual.
Decimais são interpretados em milhares; inteiros admitem valor original ou
×1.000. Sem solução, a análise é interrompida. Se há múltiplas soluções,
adota-se o menor total compatível e registra-se a ambiguidade. Esta política
conserva a interpretação da coleta histórica; não é confirmação independente
da escala pelo Ministério da Saúde. A ambiguidade pode afetar números absolutos
e elegibilidade pelo mínimo, embora escalas uniformes preservem o percentual.

Na nova coleta, 1.733 municípios exigem interpretação de escala; 3.837 têm
mais de uma solução compatível. Consultar `interpretacao_sisvan.csv`, exportado
pelo notebook, com células originais, contagens interpretadas e flags.

DAI é calculado **somente no processamento analítico**:

```text
DAI (%) = 100 × (Altura Muito Baixa + Altura Baixa) / Total avaliado
```

O cálculo usa contagens interpretadas, sem arredondamento; total zero resulta
em ausência (`NaN`), não em DAI zero. O notebook exporta `dai_n`, `dai_pct` e
`avaliados_altura` na base derivada. Não existe percentual oficial combinado
de DAI a ser lido desta entrada.

## Limites de interpretação

O relatório descreve crianças acompanhadas pelo SISVAN, não toda a população
municipal. Não calcular cobertura sem denominador demográfico compatível, nem
tratar contagens agregadas como microdados que permitem identificar indivíduos.
DAI é sinal nutricional, não medida direta de fome ou insegurança alimentar.
Referências temporais distintas e mudanças territoriais exigem cautela na
comparação com IVS/IDHM de 2010 e outras fontes sociais.

## Reprodução

O comando utilizado para esta nova coleta foi:

```bash
python -u coletar_sisvan_municipios.py --force \
  --raw-dir dados/brutos/sisvan/coleta_20261004T205844Z \
  --output-dir dados/intermediarios/sisvan/coleta_20261004T205844Z \
  --manifest metadados/manifestos/sisvan_coleta_20261004T205844Z.csv
```

Para nova coleta futura, escolher um identificador novo nas três saídas, para
não sobrescrever esta versão. O padrão em `configuracoes/sisvan/coletas.json`
é somente altura por idade, 2025, menores de cinco anos. Peso e IMC permanecem
opções explícitas, sem gerar automaticamente DAI/DPI nem produto combinado.

A antiga cópia de altura/peso foi movida, sem alteração, para
`dados/historico/pesquisa_sisvan_altura_peso_2025/`; os produtos antigos de
`dados/tratados/sisvan/` e XLSX históricos também permanecem preservados.
