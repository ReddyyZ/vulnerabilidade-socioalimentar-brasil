# Bases selecionadas para a pesquisa

## Objetivo e recorte

> Identificar áreas do Brasil de maior risco alimentar e vulnerabilidade social a partir dos indicadores IVS, IDHM, CadÚnico e SISVAN.

Esta pasta reúne as bases municipais já disponíveis no projeto para essa análise,
incluindo CADINSAN como fonte complementar. O recorte nutricional selecionado é
**altura por idade e peso por idade de crianças de 0 a menos de 5 anos, em 2025**.

Organização realizada em **4 de outubro de 2026**. Os quatro arquivos de dados
são cópias integrais dos arquivos existentes: nenhum cabeçalho, valor, código,
formato ou categoria foi alterado nesta organização. Os arquivos de origem
continuam preservados. As bases ainda não foram cruzadas.

## Conteúdo

| Fonte | Arquivo | Registros municipais | Referência temporal | Papel na pesquisa |
|---|---|---:|---|---|
| IVS e IDHM | [atlasivs_municipios_2010.csv](ivs_idhm/atlasivs_municipios_2010.csv) | 5.565 | 2010, conforme identificação do arquivo | Vulnerabilidade social e desenvolvimento humano |
| CadÚnico | [municipios-cadunico.json](cadunico/municipios-cadunico.json) | 5.564 | Não informada no arquivo | Fonte municipal disponível; período e unidade precisam de confirmação |
| CADINSAN | [CADINSAN_2025_dados_municipais.csv](cadinsan/CADINSAN_2025_dados_municipais.csv) | 5.570 | 2025, conforme identificação do arquivo | Indicadores complementares e coluna `Cadastros_Cadunico` |
| SISVAN | [indicadores_altura_peso_idade_menores_5_2025.csv](sisvan/indicadores_altura_peso_idade_menores_5_2025.csv) | 5.571 | 2025 | Déficit de altura/estatura para idade (DAI) e déficit de peso para idade (DPI) |

**O IDHM já está no arquivo do IVS.** Não é necessário um segundo arquivo para
acessar suas variáveis. Este CSV contém `ivs`, suas três dimensões, `idhm` e
dimensões/componentes do IDHM.

O JSON do CadÚnico contém pares `código municipal: valor inteiro`, sem dicionário
de dados ou metadados temporais internos. Não assumir, apenas com esse arquivo,
que os valores são pessoas, famílias, cadastros ou beneficiários. Tampouco
substituí-los automaticamente pela coluna `Cadastros_Cadunico` do CADINSAN:
equivalência de unidade e período precisa ser demonstrada.

## Arquivos de origem e rastreabilidade

Os caminhos abaixo são relativos à raiz do repositório:

| Cópia nesta pasta | Arquivo de origem |
|---|---|
| `ivs_idhm/atlasivs_municipios_2010.csv` | `atlasivs_municipios_2010.csv` |
| `cadunico/municipios-cadunico.json` | `municipios-cadunico.json` |
| `cadinsan/CADINSAN_2025_dados_municipais.csv` | `CADINSAN_2025_dados_municipais.csv` |
| `sisvan/indicadores_altura_peso_idade_menores_5_2025.csv` | `dados/tratados/sisvan/criancas_menores_5/indicadores_altura_peso_idade_menores_5_2025.csv` |

As URLs registradas para os arquivos sociais estão em
[`fonte_dados.json`](../../fonte_dados.json). Elas apontam para cópias publicadas
no repositório `TriangulosTecnologia/cozsolidarias` no GitHub. Portanto, estes
arquivos sociais disponíveis no projeto não devem ser descritos como extrações
diretas feitas aqui nos portais oficiais. Confirmar metodologia, referência
temporal e documentação das fontes antes da análise final.

O SISVAN foi obtido do Relatório Público do Ministério da Saúde. A documentação
completa, com o dicionário das 28 colunas, filtros, fórmulas, limitações e
reprodutibilidade, está no
[README da base SISVAN](../tratados/sisvan/criancas_menores_5/README.md).
Os [metadados do produto](../tratados/sisvan/criancas_menores_5/indicadores_altura_peso_idade_menores_5_2025.metadados.json),
o [manifesto de coletas](../../metadados/manifestos/sisvan_coletas.csv) e os
XLSX oficiais permanecem nas camadas de origem do projeto.

