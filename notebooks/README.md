# Notebook da pesquisa — sobreposição de critérios

## Versão 2 — três dimensões

Notebook atualizado: [01_sobreposicao_criterios_v2.ipynb](01_sobreposicao_criterios_v2.ipynb).
O arquivo original abaixo é preservado como versão anterior; a descrição de seus
critérios não deve ser confundida com a metodologia da v2.

A v2 é autossuficiente para apresentação e execução no Colab. Incorpora quatro
entradas: IVS/IDHM, CadInsan, SISVAN Altura X Idade e SISVAN Peso X Idade.
Não lê nem incorpora o JSON de contagem de pessoas no CadÚnico. O denominador
de famílias do próprio CSV CadInsan é mantido como `familias_cadinsan`.
Nenhuma base original foi modificada.

A seleção principal identifica convergência de **três dimensões**:

- Social: IVS ≥0,401 **e** IDHM <0,600, dentro da mesma dimensão.
- Alimentar: CadInsan ≥P75 nacional (`com_PBF`), corte exploratório, não oficial.
- Nutricional: DAI ≥6,7%, com pelo menos **20 avaliações de altura**.

DAI e DPI são calculados a partir das categorias do SISVAN para menores de cinco
anos, em 2025, com denominadores separados. DPI é complementar; a alternativa
DAI ≥6,7% **e** DPI ≥1,8%, com mínimos em ambos os relatórios, é apresentada
sem substituir a análise principal. As referências nutricionais se inspiram nos
critérios do Mapa InSAN, não reproduzem seu público exclusivo PBF ou sua
clusterização. As faixas OMS do DAI têm função descritiva.

A classificação conta 0/1/2/3 dimensões; informação insuficiente permanece
ausente nas flags e recebe categoria própria. DPI ausente não inviabiliza a
seleção principal. Os rótulos não representam diagnóstico oficial ou ranking.
Sensibilidade: CadInsan P70/P75/P80/P90, mínimos 20/50/100, DAI 6,7%/10%/P75,
nos cenários com/sem efeito do PBF, incluindo entradas/saídas e Jaccard.

O peso utiliza a coleta já existente em
`dados/tratados/sisvan/peso_por_idade/`, consolidada em 4/10/2026 pela manhã;
a altura utiliza a coleta de 4/10/2026 à tarde em `dados/pesquisa/sisvan/`.
Ambas têm ano e recorte etário idênticos. Não se usa a antiga base combinada
nem seus percentuais derivados. As verificações numéricas já existentes são
preservadas, sem acrescentar comparação sistemática DAI contagens versus
percentuais oficiais.

Resultados da v2: `resultados_sobreposicao_v2/resultados/execucao_<data>/`.
São gerados 30 CSVs, 12 figuras em PNG/SVG, síntese, manifesto e ZIP. O notebook
mostra a lista por UF/nome, sem ordenação por risco; CSV completo preserva
municípios sem classificação. O percentual nacional usa o universo explícito
da malha IBGE incorporada, além do percentual entre elegíveis.

Código e reprodução local:

```bash
python -m scripts.gerar_notebook_sobreposicao_v2
python -m unittest discover -s tests -v
python -m scripts.executar_notebook_sobreposicao_v2 /tmp/sessao-analise-v2
```

O gerador reutiliza os auxiliares de leitura e cartografia da v1, incorporando
apenas os necessários no notebook (sem dependência de imports do projeto).
O executor valida células em ordem, ausência de traceback, produtos e
preservação do notebook original. Gerar novamente remove os outputs da v2;
executar novamente os restaura.

## Versão 1 — preservada

Arquivo: [01_sobreposicao_criterios.ipynb](01_sobreposicao_criterios.ipynb).

## Apresentação ao laboratório

O notebook é autossuficiente: abre com a pergunta da pesquisa e uma tabela das
bases, instituições responsáveis, links dos arquivos obtidos, períodos,
unidades e registros municipais. Distingue os arquivos sociais obtidos no
repositório de Cozinhas Solidárias da coleta direta dos relatórios SISVAN e da
malha obtida do IBGE.

