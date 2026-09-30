# Bases do SISVAN

Esta pasta contém os produtos consolidados da coleta municipal do Relatório Público do SISVAN. Os arquivos oficiais originais são preservados separadamente em `dados/brutos/sisvan/`.

## Recorte padrão

A configuração padrão está em `configuracoes/sisvan/coletas.json` e coleta:

- ano: 2025;
- abrangência: todos os municípios, uma requisição por UF;
- fase da vida: criança;
- faixa etária: 0 a menos de 5 anos;
- índices: IMC por idade e altura por idade;
- sexo, raça/cor, origem, povo/comunidade e escolaridade: todos.

## Produtos nacionais

- `imc_por_idade/sisvan_municipios_imc_por_idade_0_a_menor_5_anos_2025.csv`;
- `altura_por_idade/sisvan_municipios_altura_por_idade_0_a_menor_5_anos_2025.csv`;
- `sisvan_municipios_consultas_combinadas_2025.csv`, em formato longo.

Cada CSV possui um arquivo `.metadados.json` correspondente, com os parâmetros da consulta, colunas, UFs e estatísticas de validação.

Os CSVs são consolidações dos relatórios estaduais. O processo apenas achata o cabeçalho de dois níveis, normaliza as contagens que o XLSX representa com ponto de milhar e reúne as UFs. Não acrescenta indicadores calculados nem códigos de fontes externas.

## Camada bruta

Cada resposta oficial é mantida sem alteração:

```text
dados/brutos/sisvan/
├── imc_por_idade/<faixa>/<ano>/ufs/<UF>.xlsx
└── altura_por_idade/<faixa>/<ano>/ufs/<UF>.xlsx
```

O hash SHA-256 e os filtros de cada XLSX estão registrados em:

```text
metadados/manifestos/sisvan_coletas.csv
```

Arquivos brutos existentes são reutilizados e não são sobrescritos. A substituição somente ocorre quando o usuário informa explicitamente `--force`.

## Executar a configuração padrão

```bash
python3 scripts/coletar_sisvan.py
```

O atalho histórico na raiz continua disponível:

```bash
python3 coletar_sisvan_municipios.py
```

## Listar índices e faixas disponíveis

```bash
python3 scripts/coletar_sisvan.py --listar-opcoes
```

As nove combinações de faixa infantil aceitas pelo formulário oficial são:

- `0_a_menor_6_meses` (`0-6m`);
- `0_a_menor_2_anos` (`0-2`);
- `0_a_menor_5_anos` (`0-5`);
- `6_meses_a_menor_2_anos` (`6m-2`);
- `6_meses_a_menor_5_anos` (`6m-5`);
- `2_a_menor_5_anos` (`2-5`);
- `5_a_menor_7_anos` (`5-7`);
- `5_a_menor_10_anos` (`5-10`);
- `7_a_menor_10_anos` (`7-10`).

Faixas sobrepostas representam consultas independentes e não devem ser somadas.

## Coletar várias faixas para os dois índices

As listas da configuração podem ser ampliadas ou substituídas pela linha de comando:

```bash
python3 scripts/coletar_sisvan.py \
  --indices imc_por_idade,altura_por_idade \
  --faixas-etarias 0-5,5-10
```

Esse exemplo produz quatro bases consolidadas independentes.

## Coletar todas as faixas e criar um arquivo único

```bash
python3 scripts/coletar_sisvan.py \
  --todas-faixas \
  --arquivo-unico
```

Com os dois índices da configuração padrão, esse comando executa 18 consultas nacionais: nove faixas para IMC por idade e nove para altura por idade. Ele mantém os 18 CSVs individuais e cria também:

```text
dados/tratados/sisvan/sisvan_municipios_consultas_combinadas_2025.csv
```

O arquivo único usa formato longo. Cada linha identifica o índice, a faixa etária, a classificação nutricional, a quantidade, o percentual e o total avaliado. Isso permite reunir índices com categorias diferentes sem perder informação.

As faixas são concatenadas, nunca somadas. Como existem intervalos sobrepostos, uma mesma pessoa pode participar de mais de uma consulta.

Também é possível criar um arquivo único apenas para um índice:

```bash
python3 scripts/coletar_sisvan.py \
  --indices altura_por_idade \
  --todas-faixas \
  --arquivo-unico
```

O caminho do consolidado pode ser escolhido com `--arquivo-unico-output`.

## Simular sem consultar o SISVAN

```bash
python3 scripts/coletar_sisvan.py \
  --indices imc_por_idade,altura_por_idade \
  --faixas-etarias 0-5,5-10 \
  --dry-run
```

## Restringir a UFs durante uma validação

```bash
python3 scripts/coletar_sisvan.py --ufs RO,AC
```

Produtos parciais recebem a identificação das UFs no nome para não serem confundidos com uma base nacional.

## Validações automáticas

O coletor verifica:

- título e categorias oficiais do índice solicitado;
- código municipal SISVAN de seis dígitos;
- ausência de códigos duplicados;
- contagens não negativas;
- soma das categorias igual ao total;
- soma dos percentuais, considerando arredondamento;
- correspondência entre quantidades e percentuais;
- esquema idêntico entre as UFs;
- integridade dos arquivos brutos por SHA-256 no manifesto.

Os testes locais podem ser executados com:

```bash
python3 -m unittest discover -s tests -v
```

## Compatibilidade

A implementação anterior foi preservada em `scripts/coletar_sisvan_legado.py`. A base histórica em `data/sisvan/` também não foi modificada.