O CSV consolidado do SISVAN é um **produto derivado**: combina dois índices e
calcula DAI e DPI. A fidelidade desta cópia ao CSV existente não a transforma
em uma exportação bruta do SISVAN.

## Leitura e integração territorial

| Fonte | Campo municipal | Formato observado |
|---|---|---|
| IVS/IDHM | `municipio` | Código de sete dígitos; não é o nome municipal |
| CadÚnico | Chaves do objeto JSON | Código de sete dígitos |
| CADINSAN | `Cod_IBGE` | Código de sete dígitos |
| SISVAN | `Código IBGE` | Código de seis dígitos |

Todos os códigos são únicos dentro de cada base selecionada. Armazenar códigos
como texto. A junção direta entre os campos de seis e sete dígitos não funciona.
Preparar uma correspondência territorial em uma etapa posterior, preservando
os códigos originais e verificando unicidade e municípios sem correspondência.

Uma conferência preliminar, comparando o código SISVAN com os **seis primeiros
dígitos** das outras bases, encontrou:

| Fonte comparada ao SISVAN | Correspondências | Municípios SISVAN ausentes nessa fonte |
|---|---:|---:|
| IVS/IDHM | 5.565 | 6 |
| CadÚnico | 5.564 | 7 |
| CADINSAN | 5.570 | 1 |

Os prefixos de seis dígitos são únicos em cada uma das três bases sociais. A
interseção preliminar dos quatro arquivos contém **5.564 municípios**. Esses
números são controles dos arquivos disponíveis, não uma validação completa da
compatibilidade das malhas territoriais. Uma junção interna reduziria a cobertura;
documentar perdas antes de decidir como integrar as fontes.

Os CSVs usam vírgula como delimitador. No IVS/IDHM há números com ponto decimal
e outros com vírgula decimal entre aspas. CADINSAN também contém percentuais
com vírgula decimal e o símbolo `%`. O CSV do SISVAN distingue percentuais
oficiais com `%` dos percentuais derivados numéricos. Tratar esses formatos
por coluna em código, sem editar os arquivos de entrada. Ler como UTF-8 com
suporte a BOM (`utf-8-sig`) para evitar alterações no primeiro cabeçalho.

## Cuidados para a análise

- IVS/IDHM de 2010 e SISVAN/CADINSAN de 2025 têm referências temporais diferentes.
  Justificar essa comparação; ela não descreve simultaneidade entre indicadores.
- Confirmar período e unidade do CadÚnico antes de utilizá-lo em indicadores.
  Uma contagem absoluta não permite calcular cobertura sem um denominador
  populacional compatível; esse denominador não está incluído nesta seleção.
- DAI e DPI têm denominadores próprios e não devem ser somados. O SISVAN se
  refere à população acompanhada e registrada, não automaticamente à população
  inteira do município.
- O município de Boa Esperança do Norte (MT) tem total avaliado zero nos dois
  índices. Os percentuais derivados `0.0` nessa linha devem ser tratados como
  ausência de observações para a análise, não como prevalência comprovadamente
  nula.
- Preservar as diferenças entre risco alimentar, vulnerabilidade social e estado
  nutricional; associações municipais não demonstram causalidade.

As decisões metodológicas mais amplas estão em
[`INFORMACOES_PARA_A_PESQUISA.md`](../../INFORMACOES_PARA_A_PESQUISA.md).

## Integridade e atualizações

Os hashes dos quatro arquivos estão em [SHA256SUMS](SHA256SUMS). Para conferir
a integridade desta seleção, executar na raiz do projeto:

```bash
cd dados/pesquisa
sha256sum -c SHA256SUMS
```

Esta pasta é uma seleção fixa dos dados já existentes. Novas coletas não
atualizam automaticamente estas cópias. Ao adotar dados novos, registrar a
nova versão, atualizar os hashes e revisar períodos e cobertura.

O IMC por idade, produtos legados, checkpoints e relatórios combinando consultas
distintas permanecem nas pastas de origem. Esta seleção acompanha o recorte
principal aprovado de altura e peso por idade em menores de cinco anos.
