# Informações e decisões metodológicas da pesquisa

## 1. Pergunta norteadora

> Identificar áreas do Brasil de maior risco alimentar e vulnerabilidade social a partir dos indicadores IVS, IDHM, CadÚnico, CadInsan e SISVAN.

Este documento registra conceitos, decisões metodológicas, limitações e verificações que devem ser considerados durante a coleta, o tratamento, a análise e a interpretação dos dados.

## 2. Distinção conceitual importante

Os indicadores utilizados não medem exatamente o mesmo fenômeno:

- **IVS, IDHM e CadÚnico** descrevem diferentes dimensões das condições sociais, econômicas e territoriais da população.
- **SISVAN** registra o estado nutricional e o consumo alimentar das pessoas acompanhadas pelos serviços de saúde.
- **CadInsan** estima risco de insegurança alimentar grave entre famílias do
  universo analisado do CadÚnico, com cenários considerando ou desconsiderando
  o efeito do Bolsa Família na renda.
- O estado nutricional observado no SISVAN não constitui, isoladamente, uma medida direta de insegurança alimentar domiciliar.

Por isso, é metodologicamente mais seguro tratar:

1. IVS, IDHM e CadÚnico como indicadores de **vulnerabilidade social estrutural**;
2. SISVAN como fonte de **desfechos ou sinais de vulnerabilidade nutricional**;
3. a coincidência territorial entre essas dimensões como evidência de áreas prioritárias para investigação e políticas públicas.

Evitar afirmar que a vulnerabilidade social causou diretamente determinado resultado nutricional apenas com base em correlações ou sobreposição espacial.

## 3. Insight central sobre o SISVAN: altura por idade

### 3.1 Indicador principal recomendado

Para identificar manifestações nutricionais crônicas associadas a condições persistentes de vulnerabilidade, analisar no SISVAN:

- **Fase da vida:** Criança;
- **Faixa etária:** 0 a menos de 5 anos;
- **Índice antropométrico:** Altura por idade;
- **Categorias de interesse:**
  - Muito baixa estatura para idade;
  - Baixa estatura para idade.

Calcular a prevalência de déficit de estatura:

```text
Déficit de estatura (%) =
(crianças com muito baixa estatura + crianças com baixa estatura)
÷ total de crianças avaliadas
× 100
```

O déficit de estatura para a idade representa um comprometimento de crescimento de natureza geralmente crônica e acumulada. Por esse motivo, possui maior coerência conceitual com a análise conjunta de pobreza, privação social, IVS elevado e IDHM baixo.

### 3.2 Peso por idade: opção preservada, fora da análise vigente

Não coletar peso por padrão e não incluir DPI na análise atual. O suporte e
os arquivos históricos permanecem disponíveis para outro estudo. Para esse
uso opcional, as categorias oficiais de **Peso por idade** são:

- Peso Muito Baixo para a Idade;
- Peso Baixo para a Idade;
- Peso Adequado ou Eutrófico;
- Peso Elevado para a Idade.

Se esse outro estudo for realizado, calcular separadamente:

```text
Déficit de peso para idade (%) =
(crianças com peso muito baixo + crianças com peso baixo)
÷ total avaliado em Peso X Idade
× 100
```

O produto analítico deve preservar `Peso Muito Baixo` e `Peso Baixo` como
componentes separados, além de apresentar a soma. `Peso Elevado para a Idade`
deve permanecer com sua nomenclatura oficial e não ser interpretado
automaticamente como sobrepeso ou obesidade.

### 3.3 Relação entre os dois índices

| Índice | Interpretação principal | Papel na pesquisa |
|---|---|---|
| Altura por idade | Comprometimento crônico ou acumulado do crescimento | Desfecho nutricional principal |
| Peso por idade | Déficit ponderal que pode refletir baixa estatura, baixo peso corporal ou ambos | Opcional; excluído da análise vigente |

Regras obrigatórias:

- utilizar a consulta direta de `0 a < 5 anos` para altura; regras abaixo sobre
  dois índices aplicam-se apenas a estudos opcionais, não à análise vigente;
- manter um denominador para Altura X Idade e outro para Peso X Idade;
- não somar déficit de estatura com déficit de peso;
- não afirmar quantas crianças possuem simultaneamente os dois déficits, pois
  os relatórios municipais agregados não identificam essa interseção;
- preservar integralmente as categorias oficiais nas bases de origem.

### 3.4 IMC por idade permanece disponível, mas fora da coleta padrão

Os arquivos e o suporte de **IMC por idade** não serão apagados. O índice
permanece disponível para análises de sensibilidade, magreza e excesso de peso,
mas deixa de integrar a configuração padrão da análise principal.

Para avaliar especificamente magreza aguda ou excesso de peso, IMC por idade
ou peso por altura são mais apropriados do que interpretar `Peso Elevado para a
Idade` como diagnóstico dessas condições.

### 3.5 Por que “baixo peso” não deve ser o único indicador

No SISVAN, **baixo peso para idade** pertence ao índice **Peso por idade**. Já **magreza** e **magreza acentuada** pertencem a índices como **IMC por idade** e **Peso por altura**.

Esses nomes não são sinônimos e não devem ser trocados na base bruta. O peso por idade é menos específico, pois uma criança pode apresentar baixo peso em razão de baixa estatura, magreza ou da combinação dessas condições.

Assim, para a pergunta desta pesquisa:

- usar **déficit de estatura para idade** como resultado principal de privação nutricional crônica;
- manter peso por idade como opção para outro estudo, não como complementar atual;
- reservar **magreza por IMC para idade** para análise opcional ou de sensibilidade;
- não usar **baixo peso para idade** como único marcador de risco alimentar.

## 4. Preservação integral das bases originais

Os arquivos brutos devem permanecer **100% fiéis às fontes oficiais**. Isso inclui:

- nomes originais das colunas;
- categorias e grafia utilizadas pela fonte;
- valores, códigos, períodos e unidades originais;
- ausência de categorias que não tenham sido fornecidas pela fonte;
- metadados necessários para reproduzir a consulta.

Não renomear colunas, juntar categorias, calcular percentuais ou inserir códigos de outras fontes diretamente na camada bruta.

Sugestão de organização:

```text
dados/
├── brutos/          # arquivos exatamente como obtidos em cada fonte
├── intermediarios/  # padronizações e junções reproduzíveis
└── tratados/        # indicadores finais utilizados na análise
```

Toda transformação deve ocorrer por código e ser documentada. Dessa forma, é possível reproduzir a análise e conferir os resultados com os arquivos originais.

## 5. Unidade territorial e compatibilização

Antes do cruzamento, verificar se todas as fontes possuem a mesma unidade de análise. Para uma análise nacional detalhada, a unidade mais provável é o **município**.

Cuidados necessários:

- utilizar o código oficial do município do IBGE como chave de integração;
- confirmar se cada fonte utiliza código de seis ou sete dígitos;
- não realizar a junção apenas pelo nome do município;
- preservar zeros à esquerda quando os códigos forem armazenados como texto;
- verificar criação, extinção, fusão ou alteração de municípios entre os anos analisados;
- conferir se IVS e IDHM estão disponíveis no mesmo nível territorial pretendido;
- documentar perdas de correspondência em cada junção.

Produzir uma tabela de controle contendo, para cada integração:

- quantidade de territórios antes da junção;
- quantidade de correspondências;
- quantidade de registros sem correspondência em cada fonte;
- duplicidades encontradas;
- tratamento adotado para cada problema.

## 6. Compatibilidade temporal

IVS, IDHM, CadÚnico e SISVAN podem possuir anos de referência muito diferentes. Comparar diretamente valores de anos distintos exige cautela.

Para cada variável, registrar:

- ano ou período de referência;
- data de extração;
- abrangência geográfica;
- população considerada;
- periodicidade da atualização;
- eventuais mudanças metodológicas.

