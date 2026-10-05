# Decisão vigente: coleta de altura e peso para o notebook v3

Decisão aprovada em 5 de outubro de 2026. Substitui somente o perfil padrão
de altura isolada; mantém a fidelidade das entradas sem indicadores derivados.

1. Configuração padrão: `altura_por_idade` e `peso_por_idade`, crianças de
   `0_a_menor_5_anos`, ano 2025, abrangência nacional nas 27 UFs.
2. Gerar dois CSVs independentes, com categorias oficiais e `Total`, respectivos
   `.metadados.json`, XLSX originais e registros no manifesto.
3. Preservar valores das células, percentuais e categorias; somente achatar
   cabeçalhos multinível para CSV e reunir as UFs. Não normalizar escalas no coletor.
4. Não calcular DAI ou DPI, filtrar pelo mínimo de avaliações nem gerar
   automaticamente o produto infantil combinado. Essas operações nutricionais
   pertencem ao notebook: a v3 utiliza DAI + DPI na definição principal,
   com denominadores separados, e DAI isolado como comparação.
5. Preservar os seletores de indicadores, fases, faixas, ano e UFs, além das
   opções explícitas de concatenação, soma e harmonização. IMC continua opcional.
6. A atualização do padrão não executa coleta, não modifica bases existentes
   e não atualiza o pacote incorporado no notebook. Essas etapas são separadas.
7. Validar resolução das duas consultas, saídas separadas, seleção de apenas
   um indicador, parâmetros explícitos, ausência de DAI/DPI na entrada e
   simulação sem rede ou gravação de produtos.

Referências: [arquitetura](ARQUITETURA_DO_PROJETO.md),
[uso do coletor](../../dados/tratados/sisvan/README.md) e
[metodologia do notebook v3](../../notebooks/README.md).

A decisão anterior permanece como registro histórico em
[DECISAO_SISVAN_ALTURA_SEM_DERIVADOS.md](DECISAO_SISVAN_ALTURA_SEM_DERIVADOS.md).
