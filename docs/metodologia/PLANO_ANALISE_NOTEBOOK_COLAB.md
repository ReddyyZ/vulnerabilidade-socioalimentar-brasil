# Plano de análise e apresentação em notebook no Google Colab

**Data do planejamento:** 4 de outubro de 2026.

**Status:** estratégia inicial implementada no
[notebook de sobreposição](../../notebooks/01_sobreposicao_criterios.ipynb).
Este documento preserva o planejamento discutido. A implementação usa
percentil 75, cenário `com_PBF` e mínimo de 100 avaliações de altura como
parâmetros iniciais editáveis, com análise de sensibilidade. Essas escolhas
são exploratórias e precisam de justificativa metodológica. Unidades e períodos
das fontes sociais foram documentados com o catálogo e o relatório oficial.
Os percentuais do CadInsan são recalculados sem arredondamento, preservando os
valores do CSV e auditando a diferença na seleção.
O IDHM baixo também é obrigatório na sobreposição, por decisão da pesquisa:
P25 quando `QUANTIL = 0.75`, e P20 quando `QUANTIL = 0.80`. CadÚnico e DPI
permanecem contextuais. Não será produzido ranking composto.

## 1. Pergunta da pesquisa

> Identificar áreas do Brasil de maior risco alimentar e vulnerabilidade social
> a partir dos indicadores IVS, IDHM, CadÚnico, CadInsan e SISVAN.

Planejar um **estudo ecológico municipal**: comparar municípios e identificar
onde se sobrepõem vulnerabilidade social, risco alimentar estimado e déficits
nutricionais. Para a primeira apresentação ao laboratório, a estratégia
recomendada é uma análise descritiva com mapas e critérios explícitos de
prioridade.

O notebook deverá responder a três perguntas:

1. Onde cada indicador apresenta situações mais desfavoráveis?
2. Onde essas situações coincidem?
3. Quais municípios continuam aparecendo como prioritários quando mudamos os
   critérios de classificação?

## 2. Papel de cada fonte

| Fonte | Papel na análise | Variáveis iniciais |
|---|---|---|
| IVS | Vulnerabilidade social | IVS total; dimensões para aprofundamento |
| IDHM | Desenvolvimento humano | IDHM total; valores menores indicam situação mais desfavorável |
| CadÚnico | Dimensão da população cadastrada e demanda potencial | Pessoas cadastradas por município, junho/2026 |
| CadInsan | Risco estimado de insegurança alimentar grave | Proporção para comparar intensidade; quantidade para dimensionar demanda |
| SISVAN | Situação nutricional infantil registrada | DAI como resultado principal; DPI como complementar; respectivos denominadores |