Quando não for possível usar o mesmo ano em todas as fontes:

1. escolher os períodos mais próximos disponíveis;
2. justificar a escolha;
3. evitar linguagem que pressuponha simultaneidade perfeita;
4. realizar análise de sensibilidade com outros anos, quando possível.

O IDHM municipal, em particular, está associado aos dados censitários utilizados em sua construção e não deve ser tratado automaticamente como um indicador anual.

## 7. Indicadores sugeridos por dimensão

### 7.1 Vulnerabilidade social estrutural

Possíveis variáveis:

- IVS total e suas dimensões;
- IDHM total e suas dimensões;
- proporção da população inscrita no CadÚnico;
- proporção de famílias ou pessoas em pobreza e extrema pobreza;
- proporção de beneficiários de programas de transferência de renda, se pertinente;
- outras variáveis do CadÚnico compatíveis com a pergunta e a unidade territorial.

Como IVS alto indica maior vulnerabilidade e IDHM alto indica maior desenvolvimento, padronizar a direção antes de produzir classificações conjuntas. Por exemplo, utilizar o inverso ou uma transformação do IDHM apenas na base tratada e documentar a fórmula.

### 7.2 Vulnerabilidade nutricional

Indicador principal:

- prevalência de déficit de estatura para idade em crianças menores de 5 anos.

Indicadores complementares:

- prevalência de peso muito baixo e peso baixo para idade;
- prevalência combinada de déficit de peso para idade;
- prevalência de magreza, risco de sobrepeso, sobrepeso e obesidade por IMC
  para idade, somente em análise opcional ou de sensibilidade;
- peso por altura, se a análise de déficit nutricional agudo for relevante;
- indicadores de consumo alimentar, caso estejam disponíveis e sejam compatíveis com o recorte.

Analisar tanto déficits quanto excesso de peso permite observar a **dupla carga da má nutrição**, que pode coexistir em territórios socialmente vulneráveis.

### 7.3 Visão geral da população acompanhada

A análise principal de vulnerabilidade nutricional continuará utilizando o déficit de estatura em crianças menores de 5 anos. Como produto complementar, será construída uma visão geral do estado nutricional de crianças, adolescentes, adultos e idosos acompanhados pelo SISVAN. Gestantes permanecerão em uma base separada.

Na base harmonizada, o grupo `Déficit nutricional total` será detalhado sem perda das classificações disponíveis em cada fase:

```text
Déficit nutricional total
├── Magreza acentuada — crianças e adolescentes
├── Magreza — crianças e adolescentes
└── Baixo peso — adultos e idosos
```

`Magreza acentuada` e `Magreza` não serão tratadas como classificações existentes para adultos e idosos. Da mesma forma, `Baixo peso` não será convertido artificialmente nas categorias de magreza.

Os três detalhamentos são componentes do déficit total. Portanto, não poderão ser somados novamente a ele em tabelas, mapas ou modelos. Os percentuais detalhados deverão utilizar denominadores compatíveis com as fases que efetivamente possuem cada classificação.

As regras completas estão registradas em [Decisão metodológica: agregação etária e visão geral da população no SISVAN](docs/arquitetura/DECISAO_AGREGACAO_FAIXAS_ETARIAS.md).

## 8. Denominadores, cobertura e estabilidade dos resultados do SISVAN

Os dados do SISVAN se referem à população acompanhada e registrada na Atenção Primária à Saúde. Portanto, não devem ser interpretados automaticamente como uma amostra representativa de todos os residentes do município.

Para cada município, preservar no mínimo:

- número de pessoas avaliadas;
- número em cada categoria nutricional;
- percentual em cada categoria;
- ano de referência;
- fase da vida e faixa etária;
- índice antropométrico;
- abrangência e demais filtros utilizados na consulta.

Sempre que possível, calcular ou obter a cobertura:

```text
Cobertura aproximada do SISVAN (%) =
número de crianças avaliadas no SISVAN
÷ população estimada de crianças da mesma faixa etária no município
× 100
```