Os textos se concentram na análise, fórmulas, interpretação e limitações.
Histórico de commits e referências a documentos internos não aparecem no
texto da apresentação. As células de preparação permanecem recolhidas;
verificações completas e informações de reprodução continuam no processamento
e nas exportações. Essa reorganização não muda dados, critérios ou resultados.

A seção 8 separa os indicadores da seleção (IVS, IDHM, CadInsan e DAI, com
denominadores) da caracterização dos municípios (pessoas no CadÚnico e famílias
em risco estimado). Os cabeçalhos dessas tabelas são legíveis; a base exportada
mantém os nomes analíticos e os códigos municipais. DPI e dados de peso foram
retirados de toda a análise, não somente dessas tabelas. A comparação regional
utiliza apenas DAI. Flags são mantidas na exportação para auditoria.

As tabelas exibidas usam o padrão brasileiro: contagens como `9.486` e `223`,
índices como `0,401` e percentuais como `26,86%`. Ausências aparecem como `—`;
códigos municipais permanecem como texto. A formatação é aplicada somente à
visualização, sem converter valores em strings na base analítica e sem alterar
entradas, cálculos ou CSVs exportados.

## Uso no Google Colab

1. Baixar o `.ipynb` e abri-lo no Colab por **Arquivo → Abrir notebook → Upload**.
2. Revisar a primeira célula de parâmetros.
3. Selecionar **Ambiente de execução → Executar tudo**.
4. Conferir as tabelas de qualidade, cortes, mapas, municípios selecionados e
   sensibilidade antes de interpretar os resultados.
5. Baixar o ZIP de resultados pela aba de arquivos. Para download automático,
   ativar `BAIXAR_RESULTADOS_NO_COLAB` na célula de parâmetros e executar novamente.

O notebook é autocontido: incorpora cópias byte a byte das quatro bases de
[`dados/pesquisa/`](../dados/pesquisa/), hashes, catálogo das fontes e malha de apoio.
Não exige acesso ao repositório, Google Drive, SISVAN ou credenciais. A
instalação inicial de bibliotecas pode precisar de internet. Os arquivos das
fontes são restaurados na sessão e o processamento gera resultados separados.

## Regra inicial

- IVS ≥ **0,401**, corte fixo de vulnerabilidade alta ou muito alta.
- IDHM < **0,600**, corte fixo de desenvolvimento baixo ou muito baixo.
- CadInsan proporcional `com_PBF` recalculado sem arredondamento,
  igual ou superior ao percentil 75, com
  denominador informado positivo.
- DAI igual ou superior ao percentil 75 dos municípios com pelo menos
  **100 avaliações de altura**.
- Dados válidos para os quatro critérios; empates nos quantis e no corte do IVS
  são incluídos, enquanto o limite do IDHM é estrito (`<`).

