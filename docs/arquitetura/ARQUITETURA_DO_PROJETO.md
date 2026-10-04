# Arquitetura do projeto

## 1. Finalidade

Este documento define a arquitetura que deverá orientar a coleta, o armazenamento, o tratamento e a análise dos dados da pesquisa:

> Identificar áreas do Brasil de maior risco alimentar e vulnerabilidade social a partir dos indicadores IVS, IDHM, CadÚnico e SISVAN.

A arquitetura foi desenhada para garantir:

- fidelidade integral aos dados obtidos nas fontes oficiais;
- separação entre dados brutos, intermediários e tratados;
- rastreabilidade de cada consulta;
- reprodução das coletas e transformações;
- possibilidade de coletar diferentes faixas etárias;
- preservação das diferenças entre os índices do SISVAN;
- validação antes da utilização dos dados na pesquisa.

## 2. Princípios obrigatórios

### 2.1 Imutabilidade dos dados brutos

Os arquivos brutos devem permanecer exatamente como foram obtidos nas fontes oficiais. Não devem ser realizadas diretamente nesses arquivos operações como:

- renomear colunas;
- corrigir grafia;
- incluir códigos territoriais de outra fonte;
- acrescentar colunas de identificação da consulta;
- juntar categorias nutricionais;
- calcular novos percentuais;
- excluir linhas ou valores ausentes;
- consolidar consultas diferentes.

Qualquer modificação deverá ocorrer somente nas camadas intermediária ou tratada.

### 2.2 Uma extração bruta para cada consulta

Cada combinação de parâmetros enviada ao SISVAN deverá gerar um arquivo bruto independente. Isso inclui, no mínimo, as combinações de:

- índice antropométrico;
- faixa etária;
- ano ou período;
- abrangência territorial;
- demais filtros disponibilizados pelo SISVAN.

Essa regra é necessária porque alguns parâmetros utilizados na consulta podem não estar presentes no conteúdo do arquivo devolvido pelo sistema.

### 2.3 Transformações reproduzíveis

Toda limpeza, padronização, integração ou construção de indicador deverá ser executada por código versionado. Nenhuma alteração manual deverá ser incorporada silenciosamente à base final.

### 2.4 Separação entre fonte e interpretação

As nomenclaturas oficiais deverão ser preservadas na camada bruta. Termos analíticos criados na pesquisa, como `deficit_estatura_total`, deverão aparecer somente nas bases tratadas e ser acompanhados de fórmula e definição.

## 3. Estrutura de diretórios planejada

```text
areas-risco-alimentar-e-vuln-social/
├── README.md
├── docs/
│   ├── arquitetura/
│   │   └── ARQUITETURA_DO_PROJETO.md
│   ├── metodologia/
│   ├── dicionarios/
│   └── relatorios/
├── configuracoes/
│   ├── sisvan/
│   └── fontes_sociais/
├── dados/
│   ├── brutos/
│   │   ├── sisvan/
│   │   │   ├── altura_por_idade/
│   │   │   ├── peso_por_idade/
│   │   │   └── imc_por_idade/
│   │   ├── ivs/
│   │   ├── idhm/
│   │   └── cadunico/
│   ├── intermediarios/
│   │   ├── sisvan/
│   │   ├── territorios/
│   │   └── fontes_sociais/
│   └── tratados/
│       ├── sisvan/
│       ├── indicadores_sociais/
│       └── base_analitica/
├── metadados/
│   ├── manifestos/
│   ├── esquemas/
│   └── controles_qualidade/
├── scripts/
│   ├── coleta/
│   ├── validacao/
│   ├── tratamento/
│   ├── integracao/
│   └── analise/
├── resultados/
│   ├── tabelas/
│   ├── mapas/
│   ├── graficos/
│   └── modelos/
├── testes/
│   ├── coleta/
│   ├── esquemas/
│   └── indicadores/
└── logs/
```

Essa é a estrutura de destino. A adoção deverá preservar arquivos e diretórios que já existam no projeto, sem movimentações destrutivas ou sobrescritas.

## 4. Arquitetura específica da coleta do SISVAN

### 4.1 Fases e índices mantidos

O projeto coleta e preserva as seguintes famílias de dados:

1. **Crianças:** altura por idade e peso por idade como recorte padrão; IMC por idade como opção preservada;
2. **Adolescentes:** IMC por idade e altura por idade;
3. **Adultos:** IMC;
4. **Idosos:** IMC;
5. **Gestantes:** IMC por semana gestacional, em base separada.

Índices e fases não são misturados nos arquivos brutos porque possuem categorias
nutricionais e interpretações diferentes. O coletor valida os cabeçalhos próprios
de cada combinação antes de produzir qualquer base derivada.

### 4.2 Faixas etárias configuráveis

O coletor deverá permitir uma lista de faixas etárias para cada índice. Somente opções efetivamente disponibilizadas pelo SISVAN deverão ser aceitas na coleta oficial.

Exemplo conceitual de configuração:

```yaml
sisvan:
  indices:
    - nome: altura_por_idade
      faixas_etarias:
        - 0_a_menor_5_anos
    - nome: peso_por_idade
      faixas_etarias:
        - 0_a_menor_5_anos
```

Essa é a configuração padrão implementada. Outras faixas oficiais continuam
disponíveis para consultas adicionais.

### 4.3 Matriz de execução

Cada combinação deverá ser tratada como uma unidade independente de coleta:

```text
índice × faixa etária × ano/período × abrangência × demais filtros
```

Se forem definidos dois índices, três faixas etárias e dois anos, a execução poderá produzir até doze consultas independentes, antes de considerar outros filtros.

### 4.4 Faixas sobrepostas

As faixas etárias podem ser sobrepostas. Nesse caso:

- os resultados não deverão ser somados;
- não se deverá presumir que as consultas representam grupos mutuamente exclusivos;
- uma mesma pessoa poderá contribuir para mais de uma extração;
- cada arquivo deverá ser analisado segundo os parâmetros próprios da consulta;
- agregações posteriores deverão usar apenas faixas comprovadamente disjuntas.

### 4.5 Agregação etária e visão geral da população

A agregação municipal será permitida somente entre intervalos mutuamente exclusivos. Para cobrir a fase infantil sem sobreposição, será utilizada a combinação `0 a < 5 anos` com `5 a < 10 anos`.

A visão geral da população acompanhada reunirá crianças, adolescentes, adultos e idosos após harmonização das classificações nutricionais próprias de cada fase. Gestantes permanecerão em produto separado, e altura por idade não participará da soma populacional geral.

No grupo `Déficit nutricional total`, `Magreza acentuada` e `Magreza` serão preservadas separadamente para crianças e adolescentes, enquanto `Baixo peso` será preservado para adultos e idosos. Esses campos serão componentes hierárquicos do déficit total e não poderão ser somados novamente a ele.

As regras de cálculo, harmonização, prevenção de dupla contagem, preservação das categorias oficiais e interpretação estão registradas em [Decisão metodológica: agregação etária e visão geral da população no SISVAN](DECISAO_AGREGACAO_FAIXAS_ETARIAS.md).

## 5. Convenção dos arquivos brutos

### 5.1 Organização

```text
dados/brutos/sisvan/
├── altura_por_idade/
├── peso_por_idade/
├── imc_por_idade/                 # preservado e opcional
├── adolescente/<indice>/<faixa>/<ano>/ufs/<UF>.xlsx
├── adulto/imc/<faixa>/<ano>/ufs/<UF>.xlsx
├── idoso/imc/<faixa>/<ano>/ufs/<UF>.xlsx
└── gestante/imc_por_semana_gestacional/<faixa>/<ano>/ufs/<UF>.xlsx
```

### 5.2 Regras de nomenclatura

O nome físico do arquivo poderá registrar os parâmetros da extração, mas seu conteúdo permanecerá inalterado. A convenção deverá:

- utilizar apenas caracteres portáveis;
- evitar espaços e acentos;
- indicar o índice;
- indicar a faixa etária de forma não ambígua;
- indicar o ano ou período;
- indicar a abrangência quando necessário;
- evitar sobrescrita de extrações anteriores.

Se a fonte determinar o nome original do arquivo, esse nome também deverá ser registrado no manifesto.

## 6. Manifesto de coletas