O denominador populacional deve possuir idade, território e período compatíveis com o numerador.

Municípios com poucos avaliados podem apresentar percentuais extremos por acaso. Considerar:

- estabelecer um número mínimo de avaliações para análises comparativas;
- apresentar o número de avaliados junto com a prevalência;
- produzir análise de sensibilidade com diferentes pontos de corte;
- utilizar suavização estatística ou modelos apropriados para pequenas áreas, se houver suporte metodológico;
- mapear a cobertura para distinguir possível risco nutricional de ausência ou baixa intensidade de monitoramento.

Nunca classificar uma prevalência elevada como prioridade sem conferir seu denominador.

## 9. Possível sobreposição entre CadÚnico e SISVAN

Parte relevante das pessoas acompanhadas no SISVAN pode estar vinculada ao CadÚnico ou a programas de transferência de renda. Isso pode gerar sobreposição entre as populações das fontes.

Consequências possíveis:

- municípios com melhor busca ativa podem registrar mais famílias vulneráveis no CadÚnico e mais avaliações no SISVAN;
- uma associação observada pode refletir tanto vulnerabilidade real quanto diferenças de cobertura e capacidade administrativa;
- baixa ocorrência registrada pode significar baixo risco, mas também baixa cobertura do sistema.

Incluir cobertura, porte populacional, região e capacidade de registro entre as variáveis de controle ou nas análises de sensibilidade, quando possível.

## 10. Estratégia analítica recomendada

### Etapa 1 — Descrição individual das fontes

- avaliar distribuição, valores ausentes e extremos;
- conferir definições, denominadores e anos;
- mapear a cobertura e a disponibilidade dos dados;
- inspecionar a estabilidade dos percentuais do SISVAN.

### Etapa 2 — Construção de uma dimensão social

Padronizar, somente na base tratada, indicadores selecionados de IVS, IDHM e CadÚnico para que todos tenham a mesma direção: valores maiores devem representar maior vulnerabilidade.

Antes de criar um índice sintético, examinar:

- correlação entre variáveis;
- redundância conceitual;
- disponibilidade territorial;
- sensibilidade aos pesos utilizados;
- justificativa teórica de cada componente.

Não atribuir pesos arbitrários sem justificativa. Uma alternativa transparente é apresentar separadamente as dimensões e testar mais de uma especificação.

### Etapa 3 — Confronto com os resultados nutricionais

Relacionar a dimensão social principalmente com:

- déficit de estatura para idade;
- magreza por IMC para idade como resultado complementar;
- cobertura e número de avaliados do SISVAN.

### Etapa 4 — Identificação de áreas prioritárias

Uma classificação simples e interpretável pode identificar territórios com:

```text
alta vulnerabilidade social
+ alta prevalência de déficit de estatura
+ cobertura suficiente para sustentar a estimativa
```

É possível utilizar quantis, pontos de corte teóricos, mapas bivariados ou técnicas de análise espacial. A escolha deve ser descrita e testada quanto à sensibilidade.

### Etapa 5 — Análise espacial

Se forem aplicadas técnicas espaciais, considerar:

- dependência espacial entre municípios vizinhos;
- escolha e justificativa da matriz de vizinhança;
- autocorrelação espacial global e local;
- efeito do tamanho populacional e de pequenos denominadores;
- diferenças regionais e urbano-rurais;
- interpretação cuidadosa de agrupamentos espaciais.

## 11. Interpretação dos resultados

Evitar os seguintes erros:

- **falácia ecológica:** relações municipais não demonstram que todos os indivíduos do município possuem as mesmas características;
- **causalidade indevida:** associação espacial ou estatística não comprova causa;
- **confusão entre ausência de registro e ausência de problema:** dados faltantes ou baixa cobertura precisam ser mostrados;
- **comparação de grandezas incompatíveis:** contagens absolutas favorecem municípios populosos;
- **confusão entre baixo peso e magreza:** são classificações pertencentes a índices diferentes;
- **transformação da base bruta:** nomes e categorias oficiais devem ser preservados na origem;
- **ranking sem incerteza:** pequenas diferenças podem não representar diferenças substantivas.