Os cortes sociais seguem as faixas de referência do
[Atlas do IVS/Ipea](https://repositorio.ipea.gov.br/bitstream/11058/4381/1/Atlas_da_vulnerabilidade_social_nos_municipios_brasileiros.pdf)
e do [IDHM/PNUD](https://www.undp.org/sites/g/files/zskgke326/files/2024-05/anexo_estatistico_pnud_21maio24_isbn_web2.pdf).
IVS exatamente 0,401 é incluído; IDHM exatamente 0,600 não é incluído.
Os quantis de CadInsan/DAI e o mínimo de avaliações são escolhas exploratórias;
a sobreposição não é classificação oficial de risco alimentar. Cada município
tem o mesmo peso nos quantis nacionais, calculados antes de filtrar pelos
critérios sociais. A tabela de cortes distingue método fixo de quantil;
percentil fica vazio para IVS/IDHM.

DAI é calculado no notebook a partir das categorias de altura; CadInsan também
usa razões sem arredondamento na base analítica. Denominador zero
produz ausência analítica (`NaN`), mantendo os valores do CSV em colunas próprias.
CadÚnico é contextual. O JSON representa pessoas
cadastradas em junho/2026; a regra principal é IVS elevado + IDHM baixo +
CadInsan elevado + DAI elevado. O IDHM passou a ser obrigatório por decisão
metodológica da pesquisa. `QUANTIL` não altera IVS/IDHM; seus cortes são fixos
também na sensibilidade. IDHM ausente implica informação insuficiente, não baixo risco.

O notebook valida os hashes do catálogo contra as três bases sociais, conserva
os percentuais originais em colunas `*_arquivo` e exporta a comparação entre
seleções com percentuais arredondados e recalculados. Com os parâmetros padrão,
são **242 municípios selecionados**; usar as proporções do CSV resultaria em 243.
A regra anterior, com quartis também para IVS/IDHM, selecionava 218. A troca
somente dos cortes sociais acrescenta 24 municípios; as bases originais, os
quantis nutricionais/alimentares e o mínimo de 100 avaliações permanecem iguais.

## Produtos

- Base municipal integrada com códigos originais, indicadores, presença por
  fonte, elegibilidade, perfil e motivos de não classificação.
- Lista de municípios com convergência dos quatro critérios, ordenada por UF e
  nome, sem índice composto ou ranking sintético.
- Distribuições, associações, correlações de Spearman e mapas de disponibilidade,
  IVS, IDHM, CadInsan, DAI e sobreposição. No mapa do IDHM, vermelho indica
  valores menores; nos demais mapas numéricos, valores maiores.
- Resumo regional de DAI por razão entre somas de numerador e avaliações de altura.
- Auditoria de interpretação das contagens SISVAN, com células preservadas,
  mudanças de escala e indicação de ambiguidades.
- Sensibilidade a percentis 75/80, mínimos de 30/50/100 e cenários
  `com_PBF`/`sem_PBF`, incluindo frequência de seleção e Jaccard. O IDHM usa
  corte fixo < 0,600 e IVS ≥ 0,401 em todas as especificações;
  as 12 especificações selecionam de 179 a 270 municípios.
- CSVs, figuras PNG/SVG, síntese Markdown e manifesto com parâmetros, hashes e
  versões do ambiente, reunidos em um ZIP por execução.
- Validação do catálogo e auditoria do efeito do arredondamento, com os
  municípios que mudaram de seleção e os cortes de comparação.

Os resultados ficam em `resultados_sobreposicao/resultados/execucao_<data>/`,
relativo à pasta da sessão. Cada exportação tem um diretório próprio.

## Limitações visíveis na execução

IVS/IDHM são de 2010; SISVAN cobre 2025; CadInsan tem referência janeiro/2025;
o JSON CadÚnico contém pessoas cadastradas em junho/2026. O catálogo documenta
as três bases sociais, com hashes correspondentes. O relatório oficial
complementa o período mensal e os cenários do CadInsan.

CadInsan estima risco entre famílias do universo analisado. `com_PBF` considera
o efeito do Bolsa Família na renda e `sem_PBF` é um cenário contrafactual sem
esse efeito. Seu risco estimado não é medição direta em todas as famílias
residentes. Os cenários não são grupos de beneficiários e não beneficiários.

O JSON CadÚnico representa pessoas, enquanto `Cadastros_Cadunico` do CadInsan
representa famílias. Esses valores e períodos continuam separados; não há
conversão entre pessoas e famílias nem cálculo de cobertura populacional.

O SISVAN descreve a população acompanhada; o mínimo de avaliações não demonstra
representatividade. Não se calcula cobertura populacional sem denominador
demográfico adequado.

O SISVAN foi baixado novamente nas 27 UFs em 4 de outubro de 2026, usando o
coletor atualizado, sem indicadores derivados. O CSV achata cabeçalhos do XLSX
e preserva valores numéricos como aparecem nas células; os XLSX exatos ficam
na camada bruta. A interpretação de contagens ocorre no notebook, por soma e
percentuais. Inteiros que conferem são preservados sem criar uma alternativa
uniforme ×1.000. A leitura de decimais e a conciliação de células inconsistentes
continuam sendo verificadas, exigindo solução única.
Ver [documentação da entrada](../dados/pesquisa/sisvan/README.md).

Os detalhes da revisão numérica não aparecem no texto da apresentação nem nas
linhas exibidas da tabela de qualidade. A auditoria continua nas exportações;
a apresentação não lista municípios para aprovação individual. A decisão
aprovada é não multiplicar linhas inteiras coerentes por 1.000. A hipótese
artificial deixou de ser gerada, sem alterar os totais ou os 242 selecionados.

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
