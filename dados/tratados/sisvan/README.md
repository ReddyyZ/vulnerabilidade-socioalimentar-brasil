# Bases do SISVAN

Esta pasta contém os produtos consolidados da coleta municipal do Relatório Público do SISVAN. Os arquivos oficiais originais são preservados separadamente em `dados/brutos/sisvan/`.

A documentação do produto histórico combinado de crianças menores de 5 anos está em
[`criancas_menores_5/README.md`](criancas_menores_5/README.md). Esse produto derivado
não é gerado automaticamente nem utilizado como entrada do notebook v3.

## Recorte padrão

A configuração padrão está em `configuracoes/sisvan/coletas.json` e coleta:

- ano: 2025;
- abrangência: todos os municípios, uma requisição por UF;
- fase da vida: criança;
- faixa etária: 0 a menos de 5 anos;
- índices: altura por idade e peso por idade;
- sexo, raça/cor, origem, povo/comunidade e escolaridade: todos.

Esse padrão atende às duas entradas nutricionais do notebook v3. DAI, DPI e
o mínimo de avaliações são calculados/aplicados somente na análise.

## Produtos nacionais já preservados

- `imc_por_idade/sisvan_municipios_imc_por_idade_0_a_menor_5_anos_2025.csv`;
- `altura_por_idade/sisvan_municipios_altura_por_idade_0_a_menor_5_anos_2025.csv`;
- `peso_por_idade/sisvan_municipios_peso_por_idade_0_a_menor_5_anos_2025.csv`;
- `sisvan_municipios_consultas_combinadas_2025.csv`, em formato longo.

Esses arquivos anteriores de IMC permanecem preservados. Uma nova execução da
configuração padrão passa a gerar:

- `altura_por_idade/sisvan_municipios_altura_por_idade_0_a_menor_5_anos_<ano>.csv`;
- `peso_por_idade/sisvan_municipios_peso_por_idade_0_a_menor_5_anos_<ano>.csv`.

Cada CSV possui um arquivo `.metadados.json` correspondente, com os parâmetros da consulta, colunas, UFs e estatísticas de validação.

Os CSVs individuais por índice são consolidações dos relatórios estaduais. O
processo atual apenas achata o cabeçalho de dois níveis e reúne as UFs,
preservando os valores das células e os percentuais oficiais, sem normalizar
escalas ou acrescentar DAI/DPI. Os indicadores nutricionais são calculados
no notebook; os produtos derivados históricos permanecem preservados.

## Camada bruta

Cada resposta oficial é mantida sem alteração:

```text
dados/brutos/sisvan/
├── altura_por_idade/<faixa>/<ano>/ufs/<UF>.xlsx
├── peso_por_idade/<faixa>/<ano>/ufs/<UF>.xlsx
└── imc_por_idade/<faixa>/<ano>/ufs/<UF>.xlsx  # preservado/opcional
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

A execução padrão gera **dois CSVs separados**, com todas as categorias
oficiais e `Total` de cada relatório, além dos respectivos metadados. Não gera
automaticamente uma base combinada, DAI, DPI ou filtragem por mínimo de avaliações.
As opções explícitas de concatenação, soma de faixas e harmonização continuam
disponíveis; esses produtos são adicionais e não substituem os CSVs individuais.

Para consultar somente um indicador, usar `--indices altura_por_idade` ou
`--indices peso_por_idade`. Uma nova coleta não atualiza automaticamente o
pacote de dados incorporado no notebook v3; isso exige uma etapa separada.

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
  --indices altura_por_idade,peso_por_idade \
  --faixas-etarias 0-5,5-10
```

Esse exemplo produz quatro bases consolidadas independentes.

Para também somar essas faixas em um arquivo por índice:

```bash
python3 scripts/coletar_sisvan.py \
  --indices altura_por_idade,peso_por_idade \
  --faixas-etarias 0-5,5-10 \
  --somar-faixas
```

O coletor verifica a interseção dos intervalos antes de consultar o portal. A
operação é interrompida se duas faixas se sobrepuserem. Os percentuais dos
arquivos somados são recalculados com o total combinado; percentuais nunca são
somados nem submetidos a média simples.

A seleção infantil completa, sem sobreposição, também possui um atalho:

```bash
python3 scripts/coletar_sisvan.py \
  --indices altura_por_idade,peso_por_idade \
  --todas-idades-infantis \
  --somar-faixas
```

## Coletar outras fases da vida

