# Bases selecionadas para a pesquisa

## Objetivo e recorte

> Identificar áreas do Brasil de maior risco alimentar e vulnerabilidade social a partir dos indicadores IVS, IDHM, CadÚnico, CadInsan e SISVAN.

Esta pasta reúne as bases municipais já disponíveis no projeto para essa análise,
incluindo CADINSAN como fonte complementar. O recorte nutricional selecionado é
**altura por idade e peso por idade de crianças de 0 a menos de 5 anos, em 2025**.

Organização realizada em **4 de outubro de 2026**. Os quatro arquivos de dados
são cópias integrais dos arquivos existentes: nenhum cabeçalho, valor, código,
formato ou categoria foi alterado nesta organização. Os arquivos de origem
continuam preservados. A integração e os cálculos ocorrem somente na base
analítica gerada pelo [notebook](../../notebooks/01_sobreposicao_criterios.ipynb).

## Conteúdo

| Fonte | Arquivo | Registros municipais | Referência temporal | Papel na pesquisa |
|---|---|---:|---|---|
| IVS e IDHM | [atlasivs_municipios_2010.csv](ivs_idhm/atlasivs_municipios_2010.csv) | 5.565 | 2010, documentado no catálogo | Vulnerabilidade social e desenvolvimento humano |
| CadÚnico | [municipios-cadunico.json](cadunico/municipios-cadunico.json) | 5.564 | Junho de 2026 | Pessoas cadastradas, para contextualização de demanda |
| CADINSAN | [CADINSAN_2025_dados_municipais.csv](cadinsan/CADINSAN_2025_dados_municipais.csv) | 5.570 | Janeiro de 2025, conforme relatório oficial | Famílias em risco estimado nos cenários com/sem efeito do PBF |
| SISVAN | [indicadores_altura_peso_idade_menores_5_2025.csv](sisvan/indicadores_altura_peso_idade_menores_5_2025.csv) | 5.571 | 2025 | Déficit de altura/estatura para idade (DAI) e déficit de peso para idade (DPI) |

**O IDHM já está no arquivo do IVS.** Não é necessário um segundo arquivo para
acessar suas variáveis. Este CSV contém `ivs`, suas três dimensões, `idhm` e
dimensões/componentes do IDHM.

O [dataset_catalogue.json](../../dataset_catalogue.json) documenta o JSON do
CadÚnico como contagem de **pessoas cadastradas em junho/2026**, obtida do campo
`cadun_qtd_pessoas_cadastradas_i`, com `anomes:202606`. Os hashes das três bases
sociais correspondem exatamente aos registrados no catálogo.

Já `Cadastros_Cadunico` no CADINSAN é um denominador de **famílias**, no universo
analisado pelo indicador. O relatório oficial citado pelo catálogo informa
referência de janeiro/2025 e famílias com cadastro atualizado nos últimos 12
meses. As contagens de pessoas e famílias não são intercambiáveis.

`com_PBF` e `sem_PBF` representam cenários considerando e desconsiderando o
efeito do Bolsa Família na renda. Não são grupos separados de beneficiários e
não beneficiários. As quantidades são estimativas de risco, não medições
diretas de insegurança alimentar de todas as famílias residentes.

## Arquivos de origem e rastreabilidade

Os caminhos abaixo são relativos à raiz do repositório:

| Cópia nesta pasta | Arquivo de origem |
|---|---|
| `ivs_idhm/atlasivs_municipios_2010.csv` | `atlasivs_municipios_2010.csv` |
| `cadunico/municipios-cadunico.json` | `municipios-cadunico.json` |
| `cadinsan/CADINSAN_2025_dados_municipais.csv` | `CADINSAN_2025_dados_municipais.csv` |
| `sisvan/indicadores_altura_peso_idade_menores_5_2025.csv` | `dados/tratados/sisvan/criancas_menores_5/indicadores_altura_peso_idade_menores_5_2025.csv` |

As URLs registradas para os arquivos sociais estão em
[`fonte_dados.json`](../../fonte_dados.json). Elas apontam para cópias publicadas
no repositório `TriangulosTecnologia/cozsolidarias` no GitHub. Portanto, estes
arquivos sociais disponíveis no projeto não devem ser descritos como extrações
diretas feitas aqui nos portais oficiais. O catálogo é documentação do
repositório de origem; seu status declarado é `draft`. O notebook o incorpora
e confere a correspondência dos arquivos por SHA-256 em cada execução.

