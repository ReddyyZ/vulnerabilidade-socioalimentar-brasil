# Decisão metodológica: agregação etária e visão geral da população no SISVAN

- **Status:** aprovada; implementação pendente
- **Data da decisão:** 30 de setembro de 2026
- **Escopo:** crianças, adolescentes, adultos e idosos acompanhados pelo SISVAN; gestantes em produto separado

## 1. Objetivo

Ampliar a coleta para todas as fases da vida compatíveis com uma visão geral do estado nutricional da população acompanhada pelo SISVAN e permitir que o usuário:

1. selecione faixas etárias oficiais;
2. some faixas mutuamente exclusivas por município;
3. preserve uma base com as classificações oficiais de cada fase;
4. produza uma classificação harmonizada entre as fases da vida;
5. consulte quantidades e percentuais municipais independentemente da idade.

A base geral deverá responder, com as limitações registradas neste documento:

> Quantas pessoas acompanhadas pelo SISVAN apresentam déficit nutricional, estado nutricional adequado, risco para excesso de peso ou excesso de peso em cada município?

## 2. Níveis de informação que serão preservados

A arquitetura terá quatro níveis complementares:

1. **Arquivos brutos:** respostas oficiais preservadas sem alteração;
2. **Bases oficiais por consulta:** um arquivo para cada fase, índice, faixa e período;
3. **Bases harmonizadas por fase:** classificações oficiais convertidas em grupos comparáveis;
4. **Base geral harmonizada:** soma municipal de crianças, adolescentes, adultos e idosos.

As categorias oficiais de fases diferentes não serão simplesmente misturadas em uma única tabela larga. A soma entre fases ocorrerá somente depois da harmonização documentada.

## 3. Preservação dos dados originais

A nova funcionalidade não alterará arquivos brutos nem consolidados individuais já produzidos.

Para cada consulta deverão continuar existindo:

- o XLSX oficial de cada UF, preservado sem alteração;
- a entrada correspondente no manifesto;
- o CSV municipal da combinação de fase, índice, faixa etária e ano;
- os metadados completos da consulta.

Qualquer soma ou harmonização será identificada como produto derivado. Nenhuma dessas bases poderá ser apresentada como exportação original do SISVAN.

## 4. População incluída na visão geral

A visão geral será formada por fases da vida etariamente exclusivas:

| Fase | Intervalo etário de referência | Papel na base geral |
|---|---:|---|
| Criança | 0 a menos de 10 anos | Incluída |
| Adolescente | 10 a menos de 20 anos | Incluída |
| Adulto | 20 a menos de 60 anos | Incluída |
| Idoso | 60 anos ou mais | Incluída |
| Gestante | Condição fisiológica específica | Mantida separada |

Os códigos, limites e nomes efetivamente enviados ao sistema deverão ser validados contra o formulário oficial antes da implementação. Uma mudança no SISVAN deverá interromper a coleta em vez de ser interpretada silenciosamente.

Neste projeto, “todas as faixas” passará a ter dois significados explícitos:

- **todas as faixas infantis:** cobertura de 0 a menos de 10 anos sem sobreposição;
- **população geral:** crianças, adolescentes, adultos e idosos, sem incluir gestantes na soma.

Não significará somar indiscriminadamente todas as opções existentes no formulário.

## 5. Tratamento das gestantes

Gestantes serão coletadas e analisadas em uma base própria porque:

- a avaliação nutricional depende da condição e do período gestacional;
- suas classificações não são diretamente equivalentes às demais fases;
- uma gestante também pertence etariamente à população adulta ou adolescente;
- incluí-la na base geral pode provocar dupla contagem.

A base de gestantes poderá ser apresentada ao lado da visão geral, mas não participará de seu total municipal.

## 6. Seleção e soma de faixas dentro de uma fase

Somente faixas etárias mutuamente exclusivas poderão ser somadas.

Exemplo válido:

```text
0 a < 6 meses
+ 6 meses a < 2 anos
+ 2 a < 5 anos
```

Exemplo inválido:

