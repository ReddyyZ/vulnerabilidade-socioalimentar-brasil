"""Cria uma nova versão autocontida sem sobrescrever a primeira versão."""

from __future__ import annotations

import ast
import base64
import copy
import hashlib
import io
import json
import textwrap
import zipfile
from pathlib import Path

import nbformat

from scripts.analise_sobreposicao_v2 import DATA_FILES, CATALOGUE_DATASETS

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT / "notebooks/01_sobreposicao_criterios.ipynb"
NOTEBOOK = ROOT / "notebooks/01_sobreposicao_criterios_v2.ipynb"
SHARED_NAMES = {"UF_REGIONS", "numeric", "codes", "check_range", "interpret_sisvan_counts",
                "figure_style", "save_figure", "geometry_audit", "map_figure"}


def analysis_source():
    """Incorpora só os auxiliares necessários; nenhum import do projeto no Colab."""
    original = (ROOT / "scripts/analise_sobreposicao.py").read_text()
    fragments = []
    for node in ast.parse(original).body:
        name = node.name if isinstance(node, ast.FunctionDef) else (
            node.targets[0].id if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) else None)
        if name in SHARED_NAMES:
            fragment = ast.get_source_segment(original, node)
            fragment = fragment.replace("# Regra aprovada: não extrapolar inteiros cuja soma e percentuais conferem.",
                                        "# Mantém as contagens inteiras quando soma e percentuais conferem.")
            fragments.append(fragment)
    source = (ROOT / "scripts/analise_sobreposicao_v2.py").read_text()
    node = next(n for n in ast.parse(source).body if isinstance(n, ast.ImportFrom) and n.module == "scripts.analise_sobreposicao")
    imports = ast.get_source_segment(source, node)
    return source.replace(imports, "from decimal import Decimal, InvalidOperation\n\n" + "\n\n".join(fragments))