Cada arquivo bruto deverá possuir uma entrada em um manifesto separado. O manifesto é a fonte de metadados da coleta e não substitui nem modifica o arquivo original.

Campos mínimos recomendados:

| Campo | Finalidade |
|---|---|
| `id_coleta` | Identificador único da consulta |
| `fonte` | Sistema de origem |
| `arquivo_local` | Caminho do arquivo bruto |
| `nome_original` | Nome recebido da fonte, quando aplicável |
| `indice_antropometrico` | IMC por idade ou altura por idade |
| `faixa_etaria` | Nome oficial do filtro utilizado |
| `ano_inicio` | Início do período consultado |
| `ano_fim` | Fim do período consultado |
| `abrangencia` | Brasil, UF, município ou outra opção |
| `filtros` | Demais parâmetros enviados |
| `data_hora_coleta` | Momento da extração |
| `quantidade_registros` | Total de registros obtidos |
| `hash_arquivo` | Verificação de integridade |
| `status` | Sucesso, vazio, falha ou pendente de validação |
| `versao_coletor` | Versão do código utilizado |
| `observacoes` | Alertas relevantes |

O manifesto poderá ser armazenado em formato tabular e, se necessário, acompanhado por uma representação estruturada em JSON ou YAML.

## 7. Camadas de dados

### 7.1 Camada bruta

Contém reproduções fiéis das fontes. Um arquivo representa uma consulta. Nenhuma transformação analítica é permitida.

### 7.2 Camada intermediária

Contém dados preparados para integração, incluindo:

- padronização técnica de tipos;
- tratamento explícito de códigos territoriais;
- identificação do ano e da faixa etária;
- conversão controlada para formato longo;
- verificação de duplicidades;
- associação com o manifesto;
- registro de inconsistências.

Toda coluna acrescentada deverá possuir origem documentada.

### 7.3 Camada tratada

Contém indicadores prontos para análise. Para o SISVAN, os produtos permanecem
separados por consulta, fase e finalidade:

```text
dados/tratados/sisvan/
├── altura_por_idade/               # consultas infantis individuais
├── peso_por_idade/                 # consultas infantis individuais
├── imc_por_idade/                  # preservado e opcional
├── criancas_menores_5/             # indicadores derivados de altura e peso
├── consultas/<fase>/<indice>/      # demais consultas individuais
├── faixas_somadas/<fase>/<indice>/ # soma solicitada pelo usuário
├── por_fase/                        # categorias oficiais na visão geral
├── harmonizados/                    # grupos comparáveis por fase
├── populacao_geral/                 # crianças + adolescentes + adultos + idosos
└── gestantes/                        # produto separado
```

Esses arquivos poderão incluir colunas de controle que não existem na fonte, como:

- índice antropométrico;
- faixa etária;
- ano;
- abrangência;
- identificador da coleta;
- data da coleta;
- indicadores derivados.

Por terem sido transformados, não deverão ser descritos como cópias idênticas dos arquivos do SISVAN.

### 7.4 Base analítica integrada

A integração entre SISVAN, IVS, IDHM e CadÚnico deverá ocorrer apenas depois da validação individual das fontes.

A base analítica deverá:

- utilizar código territorial oficial como chave;
- registrar o ano de referência de cada indicador;
- preservar os denominadores do SISVAN;
- incluir medidas de cobertura quando disponíveis;
- distinguir vulnerabilidade social de desfecho nutricional;
- permitir identificar a origem de cada variável.

## 8. Indicadores nutricionais planejados

### 8.1 Altura por idade: indicador principal

Para crianças de 0 a menos de 5 anos, o desfecho nutricional principal será a prevalência de déficit de estatura:

```text
Déficit de estatura (%) =
(muito baixa estatura para idade + baixa estatura para idade)
÷ total de crianças avaliadas
× 100
```

A fórmula deverá ser aplicada somente na camada tratada. As categorias oficiais deverão permanecer separadas na camada bruta.

### 8.2 Peso por idade: indicador complementar padrão

Para crianças de 0 a menos de 5 anos, o segundo indicador será:

```text
Déficit de peso para idade (%) =
(peso muito baixo para idade + peso baixo para idade)
÷ total avaliado em Peso X Idade
× 100
```