```text
0 a < 5 anos
+ 2 a < 5 anos
```

No exemplo inválido, as crianças de 2 a menos de 5 anos seriam contadas duas vezes.

Antes da coleta ou agregação, o sistema deverá converter os limites para uma unidade comparável e verificar a interseção entre todos os intervalos selecionados. Qualquer sobreposição deverá interromper a operação com uma mensagem clara.

Faixas contíguas, nas quais o fim de uma coincide com o início da seguinte, são válidas porque o limite superior é aberto.

### 6.1 Todas as idades infantis

Para cobrir a fase infantil de modo eficiente, a combinação padrão será:

```text
0 a < 5 anos
+ 5 a < 10 anos
```

Essa combinação cobre a fase infantil uma única vez e exige apenas duas consultas por índice. As nove combinações disponíveis no formulário não serão somadas conjuntamente, pois várias se sobrepõem.

## 7. Método de soma por município

Para cada município, grupo nutricional e recorte selecionado, as quantidades e os totais serão somados.

Seja:

- `m`: município;
- `c`: classificação ou grupo nutricional;
- `f`: faixa ou fase selecionada;
- `Q(m,c,f)`: quantidade registrada na classificação;
- `T(m,f)`: total de pessoas avaliadas.

A quantidade combinada será:

```text
Q_combinada(m,c) = soma de Q(m,c,f) nos recortes selecionados
```

O total combinado será:

```text
T_combinado(m) = soma de T(m,f) nos recortes selecionados
```

O percentual será recalculado:

```text
Percentual_combinado(m,c) =
Q_combinada(m,c) / T_combinado(m) × 100
```

Os percentuais oficiais nunca serão somados nem será utilizada sua média simples.

Quando o total for zero, o resultado deverá seguir uma representação documentada e consistente, sem divisão por zero.

## 8. Indicador transversal para a população geral

A visão geral utilizará o indicador baseado em IMC apropriado a cada fase:

- IMC por idade para crianças;
- IMC por idade para adolescentes;
- IMC e classificação própria para adultos;
- IMC e classificação própria para idosos.

Os pontos de corte continuam sendo específicos de cada fase. A harmonização não transforma essas classificações em uma única medida clínica; ela cria grupos analíticos amplos para permitir uma visão territorial agregada.

Os nomes e códigos dos índices deverão ser obtidos do SISVAN e registrados no manifesto de cada consulta.

## 9. Categorias oficiais por fase

Antes da harmonização será produzida uma base por fase contendo exatamente as classificações oficiais retornadas pelo sistema.

Regras:

- nenhuma categoria oficial será renomeada na camada de origem;
- diferenças de nomenclatura entre as fases serão preservadas;
- a soma de categorias oficiais ocorrerá apenas dentro de consultas compatíveis;
- os metadados indicarão fase, índice, faixa, período e filtros;
- alterações de cabeçalho interromperão o processamento para revisão.

Isso permitirá auditar cada valor da base geral até sua categoria e consulta de origem.

## 10. Harmonização das classificações nutricionais

A base harmonizada utilizará quatro grupos gerais:

| Grupo harmonizado | Categorias conceituais de origem |
|---|---|
| Déficit nutricional | Magreza acentuada, magreza e classificações de baixo peso |
| Estado nutricional adequado | Eutrofia e classificações de peso adequado |
| Risco para excesso de peso | Categoria de risco utilizada em faixas infantis, quando existente |
| Excesso de peso | Sobrepeso e todas as categorias ou graus de obesidade |

A correspondência exata será registrada em um dicionário versionado. Somente categorias confirmadas nos cabeçalhos oficiais poderão entrar no mapeamento.

### 10.1 Detalhamento do déficit nutricional

`Magreza acentuada` será preservada separadamente de `Magreza`. Entretanto, essas classificações não estão disponíveis em todas as fases da vida:

| Componente | Fases contribuintes |
|---|---|
| Magreza acentuada | Crianças e adolescentes |
| Magreza | Crianças e adolescentes |
| Baixo peso | Adultos e idosos |
| Baixo peso gestacional | Gestantes, exclusivamente na base separada |

