# Malha simplificada de apoio aos mapas

A malha foi obtida da API v4 do IBGE para apoiar os mapas do notebook de
sobreposição. Este é um arquivo geográfico adicional; as quatro bases
selecionadas da pesquisa continuam preservadas em `dados/pesquisa/`.

- `malha_municipal_simplificada.geojson`: resposta preservada da API, sem edição.
- `malha_municipal_simplificada.metadados.json`: URL completa, data de obtenção,
  hash SHA-256 e número de feições.

[Documentação oficial](https://servicodados.ibge.gov.br/api/docs/malhas?versao=4).

A API v4 não expõe parâmetro de ano. Por isso, não atribuir à malha o ano de
2025 apenas porque os indicadores analisados se referem a esse ano. O notebook
audita os códigos de sete dígitos e a correspondência por prefixos únicos, mas
essa verificação não harmoniza limites territoriais históricos.

Uso ilustrativo em coordenadas geográficas, sem cálculo de áreas, distâncias,
cobertura populacional ou testes de agrupamento espacial.