As combinações implementadas, conforme o formulário oficial, são:

| Fase | Índices disponíveis | Faixa de referência |
|---|---|---|
| Criança | `altura_por_idade`, `peso_por_idade`, `imc_por_idade` | faixas oficiais entre 0 e menos de 10 anos |
| Adolescente | `imc_por_idade`, `altura_por_idade` | 10 a menos de 20 anos |
| Adulto | `imc` | 20 a menos de 60 anos |
| Idoso | `imc` | 60 anos ou mais |
| Gestante | `imc_por_semana_gestacional` | todas as idades gestacionais |

Exemplo de coleta do IMC por idade de adolescentes:

```bash
python3 scripts/coletar_sisvan.py \
  --fases adolescente \
  --indices imc_por_idade
```

O XLSX bruto mantém os nomes exatos devolvidos pelo SISVAN. Por exemplo,
`Obesidade grave (5-10 anos)`, `Obesidade Grave` e `Obesidade Grau III` são
categorias distintas de criança, adolescente e adulto e não são renomeadas na
camada de origem.

## Construir a visão geral da população acompanhada

```bash
python3 scripts/coletar_sisvan.py --populacao-geral
```

Esse comando seleciona automaticamente recortes etariamente exclusivos:

- crianças de `0 a < 5` e `5 a < 10`;
- adolescentes de `10 a < 20`;
- adultos de `20 a < 60`;
- idosos de `60 anos ou mais`.

Ele gera:

```text
dados/tratados/sisvan/
├── por_fase/<fase>_categorias_oficiais_<ano>.csv
├── harmonizados/<fase>_harmonizado_<ano>.csv
└── populacao_geral/estado_nutricional_populacao_geral_<ano>.csv
```

O mapeamento analítico utilizado está versionado em
`configuracoes/sisvan/harmonizacao_v1.json`. Na base geral, `Magreza
acentuada`, `Magreza` e `Baixo peso` permanecem em campos separados e formam,
sem dupla soma, o `Déficit nutricional total`. Os denominadores próprios desses
componentes também são preservados em colunas explícitas.

Para coletar gestantes na mesma execução, mas mantê-las fora da soma geral:

```bash
python3 scripts/coletar_sisvan.py \
  --populacao-geral \
  --incluir-gestantes
```

O produto é gravado em `gestantes/estado_nutricional_gestantes_<ano>.csv`.
Gestantes nunca são incluídas no total geral.

Esses produtos representam pessoas contabilizadas nas consultas do SISVAN, e
não toda a população residente. Em consulta anual, uma pessoa que muda de fase
pode aparecer em mais de uma extração; por isso, os metadados não afirmam
unicidade individual.

## Coletar todas as faixas e criar um arquivo único

```bash
python3 scripts/coletar_sisvan.py \
  --todas-faixas \
  --arquivo-unico
```

Com os dois índices da configuração padrão, esse comando executa 18 consultas
nacionais: nove faixas para altura por idade e nove para peso por idade. Ele
mantém os 18 CSVs individuais e cria também:

```text
dados/tratados/sisvan/sisvan_municipios_consultas_combinadas_2025.csv
```

O arquivo único usa formato longo. Cada linha identifica o índice, a faixa etária, a classificação nutricional, a quantidade, o percentual e o total avaliado. Isso permite reunir índices com categorias diferentes sem perder informação.

As faixas são concatenadas, nunca somadas. Como existem intervalos sobrepostos,
uma mesma pessoa pode participar de mais de uma consulta. A combinação de
`--todas-faixas` com `--somar-faixas` é rejeitada.

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
  --indices altura_por_idade,peso_por_idade \
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
- integridade dos arquivos brutos por SHA-256 no manifesto;
- ausência de sobreposição antes de somar faixas;
- cobertura municipal idêntica entre bases que serão combinadas;
- correspondência integral com o dicionário de harmonização;
- partição dos grupos harmonizados igual ao total;
- déficit total igual a magreza acentuada + magreza + baixo peso;
- exclusão de gestantes da população geral;
- manutenção de denominadores separados para altura por idade e peso por idade;
- déficit de estatura e déficit de peso nunca somados entre si.

Os testes locais podem ser executados com:

```bash
python3 -m unittest discover -s tests -v
```

## Compatibilidade

A implementação anterior foi preservada em `scripts/coletar_sisvan_legado.py`. A base histórica em `data/sisvan/` também não foi modificada.