A base harmonizada da população geral utilizará uma estrutura hierárquica:

```text
Déficit nutricional total
├── Magreza acentuada — crianças e adolescentes
├── Magreza — crianças e adolescentes
└── Baixo peso — adultos e idosos
```

O valor harmonizado será calculado por município como:

```text
Déficit nutricional total =
Magreza acentuada
+ Magreza
+ Baixo peso
```

Regras obrigatórias:

- `Magreza acentuada` e `Magreza` permanecerão em campos distintos;
- `Baixo peso` não será convertido artificialmente em magreza ou magreza acentuada;
- o déficit total será o indicador comparável entre todas as fases;
- os três componentes serão detalhamentos do déficit total e não categorias adicionais a serem somadas novamente;
- a fase contribuinte de cada componente será registrada nos metadados;
- em uma base específica de adultos ou idosos, magreza e magreza acentuada serão marcadas como não aplicáveis, e não como ausência de casos;
- gestantes não contribuirão para o déficit total da população geral.

O percentual de déficit nutricional total utilizará como denominador o total combinado de crianças, adolescentes, adultos e idosos. Percentuais detalhados de magreza acentuada e magreza deverão usar o total de crianças e adolescentes como denominador; o percentual detalhado de baixo peso deverá usar o total de adultos e idosos. Os nomes das colunas e os metadados deverão explicitar esses denominadores.

Essa estrutura permite conhecer o número de pessoas em cada componente sem afirmar que `Magreza acentuada` é uma classificação disponível para toda a população.

### 10.2 Regra para risco de sobrepeso

`Risco de sobrepeso` permanecerá separado de `Excesso de peso`. Essa escolha evita classificar como excesso uma categoria de risco específica de crianças pequenas.

Na base geral:

- o grupo poderá receber valores apenas da fase em que existe;
- zero significará ausência de registros naquela categoria;
- não será interpretado como uma categoria aplicável igualmente a todas as idades.

### 10.3 Categorias inesperadas

Se uma consulta retornar uma categoria sem correspondência aprovada:

1. a base oficial da fase poderá ser preservada;
2. a harmonização deverá ser interrompida;
3. a categoria deverá ser revisada metodologicamente;
4. o dicionário só poderá ser alterado de forma explícita e documentada.

Não haverá inferência automática de equivalências.

## 11. Altura por idade

Altura por idade não fará parte da base harmonizada da população geral porque não é um indicador aplicável de modo equivalente a adultos e idosos.

Ela permanecerá como dimensão específica de crescimento para:

- crianças, com prioridade para o déficit de estatura em menores de 5 anos;
- adolescentes, caso a pesquisa decida incluir essa análise complementar.

Para crianças, as classificações previstas são:

- Altura Muito Baixa para a Idade;
- Altura Baixa para a Idade;
- Altura Adequada para a Idade.

As quantidades poderão ser somadas apenas entre faixas compatíveis e não sobrepostas, depois da validação dos cabeçalhos oficiais.

## 12. Produtos esperados

A estrutura conceitual dos produtos será:

```text
dados/tratados/sisvan/
├── por_fase/
│   ├── criancas_categorias_oficiais_<ano>.csv
│   ├── adolescentes_categorias_oficiais_<ano>.csv
│   ├── adultos_categorias_oficiais_<ano>.csv
│   └── idosos_categorias_oficiais_<ano>.csv
├── harmonizados/
│   ├── criancas_harmonizado_<ano>.csv
│   ├── adolescentes_harmonizado_<ano>.csv
│   ├── adultos_harmonizado_<ano>.csv
│   └── idosos_harmonizado_<ano>.csv
├── populacao_geral/
│   └── estado_nutricional_populacao_geral_<ano>.csv
├── altura_por_idade/
│   └── altura_faixas_somadas_<ano>.csv
└── gestantes/
    └── estado_nutricional_gestantes_<ano>.csv
```

Os nomes definitivos deverão identificar:

- fase ou população geral;
- índice;
- ano;
- faixas participantes;
- categorias oficiais ou harmonizadas;
- abrangência nacional ou parcial.

Cada produto deverá possuir metadados próprios e referências aos arquivos que contribuíram para sua geração.

## 13. Validações obrigatórias

Antes de qualquer soma, verificar:

- fase, índice, período, abrangência e filtros de cada consulta;
- ausência de sobreposição entre faixas da mesma fase;
- exclusão de gestantes da soma geral;
- presença de cada município no máximo uma vez por consulta;
- compatibilidade dos códigos territoriais;
- quantidades e totais inteiros e não negativos;
- correspondência dos cabeçalhos com o esquema oficial esperado;
- soma das categorias oficiais igual ao total da consulta;
- cobertura completa ou ausência documentada de municípios;
- correspondência explícita de cada categoria com o dicionário harmonizado;
- soma dos grupos harmonizados igual ao total, quando formarem uma partição completa;
- déficit nutricional total igual à soma de magreza acentuada, magreza e baixo peso;
- ausência de dupla soma entre o déficit total e seus componentes;
- uso do denominador próprio de cada componente detalhado;
- consistência dos percentuais recalculados;
- rastreabilidade até os arquivos brutos.

## 14. Risco de duplicação entre fases

Faixas etárias exclusivas eliminam a sobreposição conceitual, mas não garantem por si só que uma pessoa não seja contabilizada em duas consultas agregadas durante um período anual.

Uma pessoa pode mudar de fase ao completar 10, 20 ou 60 anos durante o ano. A soma só poderá ser descrita como número de pessoas distintas se a metodologia do relatório público garantir uma única contribuição por indivíduo no período, independentemente da fase consultada.

Antes de usar essa interpretação, a implementação deverá:

1. confirmar como o relatório escolhe o acompanhamento de cada indivíduo;
2. registrar essa regra nos metadados;
3. avaliar a utilização de um período mensal se a consulta anual não permitir deduplicação;
4. usar linguagem mais cautelosa, como “pessoas contabilizadas nas consultas”, enquanto a unicidade não estiver comprovada.

Essa limitação não poderá ser omitida dos resultados da pesquisa.

## 15. Limites de representatividade

A base geral representará a população acompanhada e registrada pelo SISVAN, não toda a população residente no município.

Os resultados deverão ser apresentados com:

- total de avaliados ou contabilizados;
- cobertura do SISVAN, quando for possível calculá-la;
- denominadores demográficos compatíveis por fase;
- indicação de municípios com poucos registros;
- ressalva sobre diferenças locais de cobertura e capacidade de registro.

A comparação entre municípios não deverá usar apenas contagens absolutas. Quantidades serão úteis para dimensionamento da população acompanhada, enquanto prevalências e cobertura serão necessárias para comparação territorial.

## 16. Critérios de aceite da futura implementação

A funcionalidade será considerada concluída quando:

- o usuário puder selecionar fases e faixas oficiais;
- faixas sobrepostas forem rejeitadas antes da coleta;
- todas as idades infantis utilizarem `0 a < 5` e `5 a < 10`;
- crianças, adolescentes, adultos e idosos possuírem bases oficiais independentes;
- gestantes forem preservadas em produto separado;
- existir um dicionário versionado de harmonização;
- magreza acentuada, magreza e baixo peso permanecerem separados como componentes do déficit total;
- cada fase possuir uma base harmonizada validada;
- a base geral somar somente os quatro grupos etários aprovados;
- altura por idade permanecer fora da soma da população geral;
- percentuais forem recalculados, nunca somados;
- arquivos brutos e individuais permanecerem inalterados;
- metadados registrarem filtros, fórmulas, fontes e limitações;
- testes cobrirem sobreposição, harmonização, soma e rastreabilidade;
- a possível duplicação entre fases no período estiver confirmada ou explicitamente limitada.

## 17. Estado da implementação

Esta decisão está documentada e aprovada metodologicamente. Nenhuma alteração no coletor foi realizada como parte desta atualização. A implementação deverá ocorrer em etapa posterior.
