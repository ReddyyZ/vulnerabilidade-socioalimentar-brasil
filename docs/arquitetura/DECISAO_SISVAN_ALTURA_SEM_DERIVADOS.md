# Decisão vigente: SISVAN de altura sem indicadores derivados na entrada

Decisão aprovada em 4 de outubro de 2026. Substitui o perfil anterior de coleta
conjunta de altura/peso e uso complementar de DPI.

1. Coleta padrão: Altura X Idade, crianças de 0 a <5 anos, 2025, 27 UFs.
2. Baixar novamente com o coletor atualizado, em diretórios exclusivos; não
   regenerar a entrada reutilizando os XLSX históricos.
3. Preservar cada XLSX exatamente; converter cabeçalhos multinível para CSV,
   mantendo valores das células e percentuais oficiais, sem normalizar escala.
4. Entrada SISVAN com 12 colunas territoriais/categorias/total. Ano, idade,
   fase, filtros, datas e hashes ficam no sidecar. Não calcular DAI no coletor.
5. Remover geração automática do produto infantil combinado. Peso/IMC e
   agregações explícitas continuam disponíveis como funcionalidades opcionais.
6. Interpretar contagens apenas na análise: preservar inteiros coerentes sem
   gerar alternativas uniformes ×1.000; conciliar soma e percentuais e exigir
   solução única nas linhas inconsistentes. A leitura das células é auditada.
7. Calcular DAI sem arredondamento no notebook; total zero produz ausência.
8. Excluir DPI e dados de peso de todas as tabelas, gráficos, controles,
   correlações, resumos, dicionário e exportações da análise vigente.
9. Manter IVS ≥0,401; IDHM <0,600; P75 nacional de CadInsan e DAI; mínimo
   principal 100 avaliações de altura; sensibilidade já aprovada.
10. Ativar somente a nova entrada em `dados/pesquisa`, atualizar hashes e
    pacote autocontido. Preservar produtos anteriores fora da pasta ativa.

Documentação da entrada, limitações numéricas e comando de reprodução:
[README SISVAN](../../dados/pesquisa/sisvan/README.md).

A nova coleta manteve as contagens interpretadas e a seleção histórica:
5.571 municípios, 7.846.413 avaliações de altura, 877.708 registros no numerador
DAI; 242 municípios com convergência dos quatro critérios no cenário padrão.
Esses resultados são analíticos, não colunas fornecidas no CSV de entrada.
