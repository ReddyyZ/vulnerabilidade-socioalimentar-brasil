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

O notebook exige soma das categorias igual ao total e concordância com os
percentuais oficiais com tolerância de 0,011 ponto percentual. **Inteiros
coerentes são mantidos sem testar outra linha multiplicada por 1.000**,
conforme decisão da pesquisa. Decimais são interpretados em milhares.

Somente quando essa leitura não concilia soma e percentuais, tenta-se a
interpretação de células específicas em que o exportador pode ter perdido
zeros finais. Há sete linhas assim nesta coleta: por exemplo, uma célula `1`
precisa ser lida como 1.000 para corresponder ao total e ao percentual da
categoria. Essa conciliação já existia; não extrapola uma linha coerente inteira.
Sem solução única, a análise é interrompida para conferência na fonte.

Na nova coleta, 1.733 municípios exigem interpretação numérica de alguma célula.
As alternativas artificiais dos 3.837 casos com inteiros coerentes deixaram de
ser geradas; não representam erros confirmados na fonte. Os totais, DAI e
seleção permaneceram iguais após essa alteração. Consultar
`interpretacao_sisvan.csv`, exportado pelo notebook, com células originais,
contagens interpretadas e flags. A entrada nunca é reescrita.

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
não sobrescrever esta versão. O comando acima registra a execução com a
configuração de altura isolada vigente em 4/10/2026; para reproduzir somente
esse recorte com o padrão atual, acrescentar `--indices altura_por_idade`.

Desde 5/10/2026, o padrão em `configuracoes/sisvan/coletas.json` coleta altura
e peso por idade, 2025, menores de cinco anos, em dois CSVs separados, para
atender ao notebook v3. IMC permanece opcional; não se gera automaticamente
DAI/DPI ou produto combinado. Essa mudança não modifica o arquivo de altura
documentado aqui nem atualiza os dados incorporados nos notebooks existentes.

A antiga cópia de altura/peso foi movida, sem alteração, para
`dados/historico/pesquisa_sisvan_altura_peso_2025/`; os produtos antigos de
`dados/tratados/sisvan/` e XLSX históricos também permanecem preservados.