Dar preferência a prevalências e proporções acompanhadas de seus denominadores, intervalos de confiança ou outras medidas de estabilidade, quando viável.

## 12. Produtos úteis para a pesquisa

Além da base analítica final, produzir:

- dicionário de dados com fonte, definição, unidade, direção e ano de cada variável;
- registro dos filtros usados nas consultas;
- scripts reproduzíveis de coleta, limpeza e junção;
- relatório de qualidade das integrações municipais;
- mapa da cobertura do SISVAN;
- mapa do déficit de estatura para idade;
- mapa da vulnerabilidade social;
- mapa bivariado entre vulnerabilidade social e déficit de estatura;
- análise complementar de magreza por IMC para idade;
- tabela com resultados das análises de sensibilidade.

## 13. Formulação recomendada para o objetivo

Uma formulação mais precisa pode ser:

> Identificar áreas do Brasil com sobreposição de vulnerabilidade social e nutricional, a partir de indicadores do IVS, IDHM e CadÚnico e da prevalência de déficit de estatura em crianças menores de 5 anos acompanhadas pelo SISVAN.

Se a pesquisa mantiver a expressão “risco alimentar”, explicar que ela é uma construção analítica baseada na combinação de condições sociais e desfechos nutricionais, e não uma medição direta da insegurança alimentar por escala domiciliar.

## 14. Fontes metodológicas essenciais