def payload_bytes():
    paths = {relative: ROOT / "dados/pesquisa" / relative for relative in DATA_FILES.values()}
    paths[DATA_FILES["sisvan_peso"]] = ROOT / "dados/tratados/sisvan/peso_por_idade" / Path(DATA_FILES["sisvan_peso"]).name
    files = {relative: path.read_bytes() for relative, path in paths.items()}
    for source in ("sisvan_altura", "sisvan_peso"):
        relative, path = DATA_FILES[source], paths[DATA_FILES[source]]
        files[str(Path(relative).with_suffix(".metadados.json"))] = path.with_suffix(".metadados.json").read_bytes()
    files["SHA256SUMS"] = ("\n".join(f"{hashlib.sha256(data).hexdigest()}  {relative}" for relative, data in sorted(files.items())
                                    if relative in DATA_FILES.values()) + "\n").encode()
    catalogue = json.loads((ROOT / "dataset_catalogue.json").read_text())
    # Extrato explícito: mantém os registros das duas fontes usadas, sem o dataset excluído.
    filtered = {"catalog": catalogue["catalog"], "schema_version": catalogue["schema_version"],
                "datasets": {key: catalogue["datasets"][key] for key in CATALOGUE_DATASETS.values()},
                "extrato": {"catalogo_original_sha256": hashlib.sha256((ROOT / "dataset_catalogue.json").read_bytes()).hexdigest(),
                            "datasets_incluidos": list(CATALOGUE_DATASETS.values())}}
    files["documentacao/dataset_catalogue.json"] = (json.dumps(filtered, ensure_ascii=False, indent=2) + "\n").encode()
    for name in ("malha_municipal_simplificada.geojson", "malha_municipal_simplificada.metadados.json"):
        files[f"apoio/ibge/{name}"] = (ROOT / "dados/apoio/ibge" / name).read_bytes()
    files["README.md"] = ("# Entradas da análise v2\n\nIVS/IDHM e CadInsan: cópias exatas dos CSVs obtidos do repositório "
                           "Cozinhas Solidárias. SISVAN altura: coleta de 4/10/2026 à tarde; "
                           "SISVAN peso: coleta já existente, consolidada em 4/10/2026 pela manhã. "
                           "Ambos: 2025, crianças de 0 a menos de 5 anos, 27 UFs. "
                           "DAI e DPI são recalculados no notebook a partir das categorias, nunca lidos de indicadores antigos. "
                           "Os arquivos originais não foram alterados. SHA256SUMS identifica as quatro entradas; "
                           "o catálogo é um extrato das duas fontes sociais, com hash do catálogo original.\n").encode()
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for relative, data in sorted(files.items()):
            info = zipfile.ZipInfo(relative, date_time=(2026, 10, 5, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)
    return stream.getvalue()


def build():
    previous = nbformat.read(ORIGINAL, as_version=4)
    original_hash = hashlib.sha256(ORIGINAL.read_bytes()).hexdigest()
    notebook = nbformat.v4.new_notebook(metadata=copy.deepcopy(previous.metadata))
    notebook.metadata["colab"]["name"] = NOTEBOOK.name
    notebook.metadata["origem_v1_sha256"] = original_hash
    cells = []

    def md(source):
        cells.append(nbformat.v4.new_markdown_cell(textwrap.dedent(source).strip()))

    def code(source, hidden=False):
        cell = nbformat.v4.new_code_cell(textwrap.dedent(source).strip())
        if hidden:
            cell.metadata.update({"cellView": "form", "jupyter": {"source_hidden": True}})
        cells.append(cell)
        return cell

    source = analysis_source()
    source_hash = hashlib.sha256(source.encode()).hexdigest()
    md("""
    # Risco alimentar e vulnerabilidade social no Brasil — versão 2

    **Pergunta:** em quais municípios brasileiros os sinais de vulnerabilidade
    social estrutural, risco de insegurança alimentar e vulnerabilidade nutricional
    infantil aparecem simultaneamente?

    Este estudo ecológico municipal utiliza IVS, IDHM, CadInsan e SISVAN em
    **três dimensões**. IVS e IDHM compõem juntos a dimensão social; CadInsan,
    a alimentar; DAI, a nutricional. DPI é complementar. A classificação
    identifica convergência, **não um ranking, diagnóstico municipal de fome
    ou relação causal**. Cada município é uma unidade; não se combinam
    pessoas e famílias em um único denominador.
    """)
    md("""
    ## 1. Fontes de dados e procedência

    | Entrada | Instituição / fonte original | Arquivo utilizado e obtenção | Referência / população |
    |---|---|---|---|
    | IVS e IDHM | [Atlas IVS/Ipea](https://repositorio.ipea.gov.br/handle/11058/4381); [Atlas Brasil/PNUD, Ipea e FJP](https://www.undp.org/pt/brazil/desenvolvimento-humano/atlas-do-desenvolvimento-humano-no-brasil) | [CSV de Cozinhas Solidárias](https://raw.githubusercontent.com/TriangulosTecnologia/cozsolidarias/refs/heads/main/src/data-source-static/data/atlasivs_municipios_2010.csv), 5.565 municípios | 2010; índices municipais |
    | CadInsan | [MDS, relatório 2025](https://www.gov.br/mds/pt-br/Sisan/vigilancia-do-sisan/CADINSAN2025.pdf) | [CSV de Cozinhas Solidárias](https://raw.githubusercontent.com/TriangulosTecnologia/cozsolidarias/refs/heads/main/src/data-source-static/data/CADINSAN_2025_dados_municipais.csv), 5.570 municípios | Janeiro/2025; famílias do universo analisado |
    | SISVAN — Altura X Idade | [Ministério da Saúde, relatórios públicos](https://sisaps.saude.gov.br/sisvan/relatoriopublico/) | CSV municipal da coleta direta de 4/10/2026, consolidada à tarde; 5.571 municípios | 2025; crianças de 0 a menos de 5 anos acompanhadas pelo sistema |
    | SISVAN — Peso X Idade | Ministério da Saúde, mesmos relatórios públicos | CSV municipal da coleta já disponível, consolidada em 4/10/2026 pela manhã; 5.571 municípios | 2025; mesmo recorte etário e 27 UFs |

    As **duas entradas sociais** foram obtidas do repositório de
    [Cozinhas Solidárias](https://github.com/TriangulosTecnologia/cozsolidarias),
    não extraídas diretamente dos portais oficiais nesta pesquisa. Seus hashes
    são conferidos contra os respectivos registros do catálogo fornecido com elas.
    Os dois CSVs nutricionais e seus metadados são reutilizados sem modificar
    os arquivos do projeto. DAI e DPI são calculados aqui; a antiga base combinada
    com indicadores derivados não é utilizada.

    **Por que não há uma entrada adicional do CadÚnico?** O CadInsan já utiliza
    famílias inscritas nesse cadastro. Para esta estratégia, acrescentar apenas
    o número absoluto de pessoas cadastradas repetiria parte do contexto conceitual
    e refletiria fortemente o tamanho populacional. Essa é uma decisão da análise,
    não uma afirmação de que todas as variáveis do CadÚnico sejam redundantes.
    O denominador de famílias do próprio CSV CadInsan continua necessário.

    A malha simplificada é da [API v4 do IBGE](https://servicodados.ibge.gov.br/api/docs/malhas?versao=4),
    incorporada com hash e metadados. A API usada não identifica seu ano: os mapas
    são apoio ilustrativo, não prova de harmonização dos limites entre 2010 e 2025.

    **Como reproduzir:** abrir este arquivo no Google Colab e selecionar
    **Ambiente de execução → Executar tudo**. Entradas, código e malha estão
    incorporados; não é necessário ter os demais arquivos do projeto ou credenciais.
    Apenas a instalação inicial de bibliotecas pode precisar de internet.
    """)
    md("""
    ## 2. Indicadores, dimensões e escolhas metodológicas

    **Social:** IVS descreve infraestrutura urbana, capital humano e renda/trabalho;
    quanto maior, maior a vulnerabilidade. É publicado como média dos três
    subíndices. IDHM sintetiza longevidade, educação e renda por média geométrica
    de seus índices; quanto menor, menor o desenvolvimento. Ambos são lidos da
    fonte, não reconstruídos a partir de microdados. A dimensão exige
    **IVS ≥ 0,401 E IDHM < 0,600**: faixas alta/muito alta do IVS/Ipea e
    baixo/muito baixo desenvolvimento adotado aqui. IDHM igual a 0,600 não entra.
    São aspectos relacionados; a correlação de Spearman será medida, e não
    se contam os dois como dimensões independentes.

    **Alimentar:** CadInsan estima risco de insegurança alimentar grave entre
    famílias do universo analisado, não mede diretamente fome em todas as famílias
    residentes. Utiliza-se **CadInsan ≥ P75 nacional**. P75 é uma escolha
    distributiva/exploratória, **não um corte oficial**: identifica o quartil superior
    municipal, aproximadamente 25% dos municípios válidos, com empates incluídos.
    Cada município recebe o mesmo peso; não são 25% da população. O quantil
    é calculado antes de filtrar pelos critérios sociais ou nutricionais.

    `com_PBF` considera o efeito do Bolsa Família na renda; `sem_PBF` é o
    contrafactual que desconsidera esse efeito. Não são grupos de beneficiários
    versus não beneficiários. O CSV é referente a famílias com cadastro atualizado
    nos últimos 12 meses, em janeiro/2025.

    **Nutricional:** utiliza-se **DAI ≥ 6,7% com pelo menos 20 avaliações de altura**.
    A referência vem dos critérios de inclusão do
    [Mapa InSAN 2017–2022, seção de mapeamento, tabela 2](https://www.gov.br/mds/pt-br/Sisan/monitoramento-da-san/MapaInSAN_20172022.pdf).
    Seus limiares de DAI (6,7%) e DPI (1,8%) retomam a PNDS 2006; a exclusão
    de municípios com menos de 20 acompanhamentos é um precedente operacional.
    Não são novos limites clínicos da OMS nem garantia de precisão amostral.

    **Adaptação, não reprodução do Mapa InSAN:** o Mapa se refere a crianças
    beneficiárias do PBF e utiliza também agrupamento estatístico. Aqui os relatórios
    não filtram exclusivamente esse público, DAI é o critério principal e não há
    clusterização. A comparação DAI+DPI exige os mínimos separadamente em cada
    relatório, sem afirmar que seus denominadores representam as mesmas crianças.
    DPI permanece complementar e não interfere na seleção principal.
    """)
    code("""
    QUANTIL_CADINSAN = 0.75
    CORTE_DAI = 6.7  # porcentagem; referência metodológica do Mapa InSAN
    CORTE_DPI = 1.8  # porcentagem; indicador complementar
    MINIMO_AVALIADOS = 20
    CENARIO_CADINSAN = "com_PBF"
    QUANTIS_SENSIBILIDADE = [0.70, 0.75, 0.80, 0.90]
    MINIMOS_SENSIBILIDADE = [20, 50, 100]
    CORTES_DAI_SENSIBILIDADE = [6.7, 10.0, "P75"]
    CENARIOS_SENSIBILIDADE = ["com_PBF", "sem_PBF"]
    GERAR_MAPAS = True
    BAIXAR_RESULTADOS_NO_COLAB = False
    """)
    md("""
    ### Preparação do ambiente

    As células técnicas recolhidas preparam bibliotecas e recuperam as entradas.
    Os resultados ficam separados dos arquivos da fonte. Contagens, índices e
    percentuais são apresentados no padrão brasileiro; `—` indica ausência.
    A formatação de tabelas não altera valores, cálculos ou CSVs exportados.
    """)
    setup = previous.cells[5].source.split("CODIGO_ANALISE_SHA256 =", 1)[0]
    setup = setup.replace('"resultados_sobreposicao"', '"resultados_sobreposicao_v2"')
    setup = setup.replace('"cadastros_cadunico_cadinsan", "cadunico_pessoas_2026_06",',
        '"familias_cadinsan", "convergencia_total", "entram_vs_principal", "saem_vs_principal",\n'
        '    "municipios_dim_alimentar", "municipios_dim_nutricional", "dai_isolado", "dai_e_dpi",\n'
        '    "convergencia_dai", "convergencia_dai_dpi",')
    setup = setup.replace('["cadinsan", "dai"]', '["cadinsan", "dai", "dpi"]')
    code(setup + f'\nCODIGO_ANALISE_SHA256 = "{source_hash}"', hidden=True)
    # Preserva o extrator seguro da primeira versão, substituindo somente seu pacote.
    extractor = previous.cells[6].source
    encoded = base64.b64encode(payload_bytes()).decode()
    lines = extractor.splitlines()
    lines = [f'PACOTE_BASE64 = "{encoded}"' if line.startswith("PACOTE_BASE64 =") else line for line in lines]
    code("\n".join(lines), hidden=True)
    code("# @title Funções de análise — executar sem editar\n" + source, hidden=True)
    md("""
    ## 3. Integração, códigos IBGE e qualidade dos dados

    A união externa preserva todos os municípios encontrados, inclusive aqueles
    sem alguma fonte. O SISVAN usa códigos de seis dígitos; as fontes sociais,
    sete. Usa-se o prefixo único de seis, verificando duplicatas e conflitos de
    códigos e UFs. `codigo_ibge_7` conserva o código social quando disponível;
    `codigo_ibge` mantém o prefixo original se o sétimo dígito não é conhecido.
    Nenhum dígito verificador é inventado.

    As verificações de integridade já existentes (hashes, esquema, categorias,
    soma das contagens e leitura dos percentuais) são preservadas. Não se acrescenta
    uma seção de comparação entre DAI por contagens e DAI por percentuais oficiais.
    Ausência de informação nunca é substituída por zero.
    """)
    code("""
    validacao_catalogo, proveniencia_catalogo = validate_catalogue(
        PASTA_DADOS / "documentacao/dataset_catalogue.json", PASTA_DADOS)
    base, controle_integracao, hashes_entrada = prepare_base(PASTA_DADOS)
    figure_style()
    display(tabela_br(controle_integracao))
    colunas_fontes = ["tem_ivs_idhm", "tem_cadinsan", "tem_sisvan_altura", "tem_sisvan_peso"]
    ausencias = base.loc[~base[colunas_fontes].all(axis=1),
        ["codigo_ibge", "municipio", "uf"] + colunas_fontes]
    display(tabela_br(ausencias))
    qualidade_sisvan = pd.DataFrame([
        {"relatorio": label, "controle": control, "municipios": int(mask.sum())}
        for label, total, indicator in [("Altura X Idade", "avaliados_altura", "dai_pct"),
                                         ("Peso X Idade", "avaliados_peso", "dpi_pct")]
        for control, mask in [("Sem avaliações", base[total].eq(0)),
                              ("Abaixo do mínimo principal", base[total].between(1, MINIMO_AVALIADOS - 1)),
                              ("Indicador ausente", base[indicator].isna())]])
    display(tabela_br(qualidade_sisvan))
    interpretacao_sisvan = base[["codigo_ibge", "municipio", "uf"] +
        [c for c in base if c.endswith(("_valor_fonte", "_percentual_fonte", "_escala_alterada", "_escalas_compativeis"))]].copy()
    """)
    md(r"""
    ## 4. Construção dos indicadores

    $$CadInsan(\%)=100\times\frac{\text{famílias em risco estimado no cenário escolhido}}
    {\text{famílias no universo analisado pelo CadInsan}}$$

    $$DAI(\%)=100\times\frac{N(\text{altura muito baixa para idade})+N(\text{altura baixa para idade})}
    {N(\text{avaliados em altura por idade})}$$

    $$DPI(\%)=100\times\frac{N(\text{peso muito baixo para idade})+N(\text{peso baixo para idade})}
    {N(\text{avaliados em peso por idade})}$$

    DAI é o **déficit de altura para idade** e DPI, o **déficit de peso para idade**,
    em crianças de 0 a menos de cinco anos. Utilizam-se as categorias já
    classificadas pelo SISVAN, sem calcular escores-Z ou ligar microdados individuais.
    Os denominadores de altura e peso são mantidos separados.

    CadInsan é recalculado sem arredondamento; seus percentuais de origem ficam
    em colunas próprias. Denominador zero produz indicador indefinido (`NaN`),
    não percentual zero. Os índices IVS e IDHM permanecem como publicados.
    A tabela abaixo descreve a união das fontes, antes da seleção.
    """)
    code("""
    descritivas = base[["ivs", "idhm", "cadinsan_pct_com_PBF", "cadinsan_pct_sem_PBF",
                       "dai_pct", "dpi_pct", "avaliados_altura", "avaliados_peso"]].describe().T
    display(tabela_br(descritivas))
    totais_nutricionais = pd.DataFrame([
        {"indicador": label.upper(), "numerador": base[label + "_n"].sum(),
         "denominador": base.loc[base[label + "_n"].notna(), total].sum(),
         "percentual_agregado": base[label + "_n"].sum() /
            base.loc[base[label + "_n"].notna(), total].sum() * 100}
        for label, total in [("dai", "avaliados_altura"), ("dpi", "avaliados_peso")]])
    display(tabela_br(totais_nutricionais))
    """)
    md("""
    **Interpretação:** o percentual agregado é a razão entre somas, não a média
    municipal. Muitos acompanhamentos não garantem representatividade. Sem
    denominador demográfico compatível de menores de cinco anos, não se calcula
    cobertura populacional. Altura e peso não devem ser somados como pessoas distintas.
    """)
    md("""
    ## 5. As três dimensões e a sobreposição

    | Dimensão | Condição desfavorável principal |
    |---|---|
    | Social (`dim_social`) | IVS ≥ 0,401 **e** IDHM < 0,600 |
    | Alimentar (`dim_alimentar`) | CadInsan ≥ P75 nacional |
    | Nutricional (`dim_nutricional`) | DAI ≥ 6,7% com ≥20 avaliações de altura |

    O mínimo de 20 reduz o uso de denominadores extremamente pequenos, mas não
    elimina instabilidade: com 20 avaliados, uma criança altera o percentual em
    cinco pontos. Por isso são testados mínimos de 50 e 100.

    A quantidade de dimensões desfavoráveis varia de **0 a 3**, somente quando
    todas são conhecidas. Os rótulos são descritivos e não uma classificação oficial:
    0 = sem sinais pelos critérios adotados; 1 = atenção; 2 = prioridade alta;
    3 = prioridade muito alta. **Zero não significa ausência de insegurança alimentar**;
    significa que nenhum dos três critérios dimensionais foi satisfeito.
    Uma dimensão desconhecida implica **dados insuficientes** na classificação geral,
    sem ocultar os sinais conhecidos nas demais flags.

    DPI ausente ou com poucas avaliações impede apenas sua classificação
    complementar e a comparação DAI+DPI, não a seleção principal baseada em DAI.
    """)
    code("""
    classificados, cortes = classify(base, QUANTIL_CADINSAN, MINIMO_AVALIADOS,
                                     CENARIO_CADINSAN, CORTE_DAI, CORTE_DPI)
    display(tabela_br(cortes))
    resumo_social = classificados["social_status"].value_counts().rename_axis("social_status").reset_index(name="municipios")
    display(tabela_br(resumo_social))
    classes = classificados["classe_prioridade"].value_counts().reindex(
        list(PRIORITY_LABELS.values()) + ["dados insuficientes"], fill_value=0)
    resumo_classes = classes.rename_axis("classe_prioridade").reset_index(name="municipios")
    display(tabela_br(resumo_classes))
    sem_classificacao = classificados.loc[~classificados["elegivel_principal"],
        ["codigo_ibge", "municipio", "uf", "avaliados_altura", "motivo_nao_classificacao"]]
    display(tabela_br(sem_classificacao))
    comparacao_arredondamento, cortes_percentuais_csv = compare_rounding(
        base, classificados, QUANTIL_CADINSAN, MINIMO_AVALIADOS, CENARIO_CADINSAN, CORTE_DAI)
    total_com_csv = int(comparacao_arredondamento["selecionado_percentual_csv"].sum())
    total_recalculado = int(classificados["convergencia_total"].sum())
    display(Markdown(f"**Arredondamento CadInsan:** {total_com_csv} selecionados usando os percentuais "
                     f"do CSV; {total_recalculado} usando as razões sem arredondamento."))
    display(tabela_br(comparacao_arredondamento.loc[comparacao_arredondamento["mudou_selecao"]]))
    """)
    md("""
    ## 6. Convergência total e distribuição geográfica

    `convergencia_total = dim_social & dim_alimentar & dim_nutricional`.
    A lista responde onde os sinais das três dimensões coincidem. Ordena-se
    por UF e município, sem ranking. O percentual nacional usa como denominador
    **os municípios presentes na malha de apoio do IBGE**; também se informa
    o percentual entre elegíveis e eventuais selecionados fora dessa malha.
    O universo é explicitado, sem presumir que todos os períodos têm o mesmo
    número de municípios. As tabelas por UF/região têm denominadores próprios.
    """)
    code("""
    caminho_malha = PASTA_DADOS / "apoio/ibge/malha_municipal_simplificada.geojson"
    metadados_malha = json.loads((PASTA_DADOS / "apoio/ibge/malha_municipal_simplificada.metadados.json").read_text())
    if hashlib.sha256(caminho_malha.read_bytes()).hexdigest() != metadados_malha["sha256"]:
        raise ValueError("Hash da malha diferente do registrado")
    geometria = json.loads(caminho_malha.read_text())
    controle_geometria = geometry_audit(geometria, base)
    universo_ibge = {str(f["properties"]["codarea"])[:6] for f in geometria["features"]}
    convergentes = classificados.loc[classificados["convergencia_total"].fillna(False)].sort_values(["uf", "municipio"])
    selecionados_na_malha = int(convergentes["codigo_ibge_6"].isin(universo_ibge).sum())
    elegiveis = int(classificados["elegivel_principal"].sum())
    resumo_nacional = pd.DataFrame([{
        "municipios": len(base), "municipios_malha_ibge": len(universo_ibge), "elegiveis": elegiveis,
        "convergencia_total": len(convergentes), "selecionados_na_malha": selecionados_na_malha,
        "selecionados_fora_malha": len(convergentes) - selecionados_na_malha,
        "pct_convergencia_brasil_malha": selecionados_na_malha / len(universo_ibge) * 100,
        "pct_convergencia_elegiveis": len(convergentes) / elegiveis * 100 if elegiveis else np.nan}])
    display(tabela_br(resumo_nacional))
    colunas_selecao = {"municipio": "Município", "uf": "UF", "ivs": "IVS", "idhm": "IDHM",
        "cadinsan_pct": "CadInsan (%)", "dai_pct": "DAI (%)", "avaliados_altura": "Avaliações de altura",
        "familias_cadinsan": "Famílias no universo CadInsan", "cadinsan_n": "Famílias em risco estimado"}
    display(tabela_br(convergentes[list(colunas_selecao)].rename(columns=colunas_selecao).head(30)))
    print("Prévia de 30 municípios; a lista completa será exportada.")
    resumo_uf = geographic_summary(classificados, "uf")
    resumo_regional = geographic_summary(classificados, "regiao")
    display(tabela_br(resumo_uf))
    display(tabela_br(resumo_regional))
    """)
    md("""
    **Interpretação:** diferenciar a quantidade selecionada do percentual em cada
    área. Uma região com mais municípios pode ter mais selecionados sem maior
    proporção. DAI/DPI agregados das tabelas regionais usam todos os registros
    válidos da área, não apenas os selecionados nem apenas aqueles acima do mínimo.
    Não são prevalências representativas de todas as crianças residentes.
    """)
    md("""
    ## 7. DAI por faixas OMS e comparação com DPI

    As [faixas de prevalência de baixa estatura da OMS/UNICEF](https://www.who.int/data/nutrition/nlis/info/malnutrition-in-children)
    permitem descrever a magnitude do DAI: **<2,5% muito baixa; 2,5 a <10% baixa;
    10 a <20% média; 20 a <30% alta; ≥30% muito alta**. São categorias de
    prevalência, não diagnósticos individuais. Sua aplicação aos acompanhados pelo
    SISVAN é descritiva, sem assegurar representatividade municipal.

    Essas faixas não substituem o critério principal de **6,7%**; este pode ser
    atendido dentro da categoria OMS “baixa”. Municípios sem DAI ou abaixo do
    mínimo aparecem como dados insuficientes, e não como categoria muito baixa.

    A alternativa nutricional exige **DAI ≥6,7% E DPI ≥1,8%**, com pelo menos
    20 avaliações **em cada relatório**. Mostram-se a comparação em todo o universo
    válido para DAI e em um universo comum com ambos os denominadores válidos.
    Assim é possível distinguir o efeito do critério adicional do efeito da falta
    de informação de peso. A alternativa não muda a seleção principal.
    """)
    code("""
    resumo_oms = classificados["dai_categoria_oms"].value_counts().reindex(
        OMS_LABELS + ["dados insuficientes"], fill_value=0).rename_axis("dai_categoria_oms").reset_index(name="municipios")
    display(tabela_br(resumo_oms))
    comparacao_nutricional = nutrition_comparison(classificados)
    display(tabela_br(comparacao_nutricional))
    peso_insuficiente = classificados.loc[classificados["criterio_dpi"].isna(),
        ["codigo_ibge", "municipio", "uf", "avaliados_peso", "dpi_pct", "dpi_status"]]
    display(tabela_br(peso_insuficiente))
    """)
    md("""
    ## 8. Mapas nacionais

    O mapa de **0/1/2/3 dimensões** mostra graus de convergência, não intensidade
    clínica ou ranking. O mapa de **convergência total** destaca somente os
    selecionados; dados insuficientes permanecem distintos dos não selecionados.
    O mapa de **DAI por faixas OMS** descreve os acompanhamentos com denominador
    mínimo. Mantêm-se os mapas numéricos e de disponibilidade úteis da primeira versão.

    Polígonos maiores não representam mais pessoas. Proximidade visual não é
    teste de autocorrelação espacial. Cinza indica ausência ou insuficiência,
    nunca baixo risco. IDHM menor aparece mais vermelho; nos demais mapas
    numéricos, valores maiores aparecem mais vermelhos.
    """)
    code("""
    print("Municípios da análise sem geometria:", int((~controle_geometria["tem_geometria"]).sum()))
    print("Feições sem registro na análise:", len(universo_ibge - set(base["codigo_ibge_6"])))
    figuras_mapas = []
    if GERAR_MAPAS:
        mapa = classificados.copy()
        mapa["dimensoes_mapa"] = mapa["n_dimensoes_desfavoraveis"].astype("string").fillna("dados insuficientes")
        mapa["convergencia_mapa"] = mapa["convergencia_total"].map(
            {True: "Convergência total", False: "Sem convergência total"}).fillna("dados insuficientes")
        mapa["disponibilidade"] = mapa["elegivel_principal"].map(
            {True: "Elegível", False: "dados insuficientes"})
        mapas_categoricos = [
            ("dimensoes_mapa", "Número de dimensões desfavoráveis", "09_dimensoes", DIMENSION_COLORS),
            ("convergencia_mapa", "Convergência social, alimentar e nutricional", "11_convergencia_total",
                {"Convergência total": "#9e1b32", "Sem convergência total": "#edf2ef", "dados insuficientes": "#b9b9b9"}),
            ("dai_categoria_oms", "DAI — categorias de prevalência OMS", "12_dai_oms", OMS_COLORS),
            ("disponibilidade", "Disponibilidade para a classificação principal", "05_disponibilidade",
                {"Elegível": "#327c81", "dados insuficientes": "#b9b9b9"})]
        for coluna, titulo, nome, cores in mapas_categoricos:
            display(map_figure(geometria, mapa, coluna, titulo, PASTA_FIGURAS, nome, cores))
            figuras_mapas.append(nome)
            plt.close("all")
        for coluna, titulo, nome in [("ivs", "IVS — vulnerabilidade estrutural de 2010", "06_ivs"),
            ("idhm", "IDHM — 2010; menor é mais desfavorável", "10_idhm"),
            ("cadinsan_pct", f"CadInsan (%) — {CENARIO_CADINSAN}", "07_cadinsan"),
            ("dai_pct", f"DAI (%) — altura com n ≥ {MINIMO_AVALIADOS}", "08_dai")]:
            if coluna == "dai_pct":
                mapa[coluna] = mapa[coluna].where(mapa["avaliados_altura"].ge(MINIMO_AVALIADOS))
            display(map_figure(geometria, mapa, coluna, titulo, PASTA_FIGURAS, nome))
            figuras_mapas.append(nome)
            plt.close("all")
    """)
    md("""
    ## 9. Distribuições, associações e correlações

    Os histogramas mostram as distribuições, inclusive DAI/DPI em todos os
    municípios com avaliações. Os diagramas relacionam os indicadores com DAI;
    as linhas mostram cortes e o vermelho, convergência das três dimensões.

    Spearman descreve associação monotônica, sem exigir distribuição normal.
    Utilizam-se pares disponíveis e, para cada indicador nutricional, seu próprio
    denominador mínimo. A matriz informa o número de municípios de cada par.
    A relação inversa IVS–IDHM, se forte, reforça a decisão de agrupá-los na dimensão
    social. Correlação ajuda a identificar redundância e associações, mas não
    demonstra causalidade, relação individual nem independência das fontes.
    """)
    code("""
    display(distribution_figure(classificados, PASTA_FIGURAS))
    plt.close("all")
    display(association_figure(classificados, cortes, PASTA_FIGURAS))
    plt.close("all")
    figura_correlacao, correlacoes, n_pares = correlation_figure(classificados, PASTA_FIGURAS, MINIMO_AVALIADOS)
    display(figura_correlacao)
    plt.close("all")
    rho_social = correlacoes.loc["ivs", "idhm"]
    relacao_social = "forte e inversa" if rho_social <= -0.7 else "inversa" if rho_social < 0 else "não inversa"
    display(Markdown(f"**IVS–IDHM:** Spearman = {numero_br(rho_social)}, "
        f"n = {contagem_br(n_pares.loc['ivs', 'idhm'])}; relação {relacao_social}. "
        "O agrupamento também tem justificativa conceitual; não depende apenas de um coeficiente."))
    """)
    md("""
    ## 10. Sensibilidade e estabilidade

    Comparam-se **CadInsan P70/P75/P80/P90**, mínimos SISVAN **20/50/100** e
    DAI **6,7% / 10% / P75**, nos cenários com/sem efeito do PBF.
    **6,7%** é a referência do Mapa InSAN; **10%** inicia a categoria OMS média;
    **P75** é uma comparação exploratória da distribuição municipal do DAI.
    Somente o cenário P75 de DAI recalcula seu corte entre municípios acima
    do mínimo de altura; os cortes fixos não variam com a distribuição.
    O P75 alimentar usa todos os municípios com CadInsan válido, antes dos filtros.

    As tabelas de uma mudança por vez mostram quem **entra/sai em relação ao
    cenário principal**, não transições sucessivas entre linhas. O painel mostra
    combinações no cenário CadInsan principal; a exportação contém todos os cenários.
    IVS/IDHM permanecem fixos. Nenhuma alternativa substitui automaticamente
    o resultado principal.

    Jaccard compara as listas (interseção / união; 1 indica igualdade). Frequência
    de seleção é fração das especificações testadas, não probabilidade de risco
    nem intervalo de confiança. Os cenários têm sentidos diferentes e são identificados.
    """)
    code("""
    tabela_sensibilidade, estabilidade = sensitivity(
        base, classificados, sorted(set(QUANTIS_SENSIBILIDADE + [QUANTIL_CADINSAN])),
        sorted(set(MINIMOS_SENSIBILIDADE + [MINIMO_AVALIADOS])),
        sorted(set(CENARIOS_SENSIBILIDADE + [CENARIO_CADINSAN])),
        list(dict.fromkeys(CORTES_DAI_SENSIBILIDADE + [CORTE_DAI])))
    principal_sens = tabela_sensibilidade["cenario"].eq(CENARIO_CADINSAN)
    sensibilidade_cadinsan = tabela_sensibilidade.loc[principal_sens &
        tabela_sensibilidade["minimo_avaliados"].eq(MINIMO_AVALIADOS) &
        tabela_sensibilidade["referencia_dai"].eq(str(CORTE_DAI))]
    sensibilidade_minimos = tabela_sensibilidade.loc[principal_sens &
        tabela_sensibilidade["quantil"].eq(QUANTIL_CADINSAN) &
        tabela_sensibilidade["referencia_dai"].eq(str(CORTE_DAI))]
    sensibilidade_dai = tabela_sensibilidade.loc[principal_sens &
        tabela_sensibilidade["quantil"].eq(QUANTIL_CADINSAN) &
        tabela_sensibilidade["minimo_avaliados"].eq(MINIMO_AVALIADOS)]
    for titulo, tabela in [("CadInsan — uma mudança por vez", sensibilidade_cadinsan),
                           ("Mínimo de avaliações — uma mudança por vez", sensibilidade_minimos),
                           ("DAI — uma mudança por vez", sensibilidade_dai)]:
        display(Markdown("### " + titulo))
        display(tabela_br(tabela))
    display(sensitivity_figure(tabela_sensibilidade, PASTA_FIGURAS, CENARIO_CADINSAN))
    plt.close("all")
    classificados = classificados.merge(estabilidade, on="codigo_ibge_6", validate="one_to_one")
    convergentes = classificados.loc[classificados["convergencia_total"].fillna(False)].sort_values(["uf", "municipio"])
    display(tabela_br(convergentes[["municipio", "uf", "cenarios_elegiveis", "cenarios_selecionado",
        "cenarios_testados", "fracao_cenarios_selecionado"]].head(30)))
    """)
    md("""
    ## 11. Limitações metodológicas

    - **Temporalidade:** IVS/IDHM de 2010 descrevem vulnerabilidade estrutural
      histórica; não são uma fotografia contemporânea. CadInsan é de janeiro/2025
      e SISVAN, de 2025. As fontes não medem a mesma população no mesmo instante.
    - **SISVAN:** os acompanhados pelos serviços de saúde não constituem
      necessariamente amostra probabilística de todos os residentes. DAI/DPI
      descrevem esse público, não estimativas municipais representativas garantidas.
    - **Denominadores:** ≥20 é precedente operacional, não garantia de estabilidade.
      Os mínimos são separados em altura/peso; não há ligação individual entre eles.
    - **CadInsan:** risco estimado no universo familiar analisado; P75 é exploratório,
      não ponto de corte oficial. Percentis municipais não têm ponderação populacional.
    - **Referências nutricionais:** limiares do Mapa InSAN são adaptados a outro
      público SISVAN. Categorias OMS auxiliam interpretação, sem corrigir viés de cobertura.
    - **Território e associação:** verificar códigos não harmoniza limites históricos.
      A malha é ilustrativa. Sobreposição e correlação não demonstram causalidade
      nem permitem inferir situações individuais.
    - **Classificação:** dados insuficientes não significam baixo risco, e zero
      dimensões não demonstra ausência de insegurança alimentar. As classes não
      substituem diagnóstico local, escuta comunitária ou levantamentos representativos.
    """)
    md("""
    ## 12. Conclusões descritivas

    A síntese abaixo é produzida a partir dos resultados desta execução.
    A convergência pode orientar investigação territorial e discussão de políticas,
    sem estabelecer ranking nacional, escore ponderado ou classificação oficial.
    """)
    code('''
    selecionados = len(convergentes)
    regiao_maior_numero = resumo_regional.sort_values("convergencia_total", ascending=False).iloc[0]
    resumo_execucao = f"""# Síntese da análise municipal — v2

    Na união das fontes há **{contagem_br(len(base))} municípios**;
    **{contagem_br(elegiveis)}** têm informação suficiente nas três dimensões e
    **{contagem_br(selecionados)}** apresentam convergência total.
    Os selecionados presentes na malha representam
    **{percentual_br(selecionados_na_malha / len(universo_ibge) * 100)}** de seus
    {contagem_br(len(universo_ibge))} municípios de referência, e a seleção corresponde a
    **{percentual_br(selecionados / elegiveis * 100 if elegiveis else np.nan)}** dos elegíveis.

    A maior quantidade selecionada está em **{regiao_maior_numero['regiao']}**
    ({contagem_br(regiao_maior_numero['convergencia_total'])} municípios);
    quantidade não equivale à maior proporção nem ao maior risco individual.

    Regra principal: social (IVS ≥0,401 E IDHM <0,600), alimentar
    (CadInsan ≥P{QUANTIL_CADINSAN * 100:.0f}, cenário {CENARIO_CADINSAN}) e nutricional
    (DAI ≥{numero_br(CORTE_DAI, 1)}%, altura com n ≥{MINIMO_AVALIADOS}).
    DPI é complementar. A alternativa social+alimentar+DAI+DPI seleciona
    {contagem_br(int(classificados['convergencia_total_dai_dpi'].sum()))} municípios.

    A sensibilidade completa variou de
    {contagem_br(tabela_sensibilidade['convergencia_total'].min())} a
    {contagem_br(tabela_sensibilidade['convergencia_total'].max())} municípios em
    {len(tabela_sensibilidade)} especificações. Essa variação não é intervalo de confiança;
    consultar as mudanças de uma escolha por vez antes de avaliar estabilidade.

    IVS–IDHM: Spearman {numero_br(rho_social)}, associação {relacao_social},
    coerente com seu tratamento conjunto na dimensão social quando inversa.
    IVS/IDHM são históricos (2010); CadInsan e SISVAN, de 2025.
    Os resultados descrevem convergência nos universos analisados, não a
    prevalência de fome em toda a população e não permitem inferir causalidade.
    """
    display(Markdown(resumo_execucao))
    ''')
    md("""
    ## 13. Exportação e reprodução

    Exporta-se a base municipal completa (incluindo dados insuficientes), a lista
    de convergência, flags anuláveis, tabelas de cobertura/qualidade, categorias OMS,
    correlações com tamanhos dos pares, sensibilidade, auditorias e figuras PNG/SVG.
    O CSV final inclui códigos, território, indicadores, denominadores, três dimensões
    e suas classes. A auditoria de arredondamento refere-se apenas ao CadInsan.

    O ZIP contém dicionário, síntese e manifesto com parâmetros, fórmulas, hashes
    das entradas e do código, procedência e versões do ambiente. Não contém a
    base adicional de pessoas cadastradas nem colunas derivadas dela.
    Pode ser baixado pela aba de arquivos do Colab ou pela opção nos parâmetros.
    """)
    code(r"""
    identificador = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    destino = PASTA_SAIDA / f"execucao_{identificador}"
    destino.mkdir()
    tabelas = {"base_municipal_final": classificados, "municipios_convergencia_total": convergentes,
        "cortes": cortes, "controle_integracao": controle_integracao, "municipios_sem_correspondencia": ausencias,
        "sem_classificacao": sem_classificacao, "qualidade_sisvan": qualidade_sisvan,
        "interpretacao_sisvan": interpretacao_sisvan, "controle_geometria": controle_geometria,
        "descritivas": descritivas.rename_axis("indicador").reset_index(), "totais_nutricionais": totais_nutricionais,
        "resumo_nacional": resumo_nacional, "resumo_uf": resumo_uf, "resumo_regional": resumo_regional,
        "resumo_classes": resumo_classes, "resumo_social": resumo_social, "resumo_oms": resumo_oms,
        "comparacao_nutricional": comparacao_nutricional, "peso_insuficiente": peso_insuficiente,
        "sensibilidade": tabela_sensibilidade, "sensibilidade_cadinsan": sensibilidade_cadinsan,
        "sensibilidade_minimos": sensibilidade_minimos, "sensibilidade_dai": sensibilidade_dai,
        "estabilidade": estabilidade, "dicionario_variaveis": dictionary(), "validacao_catalogo": validacao_catalogo,
        "comparacao_arredondamento": comparacao_arredondamento, "cortes_percentuais_csv": cortes_percentuais_csv,
        "correlacoes_spearman": correlacoes.rename_axis("indicador").reset_index(),
        "n_pares_correlacao": n_pares.rename_axis("indicador").reset_index()}
    for nome, tabela in tabelas.items():
        tabela.to_csv(destino / f"{nome}.csv", index=False, encoding="utf-8-sig")
    (destino / "figuras").mkdir()
    for nome in ["01_distribuicoes", "02_associacoes", "03_correlacoes", "04_sensibilidade"] + figuras_mapas:
        for extensao in ["png", "svg"]:
            shutil.copy2(PASTA_FIGURAS / f"{nome}.{extensao}", destino / "figuras")
    manifesto = {
        "versao": 2, "executado_em": datetime.now(timezone.utc).isoformat(),
        "quantil_cadinsan": QUANTIL_CADINSAN, "corte_dai_pct": CORTE_DAI,
        "corte_dpi_pct_complementar": CORTE_DPI, "minimo_avaliados": MINIMO_AVALIADOS,
        "cenario_cadinsan": CENARIO_CADINSAN,
        "formula_cadinsan_pct": "100 * familias_risco_cenario / familias_cadinsan",
        "formula_dai_pct": "100 * (altura_muito_baixa_n + altura_baixa_n) / avaliados_altura",
        "formula_dpi_pct": "100 * (peso_muito_baixo_n + peso_baixo_n) / avaliados_peso",
        "dimensoes": {"social": "IVS >=0.401 E IDHM <0.600", "alimentar": "CadInsan >= quantil nacional",
                      "nutricional": "DAI >= corte principal E altura com denominador mínimo"},
        "regra": "Convergência das três dimensões; DPI não integra seleção principal",
        "indicadores_com_quantil_principal": ["cadinsan"], "cortes": cortes.to_dict("records"),
        "hashes_entrada": hashes_entrada.to_dict("records"), "codigo_analise_sha256": CODIGO_ANALISE_SHA256,
        "proveniencia_catalogo": proveniencia_catalogo,
        "proveniencia_sisvan": {s: sisvan_metadata(PASTA_DADOS, s) for s in ["sisvan_altura", "sisvan_peso"]},
        "malha": metadados_malha, "universo_nacional": resumo_nacional.to_dict("records"),
        "ambiente": {"python": platform.python_version(), "pandas": pd.__version__, "numpy": np.__version__,
                     "matplotlib": matplotlib.__version__, "scipy": scipy.__version__},
        "sensibilidade": tabela_sensibilidade.to_dict("records"),
        "limites": ["Temporalidade 2010/2025", "Público SISVAN não necessariamente representativo",
                    "Adaptação das referências nutricionais; não reprodução do Mapa InSAN",
                    "Corte CadInsan exploratório", "Sem cobertura populacional ou inferência causal"]}
    (destino / "manifesto_execucao.json").write_text(json.dumps(manifesto, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (destino / "resumo.md").write_text(resumo_execucao, encoding="utf-8")
    shutil.copytree(PASTA_DADOS / "documentacao", destino / "documentacao_entradas")
    shutil.copy2(PASTA_DADOS / "README.md", destino / "documentacao_entradas/README_SELECAO.md")
    shutil.copy2(PASTA_DADOS / "SHA256SUMS", destino / "documentacao_entradas")
    arquivo_zip = shutil.make_archive(str(destino), "zip", root_dir=destino)
    print("ZIP pronto:", arquivo_zip)
    if BAIXAR_RESULTADOS_NO_COLAB:
        try:
            from google.colab import files
        except ImportError:
            print("Fora do Colab: utilizar o ZIP no caminho informado.")
        else:
            files.download(arquivo_zip)
    """)
    md("""
    ## Referências metodológicas

    - Ipea (2015). [Atlas da Vulnerabilidade Social nos Municípios Brasileiros](https://repositorio.ipea.gov.br/bitstream/11058/4381/1/Atlas_da_vulnerabilidade_social_nos_municipios_brasileiros.pdf), conceito, subíndices e faixas de IVS.
    - PNUD, Ipea e FJP. [Atlas do Desenvolvimento Humano no Brasil](https://www.undp.org/pt/brazil/desenvolvimento-humano/atlas-do-desenvolvimento-humano-no-brasil); [faixas de IDHM, anexo estatístico](https://www.undp.org/sites/g/files/zskgke326/files/2024-05/anexo_estatistico_pnud_21maio24_isbn_web2.pdf).
    - MDS. [CadInsan 2025](https://www.gov.br/mds/pt-br/Sisan/vigilancia-do-sisan/CADINSAN2025.pdf), metodologia e universo (p. 7), cenários (p. 16–19) e tabela municipal (a partir de p. 22).
    - Ministério da Saúde. [SISVAN](https://www.gov.br/saude/pt-br/composicao/saps/vigilancia-alimentar-e-nutricional/sisvan) e [relatórios públicos](https://sisaps.saude.gov.br/sisvan/relatoriopublico/).
    - MDS. [Mapa InSAN 2017–2022](https://www.gov.br/mds/pt-br/Sisan/monitoramento-da-san/MapaInSAN_20172022.pdf), seção de mapeamento/tabela 2: ≥20 acompanhamentos, DAI ≥6,7%, DPI ≥1,8%. Esses valores foram confirmados no texto oficial indexado; o acesso direto ao PDF apresentou restrição durante a revisão.
    - Ministério da Saúde (2009). [PNDS 2006 — Dimensões do Processo Reprodutivo e da Saúde da Criança](https://bvsms.saude.gov.br/bvs/publicacoes/pnds_crianca_mulher.pdf), p. 217, referência citada pelo Mapa InSAN.
    - OMS. [NLiS — Malnutrition in children](https://www.who.int/data/nutrition/nlis/info/malnutrition-in-children), tabela de prevalências de stunting; de Onis et al. (2018), DOI [10.1017/S1368980018002434](https://doi.org/10.1017/S1368980018002434).
    - [Cozinhas Solidárias](https://github.com/TriangulosTecnologia/cozsolidarias): procedência dos dois CSVs sociais utilizados; catálogo correspondente, com verificação de hashes.
    - IBGE. [API de malhas simplificadas v4](https://servicodados.ibge.gov.br/api/docs/malhas?versao=4).
    """)
    notebook.cells = cells
    nbformat.validate(notebook)
    for i, cell in enumerate(cells):
        if cell.cell_type == "code":
            compile(cell.source, f"<notebook-v2-celula-{i}>", "exec")
    nbformat.write(notebook, NOTEBOOK)
    if hashlib.sha256(ORIGINAL.read_bytes()).hexdigest() != original_hash:
        raise RuntimeError("A primeira versão foi alterada")
    return NOTEBOOK


if __name__ == "__main__":
    print(build())