`Peso muito baixo` e `Peso baixo` permanecerão separados na base tratada. O
déficit de peso não será somado ao déficit de estatura, porque as mesmas crianças
podem estar presentes nos dois índices e os relatórios agregados não permitem
identificar essa interseção.

### 8.3 IMC por idade: indicador opcional

A coleta de IMC por idade será mantida como opção e para a visão geral por
fases, mas não fará parte da configuração infantil padrão. Uma medida possível é:

```text
Magreza total (%) =
(magreza acentuada + magreza)
÷ total de crianças avaliadas
× 100
```

Também deverão ser preservadas as categorias relacionadas ao excesso de peso para permitir a análise da dupla carga da má nutrição.

### 8.4 Denominadores

Nenhuma prevalência deverá ser analisada sem o número de pessoas avaliadas. Municípios com denominadores pequenos deverão ser identificados e submetidos a critérios de qualidade ou análises de sensibilidade.

## 9. Fluxo de processamento

```text
Configuração da consulta
        ↓
Validação dos parâmetros oficiais
        ↓
Consulta à fonte
        ↓
Arquivo bruto imutável + registro no manifesto
        ↓
Validação de estrutura, conteúdo e integridade
        ↓
Camada intermediária por fonte
        ↓
Consolidados separados por índice
        ↓
Cálculo dos indicadores derivados
        ↓
Integração territorial e temporal das fontes
        ↓
Base analítica
        ↓
Tabelas, mapas, gráficos e modelos
```

## 9.1 Comandos implementados para agregação

Selecionar e somar faixas infantis sem sobreposição, uma saída por índice:

```bash
python3 scripts/coletar_sisvan.py \
  --indices altura_por_idade,peso_por_idade \
  --faixas-etarias 0-5,5-10 \
  --somar-faixas
```

Construir a visão geral de crianças, adolescentes, adultos e idosos:

```bash
python3 scripts/coletar_sisvan.py --populacao-geral
```

Acrescentar a base separada de gestantes:

```bash
python3 scripts/coletar_sisvan.py --populacao-geral --incluir-gestantes
```

`--todas-faixas` continua significando as nove consultas infantis oficiais e
pode ser usado para concatenação. Como elas se sobrepõem, sua combinação com
`--somar-faixas` é rejeitada antes da coleta.

Uma etapa só deverá avançar quando as verificações previstas na etapa anterior forem aprovadas.

## 10. Validações mínimas

### 10.1 Validação da coleta

- confirmar que a resposta pertence ao índice solicitado;
- confirmar a faixa etária e o período da consulta;
- verificar se o arquivo está completo e legível;
- identificar respostas vazias ou páginas de erro salvas como dados;
- comparar o esquema obtido com o esquema oficial esperado;
- registrar o total de linhas e o hash do arquivo.

### 10.2 Validação nutricional

- preservar exatamente os nomes oficiais das categorias;
- verificar se contagens são não negativas;
- verificar se percentuais estão dentro do intervalo possível;
- conferir a soma das categorias em relação ao total avaliado;
- aplicar tolerância documentada para arredondamentos;
- impedir a mistura de categorias de índices diferentes.

### 10.3 Validação territorial

- conferir formato e tamanho dos códigos municipais;
- identificar códigos ausentes, inválidos ou duplicados;
- verificar perdas em cada integração;
- não utilizar apenas o nome do município como chave;
- produzir relatório de correspondências e divergências.

### 10.4 Validação temporal

- registrar o ano de referência de cada fonte;
- impedir que a data de extração seja confundida com o período dos dados;
- sinalizar comparações entre anos não equivalentes;
- documentar mudanças metodológicas das fontes.

## 11. Logs, falhas e reexecução

O coletor deverá registrar, por consulta:

- início e fim da execução;
- parâmetros usados;
- tentativas realizadas;
- mensagens de erro;
- status final;
- arquivo produzido;
- validações aprovadas ou reprovadas.

Uma reexecução não deverá sobrescrever silenciosamente um arquivo bruto existente. A política definitiva poderá utilizar versionamento, carimbo de data e hora ou verificação por hash.

