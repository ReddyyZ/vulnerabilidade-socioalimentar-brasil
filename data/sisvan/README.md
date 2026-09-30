# SISVAN municipal — base bruta (2025)

## Arquivo principal

sisvan_municipios_2025.csv é uma transcrição da tabela municipal do
Relatório Público do SISVAN. Não contém indicadores calculados, nomes ou códigos
substituídos pelo IBGE, nem municípios acrescentados por outra fonte.

Fonte: https://sisaps.saude.gov.br/sisvan/relatoriopublico/

Endpoint: POST https://sisaps.saude.gov.br/sisvan/relatoriopublico/estadonutricional

Filtros oficiais:

- nuAno=2025 e nuMes[]=99;
- tpFiltro=M e coMunicipioIbge=99;
- nu_ciclo_vida=1;
- nu_idade_inicio=0 e nu_idade_fim=5;
- nu_indice_cri=4 (IMC por idade);
- sexo, raça/cor, origem, povo/comunidade e escolaridade: todos.

O ano não é uma coluna da tabela do SISVAN: ele é metadado do filtro e do nome
do arquivo. O código municipal é mantido com os seis dígitos exibidos pelo
SISVAN. Os nomes municipais também são os textos do SISVAN.

O XLSX possui cabeçalho em dois níveis. Como CSV não admite células mescladas,
os níveis foram combinados sem mudar os rótulos, por exemplo:
Magreza acentuada - Quantidade e Magreza acentuada - %.

As quantidades são serializadas como inteiros no CSV. Assim, o valor brasileiro
1.114 é escrito como 1114; isso muda somente a formatação do separador de
milhar, não o valor. Os percentuais preservam % e o símbolo - usado oficialmente
para categoria com zero casos.

## Resultado

- Linhas municipais do SISVAN: **5571**.
- Linhas com Total=0: **1**.
- Códigos duplicados: **0**.
- Categorias cuja soma difere de Total: **0**.

Linhas oficiais com total zero:

- 510183 — BOA ESPERANCA DO NORTE/MT

A versão anteriormente entregue, com código IBGE de sete dígitos e indicador
de desnutrição calculado, foi preservada separadamente como
sisvan_municipios_2025_derivada.csv.

## Reprodução

    python3 scripts/coletar_sisvan.py --year 2025

Os checkpoints brutos ficam em
data/sisvan/checkpoints_brutos/2025/UF.csv. O processo é sequencial,
possui rate limiting, sessão, timeout, retries e retomada.