O CadInsan estima risco entre famílias inscritas no CadÚnico. Portanto,
CadÚnico e CadInsan compartilham uma origem e não devem receber automaticamente
o tratamento de duas evidências independentes. Referência:
[descrição oficial do MDS](https://www.gov.br/mds/pt-br/Sisan/monitoramento-da-san/cadinsan).

O SISVAN reúne informações da população atendida na Atenção Primária. Seus
resultados devem ser apresentados como situação nutricional das crianças
acompanhadas, sem extrapolação automática para todas as crianças residentes.
Referência:
[Ministério da Saúde](https://www.gov.br/saude/pt-br/composicao/saps/vigilancia-alimentar-e-nutricional/sisvan).

O recorte nutricional aprovado é **altura por idade e peso por idade em crianças
de 0 a menos de 5 anos, em 2025**. DAI corresponde ao déficit de altura/estatura
para idade; DPI corresponde ao déficit de peso para idade.

## 3. Bases disponíveis

Os dados selecionados estão em [`dados/pesquisa/`](../../dados/pesquisa/).
A identificação, procedência, cobertura e integridade das cópias estão no
[README dessa seleção](../../dados/pesquisa/README.md).

| Arquivo | Conteúdo | Registros municipais |
|---|---|---:|
| `ivs_idhm/atlasivs_municipios_2010.csv` | IVS e IDHM | 5.565 |
| `cadunico/municipios-cadunico.json` | Pessoas cadastradas, junho/2026, conforme catálogo | 5.564 |
| `cadinsan/CADINSAN_2025_dados_municipais.csv` | Famílias em risco estimado e denominador em famílias, janeiro/2025 | 5.570 |
| `sisvan/indicadores_altura_peso_idade_menores_5_2025.csv` | Altura por idade, peso por idade, DAI e DPI | 5.571 |

Os caminhos da tabela são relativos a `dados/pesquisa/`. Os arquivos de entrada
devem permanecer preservados; limpeza, compatibilização e integração deverão
gerar uma base analítica separada.

## 4. Estrutura proposta do notebook

### 4.1 Pergunta, recorte e decisões metodológicas

Explicar a unidade municipal, o recorte infantil e o papel de cada indicador.
Registrar IVS/IDHM de 2010, SISVAN de 2025, CadInsan de janeiro/2025 e CadÚnico
de junho/2026. Essas diferenças temporais precisam aparecer na
interpretação dos resultados.

### 4.2 Carregamento e conferência das bases

Usar os arquivos de `dados/pesquisa/`, verificar hashes, apresentar quantidades
de registros e conferir tipos, ausências, duplicidades e extremos.

Para o Colab, prever carregamento de um pacote pelo Google Drive ou upload.
Fixar a versão dos dados evita resultados diferentes entre apresentações.

### 4.3 Construção da base municipal integrada

Compatibilizar códigos de seis e sete dígitos, preservando os códigos originais.
Manter municípios sem correspondência e produzir uma tabela das perdas por
fonte.

A conferência preliminar encontrou **5.564 municípios na interseção dos quatro
arquivos**, por comparação dos códigos SISVAN com os seis primeiros dígitos dos
códigos das outras fontes. Isso ainda não constitui validação completa da
compatibilidade territorial. Os demais municípios não devem ser excluídos
silenciosamente.

### 4.4 Descrição dos indicadores

Mostrar distribuições, mapas individuais e diferenças entre regiões. Separar
intensidade proporcional de quantidade absoluta: uma cidade grande pode
concentrar mais famílias em risco sem apresentar a maior proporção.

### 4.5 Comparação entre dimensões

Produzir gráficos de IVS × DAI, IDHM × DAI e CadInsan × DAI. Repetir as principais
comparações com DPI.

Uma matriz de correlação de Spearman pode mostrar associações e redundâncias.
Correlação municipal não demonstra causalidade nem relações individuais.

### 4.6 Identificação de municípios prioritários

Aplicar regras transparentes, apresentar os grupos resultantes e mostrar por
que cada município foi selecionado. A estratégia inicial recomendada está
descrita na seção 5.1.

### 4.7 Análise de sensibilidade

Alterar pontos de corte e exigências de denominador, verificando quais
municípios permanecem selecionados. Registrar também quantos municípios deixam
de ser elegíveis quando os parâmetros mudam.

### 4.8 Resultados e exportação

Gerar uma tabela municipal, figuras para apresentação e uma síntese escrita com
achados, limitações e próximos passos. Cada figura deve ter uma pequena
interpretação em Markdown.

## 5. Caminhos para identificar prioridades

### 5.1 Sobreposição de critérios — estratégia inicial recomendada

Definir critérios explícitos para cada dimensão. Por exemplo, considerar
inicialmente como “elevado” estar no quartil mais desfavorável da distribuição
nacional.

Uma regra **exploratória** poderia selecionar municípios com:

```text
IVS elevado
+ IDHM baixo
+ CadInsan proporcional elevado
+ DAI elevado
+ denominador nutricional que satisfaça o critério adotado
```

O símbolo `+` representa a coincidência dos critérios, não a soma numérica dos
indicadores.

O IDHM baixo é um quarto critério obrigatório, não apenas contextual. A maior
restrição é intencional: selecionar a coincidência de vulnerabilidade social,
baixo desenvolvimento humano, risco alimentar estimado e déficit de altura.
IVS e IDHM não são tratados como evidências independentes; sua associação é
avaliada nos gráficos e correlações. DPI acrescenta uma segunda leitura
nutricional; CadÚnico dimensiona as pessoas cadastradas em junho/2026, sem
substituir o denominador de famílias do CadInsan nem medir cobertura populacional.

O corte do IDHM é o percentil `100 × (1 − QUANTIL)` de todos os municípios
com IDHM disponível, incluindo empates pelo operador `≤`. Não se altera o
valor original. Ausência de IDHM impede a classificação principal. Com os
parâmetros padrão, há 218 municípios selecionados, contra 274 na regra anterior
de três critérios; 56 deixam de ser selecionados por não atenderem ao IDHM baixo.

Além dos municípios com convergência dos quatro sinais, apresentar:

- municípios com IVS elevado, IDHM baixo e risco alimentar elevado, sem DAI
  elevado;
- municípios com DAI elevado fora desse grupo;
- municípios cuja informação é insuficiente para a classificação.
- outras combinações dos quatro critérios.

Esses perfis podem gerar uma discussão mais rica do que uma lista única dos
“piores municípios”. A ausência de DAI elevado não elimina a possibilidade de
risco alimentar.

Os cortes por quartis seriam **critérios relativos da pesquisa**, não limites
oficiais de risco. Testar também, por exemplo, o quinto mais desfavorável da
distribuição na análise de sensibilidade.
Nessa comparação, P75/P80 para IVS, CadInsan e DAI correspondem a P25/P20
para IDHM. As 12 especificações atuais selecionam de 132 a 245 municípios.

### 5.2 Índice composto — alternativa para etapa posterior

Alternativa não adotada na estratégia atual, que permanece sem ranking.

Um índice composto facilitaria um ranking, mas exigiria justificar variáveis,
padronização e pesos. IVS e IDHM podem carregar informação semelhante; CadInsan
já utiliza características do CadÚnico. Uma média simples pode dar peso
excessivo a dimensões repetidas.

Deixar esse caminho para depois da análise das correlações e testar diferentes
especificações. O próprio Ipea discute a relação entre IVS e IDHM:
[estudo metodológico do Ipea](https://repositorio.ipea.gov.br/bitstream/11058/8257/2/vulnerability.pdf).

### 5.3 Análise espacial — aprofundamento

Depois de mapear os resultados, investigar agrupamentos de municípios vizinhos
com valores elevados. Isso exige uma malha territorial e decisões sobre
vizinhança e testes estatísticos.

Tratar como aprofundamento, após consolidar a análise principal. A malha deve
ser compatível com os códigos e períodos utilizados. Referência:
[malhas municipais do IBGE](https://www.ibge.gov.br/geociencias/organizacao-do-territorio/estrutura-territorial/15774-malhas).

## 6. Decisões pendentes e cuidados metodológicos

### 6.1 CadÚnico

O catálogo documenta o JSON como **pessoas cadastradas em junho/2026**,
campo `cadun_qtd_pessoas_cadastradas_i`, `anomes:202606`. O hash corresponde
exatamente ao arquivo usado. Para calcular proporções, ainda será necessário
um denominador compatível.

Esses valores não substituem `Cadastros_Cadunico` do CADINSAN, cujo denominador
é de **famílias** no universo analisado, com referência em janeiro/2025.

### 6.2 CadInsan

As definições do catálogo e do relatório oficial documentam os cenários:
`com_PBF` considera o efeito do benefício na renda; `sem_PBF` desconsidera esse
efeito em um cenário contrafactual. Não são grupos separados de famílias
beneficiárias e não beneficiárias. A fonte estima risco de insegurança
alimentar grave, sem medir diretamente todos os domicílios municipais.

Referência:
[relatório CadInsan com referência janeiro/2025](https://www.gov.br/mds/pt-br/Sisan/vigilancia-do-sisan/CADINSAN2025.pdf).

O cenário `com_PBF` integra a análise principal; `sem_PBF` entra na sensibilidade.
Os percentuais são recalculados sem arredondamento a partir dos absolutos e do
denominador em famílias, conforme o procedimento descrito no catálogo do
repositório de origem. Os valores proporcionais do CSV ficam preservados em
colunas próprias, com auditoria dos cortes e municípios que mudam de seleção.

### 6.3 SISVAN

- Manter DAI e DPI separados e preservar seus denominadores próprios.
- Não somar os déficits: os dados municipais não identificam sua interseção
  individual.
- Tratar denominador zero como ausência de observações. Na base disponível,
  percentuais derivados `0.0` nessas linhas não demonstram prevalência nula.
- Testar diferentes denominadores mínimos, com justificativa.
- Um número elevado de registros, sozinho, não garante representatividade.
- Ao agregar DAI ou DPI por região, somar numeradores e denominadores antes de
  calcular o percentual; não usar a média simples dos percentuais municipais.

O dicionário, fórmulas, filtros e limitações estão no
[README da base SISVAN](../../dados/tratados/sisvan/criancas_menores_5/README.md).

### 6.4 Tempo, território e dados adicionais

- Justificar a comparação entre o contexto social de 2010, CadInsan de
  janeiro/2025, SISVAN de 2025 e CadÚnico de junho/2026; não apresentá-los como
  observações simultâneas.
- Documentar correspondências territoriais e municípios sem dados por fonte.
- Acrescentar arquivos geográficos para os mapas.
- Para medir cobertura do SISVAN, obter um denominador populacional da mesma
  faixa etária e de período compatível.

## 7. Roteiro da apresentação ao laboratório

Priorizar os seguintes produtos:

1. Pergunta da pesquisa, recorte e papel de cada fonte.
2. Mapa de disponibilidade dos dados e controle das correspondências municipais.
3. Mapas de IVS, IDHM, CadInsan e DAI.
4. Um gráfico de associação entre dimensões.
5. Mapa de sobreposição dos critérios adotados.
6. Tabela de municípios selecionados, com valores e denominadores.
7. Comparação entre critérios na análise de sensibilidade.
8. Limitações e decisões necessárias para as próximas etapas.

## 8. Forma esperada da conclusão

Preencher somente após a análise:

> Foram identificados municípios com convergência de vulnerabilidade social, baixo desenvolvimento humano,
> risco alimentar estimado e déficit de crescimento infantil registrado no
> SISVAN. A seleção permaneceu estável — ou variou — sob diferentes critérios.

Relacionar essa conclusão aos critérios utilizados, à cobertura das fontes e
às limitações temporais e populacionais. A identificação de prioridades deve
ser apresentada como resultado da estratégia analítica adotada.

## 9. Encaminhamento recomendado

Desenvolver primeiro o notebook de **descrição e sobreposição**, com análise de
sensibilidade incorporada. Esse produto pode responder à pergunta e sustentar
uma discussão metodológica com os colegas do laboratório.

O índice composto e a análise espacial ficam como aprofundamentos. As decisões
mais amplas da pesquisa estão registradas em
[`INFORMACOES_PARA_A_PESQUISA.md`](../../INFORMACOES_PARA_A_PESQUISA.md).
