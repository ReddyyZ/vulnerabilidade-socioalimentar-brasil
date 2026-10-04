# Notebook da pesquisa — sobreposição de critérios

Arquivo: [01_sobreposicao_criterios.ipynb](01_sobreposicao_criterios.ipynb).

## Uso no Google Colab

1. Baixar o `.ipynb` e abri-lo no Colab por **Arquivo → Abrir notebook → Upload**.
2. Revisar a primeira célula de parâmetros.
3. Selecionar **Ambiente de execução → Executar tudo**.
4. Conferir as tabelas de qualidade, cortes, mapas, municípios selecionados e
   sensibilidade antes de interpretar os resultados.
5. Baixar o ZIP de resultados pela aba de arquivos. Para download automático,
   ativar `BAIXAR_RESULTADOS_NO_COLAB` na célula de parâmetros e executar novamente.

O notebook é autocontido: incorpora cópias byte a byte das quatro bases de
[`dados/pesquisa/`](../dados/pesquisa/), hashes, documentação e malha de apoio.
Não exige acesso ao repositório, Google Drive, SISVAN ou credenciais. A
instalação inicial de bibliotecas pode precisar de internet. Os arquivos das
fontes são restaurados na sessão e o processamento gera resultados separados.

## Regra inicial

- IVS igual ou superior ao percentil 75 dos municípios com valor disponível.
- CadInsan proporcional `com_PBF` igual ou superior ao percentil 75, com
  denominador informado positivo.
- DAI igual ou superior ao percentil 75 dos municípios com pelo menos
  **100 avaliações de altura**.
- Dados válidos para os três critérios; empates nos cortes são incluídos.

Esses cortes são exploratórios, não classificações oficiais. Cada município
tem o mesmo peso no cálculo dos quantis. Os universos de referência dos
indicadores são distintos e aparecem na tabela de cortes.

DAI/DPI são recalculados sem arredondamento na base analítica. Denominador zero
produz ausência analítica (`NaN`), mantendo os valores do CSV em colunas próprias.
IDHM e DPI são indicadores contextuais; CadÚnico JSON permanece fora da regra
enquanto sua unidade e período não forem confirmados.

## Produtos

- Base municipal integrada com códigos originais, indicadores, presença por
  fonte, elegibilidade, perfil e motivos de não classificação.
- Lista de municípios com convergência dos três critérios, ordenada por UF e
  nome, sem índice composto ou ranking sintético.
- Distribuições, associações, correlações de Spearman e mapas de disponibilidade,
  IVS, CadInsan, DAI e sobreposição.
- Resumo regional por razão entre somas, com denominadores separados de DAI/DPI.
- Sensibilidade a percentis 75/80, mínimos de 30/50/100 e cenários
  `com_PBF`/`sem_PBF`, incluindo frequência de seleção e Jaccard.
- CSVs, figuras PNG/SVG, síntese Markdown e manifesto com parâmetros, hashes e
  versões do ambiente, reunidos em um ZIP por execução.

Os resultados ficam em `resultados_sobreposicao/resultados/execucao_<data>/`,
relativo à pasta da sessão. Cada exportação tem um diretório próprio.

## Limitações visíveis na execução

IVS/IDHM são de 2010; o SISVAN e o arquivo CadInsan selecionado são de 2025.
O período efetivo e os cenários do arquivo CadInsan precisam de conferência
metodológica. Seu risco estimado não representa medição direta em todas as
famílias residentes. Não interpretar `com_PBF` e `sem_PBF` automaticamente como
grupos de beneficiários e não beneficiários.

O JSON CadÚnico não informa unidade e período, nem equivale automaticamente à
coluna `Cadastros_Cadunico` do CadInsan. Esses valores continuam separados.

O SISVAN descreve a população acompanhada; o mínimo de avaliações não demonstra
representatividade. Não se calcula cobertura populacional sem denominador
demográfico adequado. DAI e DPI não podem ser somados.

A malha simplificada é uma cópia da API v4 do IBGE, com URL/data/hash próprios
em [`dados/apoio/ibge/`](../dados/apoio/ibge/). A versão da API não expõe ano por
parâmetro: não afirmar que a geometria é de 2025. A correspondência de códigos
não valida a equivalência de limites municipais entre períodos. Os mapas são
ilustrativos; não incluem testes de autocorrelação espacial.

## Reprodução no projeto

O código analítico está em
[`scripts/analise_sobreposicao.py`](../scripts/analise_sobreposicao.py) e é
incorporado ao notebook pelo
[`gerador`](../scripts/gerar_notebook_sobreposicao.py).
O plano está em
[`PLANO_ANALISE_NOTEBOOK_COLAB.md`](../docs/metodologia/PLANO_ANALISE_NOTEBOOK_COLAB.md).

Para gerar novamente o notebook, usando as entradas e a malha já preservadas:

```bash
python -m pip install -r notebooks/requirements.txt
python scripts/gerar_notebook_sobreposicao.py
```

Esse comando regenera o `.ipynb` sem resultados executados. Se for necessário
obter uma nova malha de apoio, usar `--coletar-malha`, registrar a nova versão e
conferir sua compatibilidade. A opção faz nova consulta ao IBGE.

Testes:

```bash
python -m unittest discover -s tests -v
```