- Ministério da Saúde — [Protocolos do Sistema de Vigilância Alimentar e Nutricional (SISVAN)](https://www.gov.br/saude/pt-br/composicao/saps/vigilancia-alimentar-e-nutricional/arquivos/protocolos-do-sistema-de-vigilancia-alimentar-e-nutricional-sisvan)
- Ministério da Saúde — [Sistema de Vigilância Alimentar e Nutricional](https://www.gov.br/saude/pt-br/composicao/saps/vigilancia-alimentar-e-nutricional/sisvan)
- Organização Mundial da Saúde — [Malnutrition in children](https://www.who.int/data/nutrition/nlis/info/malnutrition-in-children)
- Organização Mundial da Saúde — [Child Growth Standards](https://www.who.int/tools/child-growth-standards)

## 15. Decisões a registrar durante o desenvolvimento

Manter esta seção atualizada com as decisões definitivas da pesquisa:

- [ ] unidade territorial escolhida;
- [ ] período ou anos analisados;
- [ ] filtros exatos utilizados no SISVAN;
- [ ] obtenção da base de altura por idade para menores de 5 anos;
- [ ] definição do denominador de cobertura do SISVAN;
- [ ] número mínimo de avaliações por município;
- [ ] variáveis selecionadas do CadÚnico;
- [ ] tratamento temporal do IVS e do IDHM;
- [ ] método de padronização dos indicadores;
- [ ] método de identificação das áreas prioritárias;
- [ ] análises de sensibilidade;
- [ ] limitações incluídas no texto final.

## 16. Validação documental das bases sociais e processamento do notebook

Em 4 de outubro de 2026, o
[dataset_catalogue.json](dataset_catalogue.json), do repositório Cozinhas
Solidárias, foi conferido com as três bases sociais utilizadas. Seus hashes
SHA-256 correspondem exatamente aos arquivos de IVS/IDHM, CadÚnico e CadInsan.
O catálogo é preservado sem edição e incorporado ao notebook.

| Fonte | Unidade | Referência |
|---|---|---|
| IVS/IDHM | Índices municipais | 2010 |
| JSON CadÚnico | Pessoas cadastradas | Junho/2026 |
| CadInsan | Famílias em risco estimado e denominador em famílias | Janeiro/2025, conforme relatório oficial |
| SISVAN | Registros de crianças menores de cinco anos acompanhadas | 2025, todos os meses |

O catálogo informa referência anual de 2025 para o CadInsan. O
[relatório oficial citado](https://www.gov.br/mds/pt-br/Sisan/vigilancia-do-sisan/CADINSAN2025.pdf)
explicita janeiro/2025, famílias com cadastro atualizado nos últimos 12 meses
e cenários com/sem efeito do PBF. A tabela municipal foi conferida por amostragem
com o CSV. Não confundir famílias no denominador do CadInsan com pessoas do JSON.

O notebook recalcula CadInsan como `100 × absoluto / Cadastros_Cadunico`, sem
arredondamento. Os percentuais do CSV permanecem em colunas `*_arquivo`, e
denominador não positivo resulta em ausência analítica. Esse processamento
segue o procedimento documentado em `datasets.municipios_cadinsan.description`
e `source.notes`, sem modificar as bases de entrada.

Na configuração atual IVS ≥ 0,401 e IDHM < 0,600 (fixos), P75 para CadInsan/DAI,
`com_PBF` e mínimo de 100 avaliações de altura, a seleção passa de 243 municípios,
usando percentuais arredondados, para 242
com as razões recalculadas. O notebook exporta essa comparação. O estudo
continua exploratório: diferenças temporais, cobertura, malhas territoriais e
justificativas para os cortes ainda precisam ser consideradas.

### IDHM como critério obrigatório da sobreposição

A pesquisa adotou a coincidência de **IVS elevado + IDHM baixo + CadInsan
proporcional elevado + DAI elevado**, sem ranking composto. Todos os municípios
continuam na base integrada; a seleção exige os quatro critérios e os
denominadores válidos. IDHM ausente gera informação insuficiente.

IVS usa corte fixo ≥ 0,401, e IDHM usa corte fixo < 0,600. Eles seguem as faixas
de alta/muito alta vulnerabilidade e baixo/muito baixo desenvolvimento. A
direção é considerada na comparação, sem transformar os índices originais.
IDHM igual a 0,600 não atende ao critério. Esses cortes não variam com os
quantis de CadInsan/DAI nem na sensibilidade; a convergência não prova
independência entre IVS e IDHM nem causalidade.

A regra anterior de quatro critérios, com quartis também para IVS/IDHM,
selecionava 218 municípios. Ao mudar somente esses dois cortes para fixos,
a seleção passa a 242. CadInsan/DAI continuam com quantis, e o mínimo principal
continua 100 avaliações; não foi adotado corte fixo de 20% para DAI.
CadÚnico continua contextual; DPI foi retirado integralmente. Na sensibilidade, os quatro critérios
são mantidos, e a seleção varia de 179 a 270 municípios nas 12 especificações.

## Atualização da entrada SISVAN: altura sem derivados

Nova coleta de 2025 nas 27 UFs, realizada em 4 de outubro de 2026 com o coletor
5.0. O padrão passa a ser somente Altura X Idade, menores de cinco anos. Não
há DAI, DPI, peso ou novas colunas de filtro na entrada. O coletor não gera mais
o produto automático combinado. XLSX exatos e produtos antigos são preservados.

O CSV achata cabeçalhos multinível e mantém contagens como aparecem nas células,
inclusive decimais do exportador. Filtros e hashes ficam no sidecar. O notebook
interpreta escalas, valida soma e percentuais e calcula DAI sem arredondamento,
com ausência quando o total é zero. Inteiros que já conferem com soma e
percentuais são mantidos sem testar uma linha inteira multiplicada por 1.000.
Essa hipótese artificial foi rejeitada pela pesquisa. Para as demais leituras,
exige-se conciliação única ou interrupção para conferência na fonte.

Ver [README da entrada SISVAN](dados/pesquisa/sisvan/README.md) e
[decisão de arquitetura](docs/arquitetura/DECISAO_SISVAN_ALTURA_SEM_DERIVADOS.md).
As contagens interpretadas e os 242 municípios selecionados permaneceram iguais
após a nova coleta; isso foi conferido, não presumido.
