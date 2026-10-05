# Base SISVAN — Altura por idade e peso por idade em crianças menores de 5 anos

**Produto histórico preservado, fora da análise vigente.** O notebook v3
utiliza CSVs separados de altura e peso por idade e calcula DAI/DPI na análise,
sem utilizar os indicadores derivados deste produto. A entrada de altura está
documentada em [dados/pesquisa/sisvan/README.md](../../../pesquisa/sisvan/README.md)
e a metodologia vigente em [notebooks/README.md](../../../../notebooks/README.md).
O coletor atualizado não gera mais automaticamente este produto combinado;
os comandos deste documento descrevem o comportamento histórico.

## 1. Identificação da base

**Arquivo principal:**
[`indicadores_altura_peso_idade_menores_5_2025.csv`](indicadores_altura_peso_idade_menores_5_2025.csv)

**Metadados estruturados:**
[`indicadores_altura_peso_idade_menores_5_2025.metadados.json`](indicadores_altura_peso_idade_menores_5_2025.metadados.json)

**Fonte:** [Relatório Público do SISVAN — Estado Nutricional](https://sisaps.saude.gov.br/sisvan/relatoriopublico/)

**Órgão responsável pela fonte:** Ministério da Saúde, Brasil.

**Ano de referência:** 2025.

**Data de geração do produto combinado:** 4 de outubro de 2026.

**Unidade de análise:** município.

**Abrangência:** Brasil, 27 Unidades da Federação e 5.571 municípios presentes nos relatórios do SISVAN.

**População do relatório:** crianças de 0 a menos de 5 anos acompanhadas e contabilizadas no SISVAN durante o período consultado.

Esta base não representa automaticamente todas as crianças residentes nos municípios. Ela representa a população registrada nos relatórios consultados do SISVAN.

## 2. Objetivo

A base reúne, por município, dois índices antropométricos independentes:

1. **Altura X Idade**, utilizado como indicador principal de comprometimento do crescimento;
2. **Peso X Idade**, utilizado como indicador complementar de déficit ponderal.

O arquivo também apresenta dois indicadores derivados:

- **DAI:** déficit de altura/estatura para idade;
- **DPI:** déficit de peso para idade.

Os dois indicadores não devem ser somados. Uma mesma criança pode contribuir para ambos, e os relatórios municipais agregados não permitem identificar essa interseção.

## 3. Recorte e filtros da consulta

| Parâmetro | Valor utilizado |
|---|---|
| Relatório | Estado nutricional |
| Ano | 2025 |
| Mês | Todos |
| Fase da vida | Criança |
| Faixa etária | 0 a menos de 5 anos |
| Índice 1 | Altura X Idade |
| Índice 2 | Peso X Idade |
| Agrupamento territorial | Município |
| Sexo | Todos |
| Raça/cor | Todas |
| Região de cobertura | Todas |
| Sistema de origem | Todos |
| Povo e comunidade | Todos |
| Escolaridade | Todas |

Os códigos centrais enviados ao formulário foram:

| Campo do formulário | Altura X Idade | Peso X Idade |
|---|---:|---:|
| `nu_ciclo_vida` | `1` | `1` |
| `nu_idade_inicio` | `0` | `0` |
| `nu_idade_fim` | `5` | `5` |
| `nu_indice_cri` | `3` | `1` |
| `nuAno` | `2025` | `2025` |
| `nuMes[]` | `99` — todos | `99` — todos |

Os filtros completos de cada requisição estão registrados no [manifesto de coletas](../../../../metadados/manifestos/sisvan_coletas.csv).

## 4. Origem e camadas dos dados

### 4.1 Camada bruta

Para cada índice foram preservados 27 arquivos XLSX oficiais, um por UF, sem alteração do conteúdo:

- [XLSX de Altura X Idade](../../../brutos/sisvan/altura_por_idade/0_a_menor_5_anos/2025/ufs/);
- [XLSX de Peso X Idade](../../../brutos/sisvan/peso_por_idade/0_a_menor_5_anos/2025/ufs/).

Os arquivos brutos constituem a reprodução fiel da fonte. Seus hashes SHA-256, filtros, horários de coleta e quantidade de registros estão no manifesto.

### 4.2 Consolidados individuais

Os XLSX estaduais foram validados e consolidados nacionalmente em duas bases independentes:

- [Altura X Idade](../altura_por_idade/sisvan_municipios_altura_por_idade_0_a_menor_5_anos_2025.csv);
- [Peso X Idade](../peso_por_idade/sisvan_municipios_peso_por_idade_0_a_menor_5_anos_2025.csv).

Nesses CSVs, o cabeçalho de dois níveis do XLSX foi achatado. `Quantidade` e `%` foram incorporados ao nome da respectiva categoria. Os valores e a grafia das categorias permanecem os fornecidos pelo SISVAN.

### 4.3 Produto combinado e derivado

O arquivo principal desta pasta combina os dois consolidados por `Código IBGE` e calcula DAI e DPI. Portanto, ele é um **produto derivado**, não uma exportação original do SISVAN.

Nenhuma junção foi realizada apenas pelo nome do município.

## 5. Fórmulas

### 5.1 Déficit de peso para idade — DPI

Quantidade:

\[
DPI_N = N(\text{Peso Muito Baixo para a Idade})
+ N(\text{Peso Baixo para a Idade})
\]

Percentual:

\[
DPI(\%) =
\frac{DPI_N}
{N(\text{avaliados em Peso X Idade})}
\times 100
\]

### 5.2 Déficit de altura/estatura para idade — DAI

Quantidade:

\[
DAI_N = N(\text{Altura Muito Baixa para a Idade})
+ N(\text{Altura Baixa para a Idade})
\]

Percentual:

\[
DAI(\%) =
\frac{DAI_N}
{N(\text{avaliados em Altura X Idade})}
\times 100
\]

Os percentuais derivados são arredondados para duas casas decimais. Quando o denominador é zero, o percentual derivado é registrado como `0.0` para evitar divisão por zero; o município deve ser tratado como sem observações, e não como prevalência comprovadamente nula.

## 6. Denominadores

Cada índice possui seu próprio denominador:

- DAI usa `Total avaliado - Altura X Idade`;
- DPI usa `Total avaliado - Peso X Idade`.

Na base nacional, os denominadores diferem em 181 municípios. Por isso:

- não substituir os dois totais por uma coluna única;
- não calcular DAI usando o total de Peso X Idade;
- não calcular DPI usando o total de Altura X Idade;
- não somar os totais dos dois índices, pois eles podem representar as mesmas crianças.

## 7. Dicionário de dados

### 7.1 Identificação e território

| Coluna | Tipo recomendado | Origem | Descrição |
|---|---|---|---|
| `Fase da vida` | texto | Acrescentada a partir do filtro | Sempre `CRIANÇA` nesta base |
| `Faixa etária` | texto | Acrescentada a partir do filtro | Sempre `0 a < 5 anos` |
| `Ano` | inteiro | Acrescentada a partir do filtro | Ano de referência do relatório |
| `Região` | texto | SISVAN | Grande região do município |
| `Código UF` | texto | SISVAN | Código da Unidade da Federação com dois dígitos |
| `UF` | texto | SISVAN | Sigla da Unidade da Federação |
| `Código IBGE` | texto | SISVAN | Código municipal de seis dígitos utilizado no relatório |
| `Município` | texto | SISVAN | Nome municipal apresentado pelo SISVAN |

`Código IBGE` deve ser lido como texto. Antes de integrar com uma fonte que utilize código municipal de sete dígitos, é obrigatório harmonizar explicitamente os formatos e validar a correspondência.

### 7.2 Altura X Idade

| Coluna | Tipo recomendado | Origem | Descrição |
|---|---|---|---|
| `Altura Muito Baixa para a Idade - Quantidade` | inteiro | SISVAN | Número na categoria oficial de maior gravidade |
| `Altura Muito Baixa para a Idade - %` | texto percentual | SISVAN | Percentual oficial da categoria |
| `Altura Baixa para a Idade - Quantidade` | inteiro | SISVAN | Número na categoria oficial de altura baixa |
| `Altura Baixa para a Idade - %` | texto percentual | SISVAN | Percentual oficial da categoria |
| `Altura Adequada para a Idade - Quantidade` | inteiro | SISVAN | Número na categoria oficial de altura adequada |
| `Altura Adequada para a Idade - %` | texto percentual | SISVAN | Percentual oficial da categoria |
| `Déficit de estatura - Quantidade` | inteiro | Calculada | Soma das duas categorias de déficit de altura |
| `Déficit de estatura - %` | decimal | Calculada | DAI, usando o total de Altura X Idade |
| `Total avaliado - Altura X Idade` | inteiro | SISVAN, renomeada | Coluna `Total` do relatório de Altura X Idade |

### 7.3 Peso X Idade

| Coluna | Tipo recomendado | Origem | Descrição |
|---|---|---|---|
| `Peso Muito Baixo para a Idade - Quantidade` | inteiro | SISVAN | Número na categoria oficial de maior gravidade |
| `Peso Muito Baixo para a Idade - %` | texto percentual | SISVAN | Percentual oficial da categoria |
| `Peso Baixo para a Idade - Quantidade` | inteiro | SISVAN | Número na categoria oficial de peso baixo |
| `Peso Baixo para a Idade - %` | texto percentual | SISVAN | Percentual oficial da categoria |
| `Peso Adequado ou Eutrófico - Quantidade` | inteiro | SISVAN | Número na categoria oficial de peso adequado |
| `Peso Adequado ou Eutrófico - %` | texto percentual | SISVAN | Percentual oficial da categoria |
| `Peso Elevado para a Idade - Quantidade` | inteiro | SISVAN | Número na categoria oficial de peso elevado |
| `Peso Elevado para a Idade - %` | texto percentual | SISVAN | Percentual oficial da categoria |
| `Déficit de peso para idade - Quantidade` | inteiro | Calculada | Soma das duas categorias de déficit de peso |
| `Déficit de peso para idade - %` | decimal | Calculada | DPI, usando o total de Peso X Idade |
| `Total avaliado - Peso X Idade` | inteiro | SISVAN, renomeada | Coluna `Total` do relatório de Peso X Idade |

## 8. Colunas originais, transformadas e calculadas

Nem todas as colunas do arquivo combinado são originais da fonte:

- **Originais do SISVAN:** território, quantidades e percentuais das categorias oficiais;
- **Originais com nome desambiguado:** os dois campos `Total`, renomeados para identificar o índice de origem;
- **Acrescentadas a partir dos filtros:** `Fase da vida`, `Faixa etária` e `Ano`;
- **Calculadas:** quantidade e percentual de DAI e DPI.

O SISVAN não fornece os dois índices em uma única exportação. Consequentemente, qualquer arquivo que os apresente lado a lado é necessariamente um produto de integração.

## 9. Formato técnico do arquivo

| Característica | Valor |
|---|---|
| Formato | CSV |
| Codificação | UTF-8 com BOM (`utf-8-sig`) |
| Separador | Vírgula |
| Cabeçalho | Uma linha |
| Linhas de dados | 5.571 |
| Colunas | 28 |
| Chave esperada | `Código IBGE` |
| Ordenação | Código municipal crescente |

Os percentuais oficiais do SISVAN são preservados como texto e podem conter `%` ou `-` para representar zero. Os percentuais derivados de DAI e DPI são numéricos, sem o caractere `%`.

## 10. Controles de qualidade executados

O processamento verificou:

- 27 arquivos XLSX por índice;
- título oficial correspondente ao índice solicitado;
- categorias e ordem das colunas oficiais;
- código municipal de seis dígitos;
- ausência de municípios duplicados em cada consulta;
- contagens inteiras e não negativas;
- soma das categorias igual ao total de cada índice;
- correspondência entre quantidades e percentuais oficiais, considerando arredondamento;
- esquema idêntico entre UFs;
- mesma cobertura municipal entre os dois consolidados;
- identidade territorial compatível antes da junção;
- DAI e DPI iguais à soma de seus componentes;
- percentuais derivados compatíveis com seus denominadores.

Resultados dos controles:

| Controle | Resultado |
|---|---:|
| Municípios | 5.571 |
| Códigos municipais únicos | 5.571 |
| UFs | 27 |
| Municípios com total zero em Altura X Idade | 1 |
| Municípios com total zero em Peso X Idade | 1 |
| Municípios com denominadores diferentes entre os índices | 181 |

O município com total zero nos dois índices é `BOA ESPERANCA DO NORTE`, MT, código SISVAN/IBGE de seis dígitos `510183`. Seus percentuais derivados não devem ser interpretados como estimativas de prevalência.

### 10.1 Totais nacionais de controle

Estes valores servem para conferir reproduções da base; não representam automaticamente estimativas para toda a população residente:

| Medida | Valor de controle |
|---|---:|
| Total contabilizado — Altura X Idade | 7.846.413 |
| DAI — quantidade | 877.708 |
| DAI — razão agregada | 11,19% |
| Total contabilizado — Peso X Idade | 7.846.386 |
| DPI — quantidade | 266.641 |
| DPI — razão agregada | 3,40% |

As razões agregadas foram calculadas como soma dos numeradores dividida pela soma dos respectivos denominadores. Elas não são médias simples dos percentuais municipais.

## 11. Interpretação metodológica

### 11.1 DAI

O déficit de altura/estatura para idade é utilizado como sinal de comprometimento do crescimento. Nesta pesquisa, é o desfecho nutricional principal para examinar sua coexistência territorial com vulnerabilidade social.

DAI não mede diretamente insegurança alimentar domiciliar e não demonstra causalidade entre vulnerabilidade social e crescimento infantil.

### 11.2 DPI

O déficit de peso para idade é um indicador complementar. Peso baixo para idade pode refletir baixa estatura, baixo peso corporal ou ambos; portanto, não deve ser interpretado isoladamente como magreza aguda.

`Peso Elevado para a Idade` não equivale automaticamente a sobrepeso ou obesidade. Para investigar especificamente a relação entre peso e altura, devem ser considerados índices como Peso X Altura ou IMC X Idade.

### 11.3 Relação entre DAI e DPI

DAI e DPI podem coexistir na mesma criança. Como esta base é municipal e agregada:

- não é possível identificar indivíduos;
- não é possível calcular a interseção entre DAI e DPI;
- não é possível somar DAI e DPI para obter um total de crianças com “qualquer déficit”;
- não se deve subtrair um indicador do outro.

## 12. Limitações

1. **Cobertura:** o SISVAN não representa necessariamente todas as crianças residentes. Diferenças entre municípios podem refletir tanto condições nutricionais quanto cobertura e capacidade de registro.
2. **Denominadores pequenos:** municípios com poucos registros podem apresentar percentuais instáveis ou extremos.
3. **Período anual:** a base utiliza todos os meses de 2025. Deve-se evitar afirmar unicidade individual além do que a metodologia oficial do relatório garantir.
4. **Dados agregados:** não há microdados nem identificadores individuais; não é possível ajustar resultados por características individuais nem identificar sobreposição entre classificações.
5. **Inferência causal:** associações territoriais com IVS, IDHM ou CadÚnico não demonstram causalidade.
6. **Compatibilidade temporal:** a comparação com outras fontes deve considerar o ano de referência de cada indicador.
7. **Município sem observações:** Boa Esperança do Norte possui total zero e deve ser tratado explicitamente como ausência de observações na análise.
8. **Código territorial:** a base utiliza código de seis dígitos; outras fontes podem empregar sete dígitos ou malhas territoriais de anos diferentes.

## 13. Recomendações para análise

- utilizar `Código IBGE` como chave, nunca apenas o nome municipal;
- manter DAI e DPI como desfechos separados;
- apresentar quantidade e denominador junto com cada percentual;
- definir e justificar um denominador mínimo para comparações municipais;
- mapear a cobertura do SISVAN sempre que houver denominador demográfico compatível;
- realizar análise de sensibilidade excluindo municípios com denominadores pequenos;
- ao agregar municípios, somar numeradores e denominadores e recalcular o percentual;
- não calcular média simples dos percentuais municipais para obter resultados estaduais, regionais ou nacionais;
- documentar harmonizações de códigos territoriais e perdas de correspondência;
- distinguir ausência de registros, valor zero e dado não aplicável;
- usar linguagem como “crianças contabilizadas no SISVAN” quando a unicidade ou representatividade populacional não estiver demonstrada.

## 14. Integração com IVS, IDHM e CadÚnico

Antes de integrar esta base às fontes sociais:

1. harmonizar o código municipal e a malha territorial;
2. registrar o ano de cada variável;
3. conferir municípios sem correspondência;
4. preservar os denominadores de DAI e DPI;
5. acrescentar medidas de cobertura quando disponíveis;
6. avaliar separadamente quantidade absoluta, prevalência e cobertura;
7. evitar interpretar correlação espacial como relação causal.

Uma tabela de controle da integração deve registrar número de municípios antes e depois da junção, correspondências, perdas e duplicidades.

## 15. Reprodutibilidade

### 15.1 Código e configuração

O processamento foi executado pelo script [`scripts/coletar_sisvan.py`](../../../../scripts/coletar_sisvan.py), especialmente pela função `write_under5_growth_product()`.

Configuração utilizada: [`configuracoes/sisvan/coletas.json`](../../../../configuracoes/sisvan/coletas.json).

Versão do código:

```text
commit e96618c
```

Comando executado na raiz do projeto:

```bash
python scripts/coletar_sisvan.py
```

Para reproduzir a partir dos XLSX já preservados, não utilizar `--force`. O coletor reutilizará os arquivos brutos e verificará seus hashes no manifesto. `--force` realiza novas consultas ao portal e pode obter uma versão atualizada da fonte.

### 15.2 Ambiente utilizado

```text
Python 3.13.12
openpyxl 3.1.5
requests 2.32.5
urllib3 2.6.3
```

### 15.3 Hashes SHA-256

```text
Altura X Idade:
6b05265e6080e3f32dc3de6452d15e056cb9b048e3466bbe35c1df3c455ac190

Peso X Idade:
7ba94bd20f51dd8edae9f44c872c9596631d28226afadb0c55d62950d9148d09

Arquivo combinado:
21aa902b60fd5f08b1109f95a1c7e9a635a937fc96661fb57fe2519dcca9a92d
```

O arquivo `.metadados.json` contém um horário de geração. Uma nova execução pode alterar o hash desse arquivo de metadados mesmo quando o conteúdo tabular permanecer igual.

## 16. Sugestão de descrição para a metodologia da pesquisa

> Foram utilizados dados municipais do Relatório Público do Sistema de Vigilância Alimentar e Nutricional (SISVAN), referentes a crianças de 0 a menos de 5 anos acompanhadas em 2025. Foram extraídos separadamente os índices Altura X Idade e Peso X Idade para as 27 Unidades da Federação, com agrupamento municipal e demais filtros abrangendo todas as categorias disponíveis. O déficit de altura para idade foi calculado pela soma das classificações “Altura Muito Baixa para a Idade” e “Altura Baixa para a Idade”, dividida pelo total avaliado no respectivo índice. O déficit de peso para idade foi calculado pela soma de “Peso Muito Baixo para a Idade” e “Peso Baixo para a Idade”, dividida pelo total avaliado em Peso X Idade. Os denominadores foram mantidos separadamente e os dois déficits não foram somados, pois os relatórios agregados não permitem identificar sua sobreposição individual.

## 17. Sugestão de referência da base

> BRASIL. Ministério da Saúde. Sistema de Vigilância Alimentar e Nutricional — SISVAN. Relatório público do estado nutricional: crianças de 0 a menos de 5 anos, Altura X Idade e Peso X Idade, ano de referência 2025. Extração de Altura X Idade em 30 set. 2026; extração de Peso X Idade em 4 out. 2026. Processamento municipal reproduzível pelo projeto *Áreas de risco alimentar e vulnerabilidade social*.

Adapte a referência às normas bibliográficas exigidas pela instituição e registre também a data de acesso ao portal.