A referência mensal e os cenários do CadInsan são complementados pelo
[relatório oficial do MDS](https://www.gov.br/mds/pt-br/Sisan/vigilancia-do-sisan/CADINSAN2025.pdf),
cuja tabela municipal foi conferida por amostragem com o CSV. O catálogo
descreve 2025 como referência anual; o relatório explicita a base de janeiro.

O SISVAN foi obtido do Relatório Público do Ministério da Saúde. A documentação
completa, com o dicionário das 28 colunas, filtros, fórmulas, limitações e
reprodutibilidade, está no
[README da base SISVAN](../tratados/sisvan/criancas_menores_5/README.md).
Os [metadados do produto](../tratados/sisvan/criancas_menores_5/indicadores_altura_peso_idade_menores_5_2025.metadados.json),
o [manifesto de coletas](../../metadados/manifestos/sisvan_coletas.csv) e os
XLSX oficiais permanecem nas camadas de origem do projeto.

O CSV consolidado do SISVAN é um **produto derivado**: combina dois índices e
calcula DAI e DPI. A fidelidade desta cópia ao CSV existente não a transforma
em uma exportação bruta do SISVAN.

## Leitura e integração territorial

| Fonte | Campo municipal | Formato observado |
|---|---|---|
| IVS/IDHM | `municipio` | Código de sete dígitos; não é o nome municipal |
| CadÚnico | Chaves do objeto JSON | Código de sete dígitos |
| CADINSAN | `Cod_IBGE` | Código de sete dígitos |
| SISVAN | `Código IBGE` | Código de seis dígitos |

Todos os códigos são únicos dentro de cada base selecionada. Armazenar códigos
como texto. A junção direta entre os campos de seis e sete dígitos não funciona.
Preparar uma correspondência territorial em uma etapa posterior, preservando
os códigos originais e verificando unicidade e municípios sem correspondência.

Uma conferência preliminar, comparando o código SISVAN com os **seis primeiros
dígitos** das outras bases, encontrou:

| Fonte comparada ao SISVAN | Correspondências | Municípios SISVAN ausentes nessa fonte |
|---|---:|---:|
| IVS/IDHM | 5.565 | 6 |
| CadÚnico | 5.564 | 7 |
| CADINSAN | 5.570 | 1 |

Os prefixos de seis dígitos são únicos em cada uma das três bases sociais. A
interseção preliminar dos quatro arquivos contém **5.564 municípios**. Esses
números são controles dos arquivos disponíveis, não uma validação completa da
compatibilidade das malhas territoriais. Uma junção interna reduziria a cobertura;
documentar perdas antes de decidir como integrar as fontes.

Os CSVs usam vírgula como delimitador. No IVS/IDHM há números com ponto decimal
e outros com vírgula decimal entre aspas. CADINSAN também contém percentuais
com vírgula decimal e o símbolo `%`. O CSV do SISVAN distingue percentuais
oficiais com `%` dos percentuais derivados numéricos. Tratar esses formatos
por coluna em código, sem editar os arquivos de entrada. Ler como UTF-8 com
suporte a BOM (`utf-8-sig`) para evitar alterações no primeiro cabeçalho.

## Cuidados para a análise

- IVS/IDHM de 2010, CadInsan de janeiro/2025, SISVAN de 2025 e CadÚnico de
  junho/2026 têm referências temporais diferentes.
  Justificar essa comparação; ela não descreve simultaneidade entre indicadores.
- CadÚnico JSON mede pessoas; o denominador do CadInsan mede famílias.
  Uma contagem absoluta não permite calcular cobertura sem um denominador
  populacional compatível; esse denominador não está incluído nesta seleção.
- DAI e DPI têm denominadores próprios e não devem ser somados. O SISVAN se
  refere à população acompanhada e registrada, não automaticamente à população
  inteira do município.
- O município de Boa Esperança do Norte (MT) tem total avaliado zero nos dois
  índices. Os percentuais derivados `0.0` nessa linha devem ser tratados como
  ausência de observações para a análise, não como prevalência comprovadamente
  nula.
- Preservar as diferenças entre risco alimentar, vulnerabilidade social e estado
  nutricional; associações municipais não demonstram causalidade.

As decisões metodológicas mais amplas estão em
[`INFORMACOES_PARA_A_PESQUISA.md`](../../INFORMACOES_PARA_A_PESQUISA.md).

## Processamento analítico do CadInsan

O catálogo descreve o recálculo dos percentuais no aplicativo de origem em
`datasets.municipios_cadinsan.description`, `source.notes` e nas descrições
das colunas proporcionais. O notebook adota essa mesma forma de cálculo:

```text
CadInsan do cenário (%) =
100 × Cadinsan_absoluto_do_cenário / Cadastros_Cadunico
```

As razões são calculadas sem arredondamento na base analítica, com ausência
quando o denominador não é positivo. Os percentuais originais do CSV ficam
nas colunas `cadinsan_pct_*_arquivo`, acompanhados da diferença em pontos
percentuais. Essa transformação não altera nenhum arquivo de entrada.

O notebook exporta uma comparação de seleção entre usar as razões e os
percentuais arredondados do CSV. Com IVS ≥ 0,401 e IDHM < 0,600 (fixos), P75
para CadInsan/DAI, `com_PBF` e mínimo de 100 avaliações de altura, a seleção muda de 243 para **242**
municípios, devido ao tratamento dos percentuais e empates no corte.
O IDHM baixo integra a seleção principal. A regra anterior com quantis também
em IVS/IDHM selecionava 218 municípios com as razões recalculadas. Essa mudança
é metodológica e não altera nenhum arquivo das quatro bases selecionadas.

## Integridade e atualizações

Os hashes dos quatro arquivos estão em [SHA256SUMS](SHA256SUMS). Para conferir
a integridade desta seleção, executar na raiz do projeto:

```bash
cd dados/pesquisa
sha256sum -c SHA256SUMS
```

Esta pasta é uma seleção fixa dos dados já existentes. Novas coletas não
atualizam automaticamente estas cópias. Ao adotar dados novos, registrar a
nova versão, atualizar os hashes e revisar períodos e cobertura.

O IMC por idade, produtos legados, checkpoints e relatórios combinando consultas
distintas permanecem nas pastas de origem. Esta seleção acompanha o recorte
principal aprovado de altura e peso por idade em menores de cinco anos.