Falhas parciais deverão permitir retomar apenas as consultas incompletas.

## 12. Responsabilidade de cada componente

| Componente | Responsabilidade |
|---|---|
| Configurações | Declarar índices, faixas, anos, abrangência e filtros |
| Coletor | Consultar a fonte e salvar a resposta sem alterar o conteúdo |
| Manifesto | Registrar parâmetros, procedência e integridade |
| Validador | Detectar respostas incorretas, incompletas ou incompatíveis |
| Tratamento | Padronizar tipos e produzir dados intermediários rastreáveis |
| Consolidador | Reunir consultas compatíveis sem misturar índices distintos |
| Integrador | Relacionar SISVAN, IVS, IDHM, CadÚnico e dados territoriais |
| Análise | Calcular indicadores, classificações e resultados espaciais |
| Testes | Garantir que mudanças no código não alterem regras já validadas |

## 13. Produtos finais planejados

O projeto deverá produzir, no mínimo:

1. arquivos brutos independentes para cada consulta;
2. manifesto completo das coletas;
3. consolidado tratado de altura por idade para menores de 5 anos;
4. consolidado tratado de peso por idade para menores de 5 anos;
5. produto infantil com os dois déficits e denominadores separados;
6. consolidados opcionais de IMC por idade e da visão geral por fases;
7. relatório de cobertura e qualidade do SISVAN;
8. bases tratadas de IVS, IDHM e CadÚnico;
9. relatório de integração territorial e temporal;
10. base analítica integrada;
11. mapas e tabelas de vulnerabilidade social;
12. mapas de déficit de estatura e de peso para idade;
13. produtos espaciais de sobreposição entre vulnerabilidade social e nutricional;
14. documentação e dicionário das variáveis.

## 14. Decisões de implementação

- [x] Enumerar as faixas etárias oficiais disponíveis no SISVAN para cada índice.
- [x] Definir inicialmente a faixa de 0 a menos de 5 anos para os dois índices.
- [x] Confirmar os filtros constantes entre as consultas.
- [x] Definir 2025 e todos os municípios do Brasil como recorte inicial.
- [x] Definir a convenção de nomes dos arquivos.
- [x] Definir o formato CSV e o esquema do manifesto.
- [x] Reutilizar arquivos brutos e exigir `--force` para sobrescrita explícita.
- [ ] Definir limite mínimo de avaliados para as análises municipais.
- [ ] Definir a fonte do denominador utilizado no cálculo de cobertura.
- [x] Validar os esquemas oficiais de altura, peso e IMC por idade.
- [x] Manter denominadores separados para altura por idade e peso por idade.
- [x] Impedir a soma entre déficit de estatura e déficit de peso para idade.
- [x] Definir testes automáticos de fidelidade e consistência.

## 15. Ordem recomendada de implementação

1. inventariar e preservar a coleta anterior de IMC por idade;
2. separar configuração, coleta, validação e transformação;
3. implementar o manifesto das consultas;
4. tornar as faixas etárias configuráveis;
5. validar as faixas contra as opções oficiais do SISVAN;
6. adicionar altura por idade e peso por idade como coletas independentes;
7. gerar um arquivo bruto por combinação de parâmetros;
8. implementar verificações automáticas de integridade e conteúdo;
9. criar consolidados separados para os índices e um produto infantil derivado;
10. calcular indicadores derivados apenas na camada tratada;
11. integrar as demais fontes somente após a aprovação das bases individuais.

## 16. Critério de aceite da arquitetura

A implementação estará de acordo com esta arquitetura quando altura por idade e
peso por idade forem coletados por padrão em `0 a < 5 anos`, IMC permanecer
disponível opcionalmente e, para cada consulta, for possível:

- reproduzir os parâmetros utilizados;
- localizar o arquivo bruto correspondente;
- demonstrar que seu conteúdo não foi alterado;
- verificar sua integridade;
- identificar sua entrada no manifesto;
- reconstruir o consolidado por meio de código;
- rastrear cada valor analítico até a fonte original.

O produto infantil deverá ainda manter os dois totais avaliados, calcular cada
déficit com seu próprio denominador e proibir sua interpretação como categorias
mutuamente exclusivas.
