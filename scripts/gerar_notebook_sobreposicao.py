"""Gera notebook autocontido com bases e código; opcionalmente coleta malha IBGE."""

from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import textwrap
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import nbformat

ROOT = Path(__file__).resolve().parents[1]
SUPPORT = ROOT / "dados/apoio/ibge"
NOTEBOOK = ROOT / "notebooks/01_sobreposicao_criterios.ipynb"
MESH_URL = "https://servicodados.ibge.gov.br/api/v4/malhas/paises/BR"


def fetch_mesh():
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=Retry(
        total=3, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"], respect_retry_after_header=True)))
    response = session.get(MESH_URL, params={"formato": "application/vnd.geo+json",
                                           "qualidade": "minima", "intrarregiao": "municipio"},
                           timeout=(15, 90))
    response.raise_for_status()
    geometry = response.json()
    if geometry.get("type") != "FeatureCollection" or not geometry.get("features"):
        raise ValueError("Resposta do IBGE não contém geometria municipal.")
    codes = [str(f["properties"]["codarea"]) for f in geometry["features"]]
    if len(codes) != len(set(codes)) or not all(len(c) == 7 and c.isdigit() for c in codes):
        raise ValueError("Códigos da malha inválidos ou duplicados.")
    SUPPORT.mkdir(parents=True, exist_ok=True)
    (SUPPORT / "malha_municipal_simplificada.geojson").write_bytes(response.content)
    metadata = {
        "fonte": "IBGE, API de malhas simplificadas v4", "url": response.url,
        "obtido_em": datetime.now(timezone.utc).isoformat(),
        "sha256": hashlib.sha256(response.content).hexdigest(),
        "feicoes": len(codes), "ano_malha": None,
        "nota": "API v4 não expõe parâmetro de período. Não afirmar que esta é a malha de 2025. "
                "A correspondência dos códigos é auditada; isso não valida a equivalência histórica dos limites.",
        "documentacao": "https://servicodados.ibge.gov.br/api/docs/malhas?versao=4",
    }
    (SUPPORT / "malha_municipal_simplificada.metadados.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def payload():
    stream = io.BytesIO()
    root = ROOT / "dados/pesquisa"
    files = {str(p.relative_to(root)): p for p in root.rglob("*") if p.is_file()}
    files["documentacao/fonte_dados.json"] = ROOT / "fonte_dados.json"
    files["documentacao/dataset_catalogue.json"] = ROOT / "dataset_catalogue.json"
    files["documentacao/README_SISVAN.md"] = root / "sisvan/README.md"
    files["documentacao/SISVAN.metadados.json"] = root / "sisvan/sisvan_municipios_altura_por_idade_0_a_menor_5_anos_2025.metadados.json"
    for path in SUPPORT.glob("*"):
        if path.is_file():
            files[f"apoio/ibge/{path.name}"] = path
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for relative, path in sorted(files.items()):
            info = zipfile.ZipInfo(relative, date_time=(2026, 10, 4, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())
    return base64.b64encode(stream.getvalue()).decode("ascii")


def build():
    if not (SUPPORT / "malha_municipal_simplificada.geojson").exists():
        raise FileNotFoundError("Gerar primeiro com --coletar-malha para incorporar os mapas.")
    nb = nbformat.v4.new_notebook()
    nb.metadata.update({
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python"},
        "colab": {"name": NOTEBOOK.name, "toc_visible": True},
    })
    cells = []

    def md(source):
        cells.append(nbformat.v4.new_markdown_cell(textwrap.dedent(source).strip()))

    def code(source, hidden=False):
        cell = nbformat.v4.new_code_cell(textwrap.dedent(source).strip())
        if hidden:
            cell.metadata.update({"cellView": "form", "jupyter": {"source_hidden": True}})
        cells.append(cell)
        return cell

    sources = json.loads((ROOT / "fonte_dados.json").read_text(encoding="utf-8"))
    sisvan_meta = json.loads((ROOT / "dados/pesquisa/sisvan/sisvan_municipios_altura_por_idade_0_a_menor_5_anos_2025.metadados.json").read_text())

    md("""
    # Áreas de risco alimentar e vulnerabilidade social no Brasil

    **Estudo ecológico municipal — sobreposição de critérios.**

    **Pergunta da pesquisa:** identificar áreas do Brasil de maior risco alimentar
    e vulnerabilidade social a partir de IVS, IDHM, CadÚnico, CadInsan e SISVAN.

    **Objetivo da análise:** identificar municípios onde coincidem IVS elevado,
    IDHM baixo, risco alimentar estimado elevado no CadInsan e déficit de
    altura para idade elevado nas crianças acompanhadas pelo SISVAN.
    CadÚnico ajuda a caracterizar esses territórios.

    A unidade de análise é o **município**, não a pessoa ou a família. A
    sobreposição identifica convergência de indicadores, sem ranking composto,
    inferência causal ou estimativa de fome em toda a população municipal.
    """)
    md(f"""
    ## 1. Bases de dados e procedência

    A análise reúne **quatro arquivos municipais**, que contêm os cinco
    indicadores da pesquisa. IVS e IDHM estão no mesmo arquivo.
    IVS significa **Índice de Vulnerabilidade Social**; IDHM, **Índice de
    Desenvolvimento Humano Municipal**; CadÚnico, **Cadastro Único para
    Programas Sociais**. CadInsan é o indicador municipalizado de risco de
    insegurança alimentar grave a partir do CadÚnico.

    | Base | Fonte original / instituição responsável | De onde o arquivo foi obtido | Referência e unidade | Registros municipais |
    |---|---|---|---|---:|
    | IVS e IDHM | [Atlas IVS / Ipea](http://ivs.ipea.gov.br/index.php/pt/planilha); IDHM do Atlas do Desenvolvimento Humano (PNUD, Ipea e FJP) | [CSV publicado por Cozinhas Solidárias]({sources['atlasivs_municipios_2010.csv']}) | 2010; índices municipais | 5.565 |
    | CadÚnico | [MDS / SAGI](https://aplicacoes.mds.gov.br/sagi/servicos/misocial) | [JSON publicado por Cozinhas Solidárias]({sources['municipios-cadunico.json']}) | Junho/2026; pessoas cadastradas | 5.564 |
    | CadInsan | [MDS — relatório CadInsan 2025](https://www.gov.br/mds/pt-br/Sisan/vigilancia-do-sisan/CADINSAN2025.pdf) | [CSV publicado por Cozinhas Solidárias]({sources['CADINSAN_2025_dados_municipais.csv']}) | Janeiro/2025; famílias do universo analisado | 5.570 |
    | SISVAN | Ministério da Saúde — Sistema de Vigilância Alimentar e Nutricional | Coleta direta dos [relatórios públicos]({sources['sisvan_relatorios']}) de Altura X Idade | 2025; crianças de 0 a menos de 5 anos acompanhadas pelo sistema | {sisvan_meta['linhas']:,} |

    **Procedência:** as três bases sociais foram obtidas do
    [repositório de Cozinhas Solidárias](https://github.com/TriangulosTecnologia/cozsolidarias),
    não extraídas diretamente dos portais oficiais nesta pesquisa. Seus períodos
    e unidades foram conferidos no catálogo que acompanha os arquivos. O
    relatório oficial do MDS complementa a referência mensal do CadInsan.
    SISVAN foi baixado novamente em **{sisvan_meta['gerado_em'][:10]}**, nas 27 UFs,
    usando o coletor atualizado. Os XLSX oficiais são preservados sem alteração.
    O CSV consolida as linhas municipais e achata cabeçalhos multinível; mantém
    os valores de contagem e os percentuais das células, sem DAI pré-calculado.
    **DAI é calculado nesta análise**, não na base de entrada.

    **Apoio cartográfico:** malha municipal simplificada obtida diretamente da
    [API v4 do IBGE](https://servicodados.ibge.gov.br/api/docs/malhas?versao=4).
    A API utilizada não informa o ano da malha; ela é apoio ilustrativo, não uma
    harmonização dos limites municipais entre os diferentes períodos.

    Os arquivos estão incorporados ao notebook. Para reproduzir no Colab,
    revisar os parâmetros e selecionar **Ambiente de execução → Executar tudo**.
    A preparação do ambiente pode exigir internet; a análise não faz nova coleta.
    """)
    md("""
    ## 2. Estratégia e parâmetros da análise

    A regra principal exige **os quatro critérios simultaneamente**: IVS,
    CadInsan e DAI elevados, e IDHM baixo. CadÚnico contextualiza os
    resultados, sem participar da seleção principal.

    IVS ≥ **0,401** e IDHM < **0,600** são cortes fixos, correspondentes a
    vulnerabilidade alta/muito alta e desenvolvimento baixo/muito baixo.
    Não mudam com `QUANTIL` nem na análise de sensibilidade. Os valores originais
    são preservados. IDHM igual a 0,600 não satisfaz o critério.

    P75 para CadInsan/DAI e mínimo de 100 avaliações são pontos de partida
    exploratórios, editáveis e sem caráter oficial. O corte do DAI é calculado
    sobre municípios com o denominador mínimo; CadInsan usa seu universo válido.
    Esses quantis são nacionais, não calculados apenas sobre municípios que
    atendem aos cortes sociais.
    O percentil 75 delimita aproximadamente os 25% maiores valores municipais,
    não 75% da população. Cada município tem o mesmo peso; empates são incluídos.
    O mínimo de 100 avaliações é uma precaução operacional, não uma exigência
    oficial nem garantia de representatividade; será examinado na sensibilidade.

    `com_PBF` é o cenário inicial, considerando o efeito do benefício na renda.
    `sem_PBF` é o cenário contrafactual que desconsidera esse efeito e entra na
    sensibilidade. Não são dois grupos de beneficiários e não beneficiários.
    CadInsan considera famílias com cadastro atualizado nos últimos 12 meses,
    com referência janeiro/2025. As pessoas cadastradas no JSON de junho/2026
    não substituem esse denominador de famílias.
    """)
    code("""
    QUANTIL = 0.75  # CadInsan e DAI
    MINIMO_AVALIADOS = 100
    CENARIO_CADINSAN = "com_PBF"  # opções: "com_PBF", "sem_PBF"
    QUANTIS_SENSIBILIDADE = [0.75, 0.80]
    MINIMOS_SENSIBILIDADE = [30, 50, 100]
    CENARIOS_SENSIBILIDADE = ["com_PBF", "sem_PBF"]
    GERAR_MAPAS = True
    BAIXAR_RESULTADOS_NO_COLAB = False  # True solicita download do ZIP no final

    """)
    md("""
    ### Preparação da execução

    As células técnicas recolhidas preparam o ambiente e recuperam os arquivos.
    A integridade das entradas é verificada antes da análise; os arquivos
    originais permanecem separados dos resultados derivados.
    As tabelas exibem contagens inteiras, índices com três casas decimais e
    percentuais com duas casas e `%`, no padrão brasileiro. `—` indica ausência.
    Essa formatação não modifica os valores dos cálculos nem os CSVs exportados.
    """)
    setup_cell = code("""
    import importlib.util
    import subprocess
    import sys
    from pathlib import Path

    packages = {"pandas": "pandas>=2.2,<4", "numpy": "numpy>=1.26,<3",
                "matplotlib": "matplotlib>=3.8,<4", "scipy": "scipy>=1.11,<2",
                "jinja2": "jinja2>=3.1,<4"}
    missing = [requirement for module, requirement in packages.items()
               if importlib.util.find_spec(module) is None]
    if missing:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", *missing])

    import hashlib
    import io
    import json
    import zipfile
    import base64
    import platform
    import shutil
    from datetime import datetime, timezone
    import pandas as pd
    import numpy as np
    import matplotlib
    import matplotlib.pyplot as plt
    import scipy
    from IPython.display import display, Markdown

    PASTA_EXECUCAO = Path.cwd() / "resultados_sobreposicao"
    PASTA_DADOS = PASTA_EXECUCAO / "entradas"
    PASTA_SAIDA = PASTA_EXECUCAO / "resultados"
    PASTA_FIGURAS = PASTA_SAIDA / "figuras"
    PASTA_SAIDA.mkdir(parents=True, exist_ok=True)
    PASTA_FIGURAS.mkdir(parents=True, exist_ok=True)
    pd.set_option("display.max_columns", 30)
    """, hidden=True)
    setup_cell.source += "\n\n" + (ROOT / "scripts/formatacao_tabelas.py").read_text(encoding="utf-8")
    encoded = payload()
    code('# @title Bases e malha incorporadas — executar sem editar\n'
         f'PACOTE_BASE64 = "{encoded}"\n'
         'with zipfile.ZipFile(io.BytesIO(base64.b64decode(PACOTE_BASE64))) as pacote:\n'
         '    for membro in pacote.infolist():\n'
         '        destino = (PASTA_DADOS / membro.filename).resolve()\n'
         '        if not destino.is_relative_to(PASTA_DADOS.resolve()):\n'
         '            raise ValueError("Caminho inválido no pacote de dados")\n'
         '    pacote.extractall(PASTA_DADOS)\n'
         'print("Bases recuperadas para análise.")', hidden=True)
    md("""
    ## 3. Integração e disponibilidade dos dados

    A união das bases preserva todos os municípios disponíveis. A integração
    verifica a unicidade dos códigos, categorias e denominadores. Ausência de
    informação é mantida como ausência, não substituída por zero.
    """)
    code('# @title Funções de análise — executar sem editar\n' +
         (ROOT / "scripts/analise_sobreposicao.py").read_text(encoding="utf-8"), hidden=True)
    code("""
    validacao_catalogo, proveniencia_catalogo = validate_catalogue(
        PASTA_DADOS / "documentacao/dataset_catalogue.json", PASTA_DADOS)
    base, controle_integracao, hashes_entrada = prepare_base(PASTA_DADOS)
    figure_style()
    print("Municípios na união:", len(base))
    print("Integridade das bases e correspondência com o catálogo verificadas.")
    display(tabela_br(controle_integracao))
    ausencias = base.loc[~base[["tem_ivs_idhm", "tem_cadunico", "tem_cadinsan", "tem_sisvan"]].all(axis=1),
                         ["codigo_ibge_6", "codigo_ibge_7", "municipio", "uf",
                          "tem_ivs_idhm", "tem_cadunico", "tem_cadinsan", "tem_sisvan"]]
    display(tabela_br(ausencias))
    """)
    md("""
    **Interpretação:** a união preserva municípios sem informações sociais.
    O código SISVAN tem seis dígitos; as fontes sociais têm sete. A ligação usa
    o prefixo único de seis dígitos, com verificação de conflitos. Isso não
    demonstra que limites territoriais de 2010 e 2025 sejam
    idênticos. CadÚnico JSON (pessoas, junho/2026) e `Cadastros_Cadunico`
    (famílias, janeiro/2025) ficam separados. Sem denominador populacional
    compatível, a contagem de pessoas não se transforma em proporção de cobertura.
    """)
    md(r"""
    ## 4. Indicadores recalculados e qualidade

    $$DAI(\%)=100\times\frac{N(\text{altura muito baixa})+N(\text{altura baixa})}
    {N(\text{avaliados em altura por idade})}$$

    $$CadInsan_{cenario}(\%)=100\times
    \frac{Cadinsan\_absoluto\_{cenario}}{Cadastros\_Cadunico}$$

    **DAI** é o percentual de déficit de altura para idade.
    CadInsan usa famílias em risco estimado no
    numerador e famílias do universo analisado no denominador.

    Os percentuais são recalculados **sem arredondamento** para evitar empates
    artificiais nos cortes; os valores de origem permanecem preservados.
    Denominador zero gera percentual indefinido, não ausência de déficit.

    As contagens são conferidas pela soma das categorias e pelos percentuais
    oficiais antes do cálculo do DAI. Essa verificação não reescreve a entrada.
    """)
    code("""
    qualidade_sisvan = pd.DataFrame({
        "controle": ["Sem avaliações de altura", "Altura abaixo do mínimo principal",
                     "Contagens com escala interpretada", "Mais de uma escala compatível"],
        "municipios": [int(base["avaliados_altura"].eq(0).sum()),
                       int(base["avaliados_altura"].between(1, MINIMO_AVALIADOS - 1).sum()),
                       int(base["sisvan_escala_alterada"].fillna(False).sum()),
                       int(base["sisvan_escalas_compativeis"].gt(1).sum())]})
    display(tabela_br(qualidade_sisvan.iloc[:2]))
    colunas_auditoria = ["codigo_ibge_6", "municipio", "uf", "avaliados_altura",
                        "altura_muito_baixa_n", "altura_baixa_n", "altura_adequada_n",
                        "sisvan_escala_alterada", "sisvan_escalas_compativeis"]
    colunas_auditoria += [c for c in base if c.endswith(("_valor_fonte", "_percentual_fonte"))]
    interpretacao_sisvan = base.loc[base["tem_sisvan"], colunas_auditoria].copy()
    display(tabela_br(base.loc[base["avaliados_altura"].eq(0),
                     ["municipio", "uf", "dai_pct", "avaliados_altura"]]))
    totais = []
    for indicador, denominador in [("dai", "avaliados_altura")]:
        n = base[f"{indicador}_n"].sum()
        d = base[denominador].sum()
        totais.append({"indicador": indicador.upper(), "numerador": n,
                       "denominador": d, "percentual_agregado": n / d * 100})
    display(tabela_br(pd.DataFrame(totais)))
    """)
    md("""
    **Interpretação:** esses totais descrevem os registros dos relatórios
    consultados. Os percentuais agregados são razões entre somas, não
    médias dos percentuais municipais. Muitos registros não garantem
    representatividade. A população municipal de menores de cinco anos não está
    disponível nesta análise; portanto não calculamos cobertura populacional.
    """)
    md("""
    ## 5. Classificação exploratória

    Ser prioritário exige IVS ≥ 0,401, IDHM < 0,600, CadInsan ≥ corte e DAI ≥ corte,
    além de dados válidos para os quatro critérios e do mínimo de avaliações de
    altura. IDHM ausente impede a classificação principal.
    Informação insuficiente é diferente de ausência de risco.
    """)
    code("""
    classificados, cortes = classify(base, QUANTIL, MINIMO_AVALIADOS, CENARIO_CADINSAN)
    display(tabela_br(cortes))
    display(tabela_br(classificados["perfil"].value_counts().rename_axis("perfil").reset_index(name="municipios")))
    sem_classificacao = classificados.loc[~classificados["elegivel_principal"],
        ["codigo_ibge_6", "municipio", "uf", "avaliados_altura", "motivo_nao_classificacao"]]
    print("Municípios com informação insuficiente:", len(sem_classificacao))
    comparacao_arredondamento, cortes_percentuais_csv = compare_rounding(
        base, classificados, QUANTIL, MINIMO_AVALIADOS, CENARIO_CADINSAN)
    total_com_csv = int(comparacao_arredondamento["selecionado_percentual_csv"].fillna(False).sum())
    total_recalculado = int(classificados["prioritario"].fillna(False).sum())
    display(Markdown(f"**Efeito do arredondamento:** {total_com_csv} municípios com percentuais do CSV; "
                     f"{total_recalculado} com as razões sem arredondamento usadas na análise."))
    display(tabela_br(comparacao_arredondamento.loc[comparacao_arredondamento["mudou_selecao"]]))
    """)
    md("""
    ## 6. Distribuições, associações e redundância

    As distribuições nutricionais mostram todos os municípios com avaliações.
    Os gráficos de associação usam municípios elegíveis para a regra principal.
    A correlação usa pares disponíveis, com denominadores nutricionais acima do
    mínimo; cada par apresenta seu número de municípios. As linhas tracejadas
    são os cortes adotados (fixos para IVS/IDHM, exploratórios para CadInsan/DAI).
    Vermelho indica convergência dos quatro critérios.
    """)
    code("""
    display(distribution_figure(classificados, PASTA_FIGURAS))
    plt.close("all")
    display(association_figure(classificados, cortes, PASTA_FIGURAS))
    plt.close("all")
    figura_correlacao, correlacoes, n_pares = correlation_figure(classificados, PASTA_FIGURAS, MINIMO_AVALIADOS)
    display(figura_correlacao)
    plt.close("all")
    """)
    md("""
    **Interpretação:** avaliar se valores desfavoráveis coincidem, a dispersão e
    possíveis diferenças regionais. Correlações são descritivas: não demonstram
    causalidade, relações individuais ou validação independente do CadInsan.
    Este depende do CadÚnico; IVS e IDHM também podem conter informação redundante.
    Não somamos os cinco indicadores em um índice.
    """)
    md("""
    ## 7. Mapas nacionais e disponibilidade dos dados

    Os mapas mostram os indicadores e sua coincidência no território municipal.
    A correspondência dos códigos com a malha do IBGE é verificada; municípios
    com informação insuficiente para a sobreposição aparecem em cinza.
    """)
    code("""
    caminho_malha = PASTA_DADOS / "apoio/ibge/malha_municipal_simplificada.geojson"
    metadados_malha = json.loads((PASTA_DADOS / "apoio/ibge/malha_municipal_simplificada.metadados.json").read_text())
    if hashlib.sha256(caminho_malha.read_bytes()).hexdigest() != metadados_malha["sha256"]:
        raise ValueError("Hash da malha diferente do registrado")
    geometria = json.loads(caminho_malha.read_text())
    controle_geometria = geometry_audit(geometria, base)
    print("Municípios da base sem geometria:", int((~controle_geometria["tem_geometria"]).sum()))
    print("Feições da malha sem registro na base:",
          len({str(f["properties"]["codarea"])[:6] for f in geometria["features"]} - set(base["codigo_ibge_6"])))
    if GERAR_MAPAS:
        mapa = classificados.copy()
        mapa["disponibilidade"] = mapa["elegivel_principal"].map({True: "Elegível para regra", False: "Informação insuficiente"})
        display(map_figure(geometria, mapa, "disponibilidade", "Disponibilidade para a regra principal", PASTA_FIGURAS,
                           "05_disponibilidade", {"Elegível para regra": "#327c81", "Informação insuficiente": "#b9b9b9"}))
        plt.close("all")
        for coluna, titulo, nome in [("ivs", "IVS — contexto de 2010", "06_ivs"),
                                    ("idhm", "IDHM — 2010; menor valor é mais desfavorável", "10_idhm"),
                                    ("cadinsan_pct", f"CadInsan (%) — {CENARIO_CADINSAN}", "07_cadinsan"),
                                    ("dai_pct", f"DAI (%) — altura com n ≥ {MINIMO_AVALIADOS}", "08_dai")]:
            if coluna == "dai_pct":
                mapa[coluna] = mapa[coluna].where(mapa["avaliados_altura"] >= MINIMO_AVALIADOS)
            display(map_figure(geometria, mapa, coluna, titulo, PASTA_FIGURAS, nome))
            plt.close("all")
        display(map_figure(geometria, classificados, "perfil", "Sobreposição de IVS, IDHM, CadInsan e DAI", PASTA_FIGURAS,
                           "09_sobreposicao", GROUP_COLORS))
        plt.close("all")
    """)
    md("""
    **Interpretação:** o mapa final identifica coincidência municipal dos
    critérios. Áreas visualmente próximas não constituem teste de agrupamento
    espacial. A área dos polígonos não representa população ou quantidade de
    famílias. O mapa de disponibilidade não é mapa de cobertura populacional.
    No mapa do IDHM, valores menores recebem as cores mais vermelhas; nos
    mapas de IVS, CadInsan e DAI, são os valores maiores.
    """)
    md("""
    ## 8. Municípios selecionados e comparação regional

    **Indicadores da seleção:** IVS, IDHM, CadInsan e DAI, com os denominadores
    de famílias do CadInsan e avaliações de altura. As flags repetidas são omitidas.

    **Caracterização dos municípios selecionados:** pessoas cadastradas no
    CadÚnico em junho/2026 e famílias em risco estimado no cenário CadInsan
    escolhido, de janeiro/2025. São unidades e períodos distintos, não somáveis.
    As tabelas seguem a mesma ordem por UF e município, **sem ranking composto**.

    **Comparação regional complementar:** DAI pela razão entre somas de
    numeradores e denominadores de altura, usando todos os registros válidos,
    não apenas os municípios selecionados.
    """)
    code("""
    prioritarios = classificados.loc[classificados["prioritario"].fillna(False)].sort_values(["uf", "municipio"])
    colunas_selecao = {
        "municipio": "Município", "uf": "UF", "ivs": "IVS", "idhm": "IDHM",
        "cadinsan_pct": "CadInsan (%)", "dai_pct": "DAI (%)",
        "cadastros_cadunico_cadinsan": "Famílias no universo CadInsan",
        "avaliados_altura": "Avaliações de altura"}
    colunas_caracterizacao = {
        "municipio": "Município", "uf": "UF",
        "cadunico_pessoas_2026_06": "Pessoas no CadÚnico — jun/2026",
        "cadinsan_n": "Famílias em risco estimado — jan/2025"}
    indicadores_selecao = prioritarios[list(colunas_selecao)].rename(columns=colunas_selecao)
    caracterizacao_municipios = prioritarios[list(colunas_caracterizacao)].rename(columns=colunas_caracterizacao)
    print("Municípios com convergência:", len(prioritarios))
    display(Markdown("### Indicadores da seleção"))
    display(tabela_br(indicadores_selecao.head(30)))
    display(Markdown(f"### Caracterização dos municípios selecionados\\n\\nCenário CadInsan: `{CENARIO_CADINSAN}`."))
    display(tabela_br(caracterizacao_municipios.head(30)))
    print("Prévia dos mesmos 30 municípios; a exportação mantém a lista completa e os nomes originais das colunas.")
    resumo_regional = regional_summary(classificados)
    display(Markdown("### Comparação regional — DAI"))
    display(tabela_br(resumo_regional))
    """)
    md("""
    ## 9. Sensibilidade e estabilidade da seleção

    São comparados percentis 75/80, mínimos de 30/50/100 avaliações e cenários
    CadInsan com/sem efeito do Bolsa Família. IVS ≥ 0,401 e IDHM < 0,600 permanecem
    fixos, e os quatro critérios continuam obrigatórios.

    Cada combinação recalcula o corte do DAI entre municípios com o mínimo
    escolhido: mudam tanto a elegibilidade quanto o universo do quantil.
    O índice de **Jaccard** é a quantidade de municípios comuns às duas listas
    dividida pela quantidade presente em pelo menos uma delas; 1 indica listas
    idênticas e 0 indica nenhuma coincidência.

    A frequência de seleção é a fração das especificações testadas, **não uma
    probabilidade de risco ou medida de incerteza amostral**. Os cenários CadInsan
    têm interpretações distintas e são discriminados na tabela.
    """)
    code("""
    quantis_teste = sorted(set(QUANTIS_SENSIBILIDADE + [QUANTIL]))
    minimos_teste = sorted(set(MINIMOS_SENSIBILIDADE + [MINIMO_AVALIADOS]))
    cenarios_teste = sorted(set(CENARIOS_SENSIBILIDADE + [CENARIO_CADINSAN]))
    tabela_sensibilidade, estabilidade = sensitivity(base, classificados, quantis_teste, minimos_teste, cenarios_teste)
    classificados = classificados.merge(estabilidade, on="codigo_ibge_6", validate="one_to_one")
    prioritarios = classificados.loc[classificados["prioritario"].fillna(False)].sort_values(["uf", "municipio"])
    display(tabela_br(tabela_sensibilidade))
    display(sensitivity_figure(tabela_sensibilidade, PASTA_FIGURAS))
    plt.close("all")
    display(tabela_br(prioritarios[["municipio", "uf", "cenarios_elegiveis", "cenarios_selecionado",
                          "cenarios_testados", "fracao_cenarios_selecionado"]].head(30)))
    """)
    md("""
    ## 10. Síntese para o laboratório e limitações

    A síntese reúne a seleção principal, sua sensibilidade e os limites de
    interpretação. As fontes não constituem um retrato simultâneo da população.
    """)
    code(r'''
    elegiveis = int(classificados["elegivel_principal"].sum())
    selecionados = len(prioritarios)
    resumo_execucao = f"""# Síntese exploratória\n\nForam preservados {len(base):,} municípios na união das fontes; \
    {elegiveis:,} são elegíveis para a regra principal e {selecionados:,} apresentam convergência de IVS, \
    CadInsan e DAI elevados e IDHM baixo ({selecionados / elegiveis * 100 if elegiveis else 0:.2f}% dos elegíveis).\n\n\
    Parâmetros: IVS ≥ 0,401 e IDHM < 0,600 (fixos), percentil {QUANTIL * 100:.0f} \
    para CadInsan/DAI, cenário `{CENARIO_CADINSAN}`, mínimo de \
    {MINIMO_AVALIADOS} avaliações de altura. Quantis e mínimo são escolhas exploratórias; \
    a sobreposição não é uma classificação oficial de risco alimentar.\n\n\
    A seleção variou de {tabela_sensibilidade.prioritarios.min()} a \
    {tabela_sensibilidade.prioritarios.max()} municípios nas especificações testadas. \
    Consultar a tabela de sensibilidade para distinguir cenários, cortes e denominadores.\n\n\
    **Referências:** IVS/IDHM de 2010; CadInsan: famílias de janeiro/2025; \
    CadÚnico JSON: pessoas de junho/2026; SISVAN: acompanhamento de menores de cinco anos em 2025.\n\n\
    **Limitações:** diferenças temporais e territoriais; SISVAN representa \
    a população acompanhada; nenhum indicador de cobertura populacional foi calculado; \
    pessoas do JSON e famílias do CadInsan não são unidades intercambiáveis; \
    malha ilustrativa sem ano identificado pela API; associação \
    municipal não demonstra causalidade nem relações individuais.\n\n\
    **Processamento:** percentuais CadInsan recalculados sem arredondamento; \
    percentuais originais preservados. Com os percentuais do CSV, esta configuração selecionaria \
    {total_com_csv} municípios.\n"""
    display(Markdown(resumo_execucao))
    ''')
    md("""
    ## 11. Resultados para consulta e reprodução

    Exportamos a base derivada, lista completa de municípios com convergência,
    cortes, controles de qualidade, sensibilidade, dicionário, resumo e figuras
    em um ZIP. O registro de execução conserva parâmetros e identificação das
    entradas para reprodução. A exportação não inclui dados pessoais individuais.
    O ZIP pode ser baixado pela aba de arquivos do Colab ou pela opção de
    download nos parâmetros.
    """)
    code("""
    identificador = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    destino = PASTA_SAIDA / f"execucao_{identificador}"
    destino.mkdir()
    tabelas = {"base_analitica": classificados, "municipios_prioritarios": prioritarios,
               "cortes": cortes, "controle_integracao": controle_integracao,
               "municipios_sem_correspondencia": ausencias, "sem_classificacao": sem_classificacao,
               "qualidade_sisvan": qualidade_sisvan, "interpretacao_sisvan": interpretacao_sisvan,
               "controle_geometria": controle_geometria,
               "resumo_regional": resumo_regional, "sensibilidade": tabela_sensibilidade,
               "estabilidade": estabilidade, "dicionario_variaveis": dictionary(),
               "validacao_catalogo": validacao_catalogo,
               "comparacao_arredondamento": comparacao_arredondamento,
               "cortes_percentuais_csv": cortes_percentuais_csv,
               "correlacoes_spearman": correlacoes.rename_axis("indicador").reset_index(),
               "n_pares_correlacao": n_pares.rename_axis("indicador").reset_index()}
    for nome, tabela in tabelas.items():
        tabela.to_csv(destino / f"{nome}.csv", index=False, encoding="utf-8-sig")
    figuras_desta_execucao = ["01_distribuicoes", "02_associacoes", "03_correlacoes", "04_sensibilidade"]
    if GERAR_MAPAS:
        figuras_desta_execucao += ["05_disponibilidade", "06_ivs", "07_cadinsan", "08_dai", "09_sobreposicao", "10_idhm"]
    (destino / "figuras").mkdir()
    for nome in figuras_desta_execucao:
        for extensao in ["png", "svg"]:
            shutil.copy2(PASTA_FIGURAS / f"{nome}.{extensao}", destino / "figuras")
    ambiente = {"python": platform.python_version(), "pandas": pd.__version__, "numpy": np.__version__,
                "matplotlib": matplotlib.__version__, "scipy": scipy.__version__}
    manifesto = {"executado_em": datetime.now(timezone.utc).isoformat(),
                 "proveniencia_sisvan": sisvan_metadata(PASTA_DADOS),
                 "formula_dai_pct": "100 * (altura_muito_baixa_n + altura_baixa_n) / avaliados_altura; total zero gera NaN",
                 "quantil": QUANTIL, "minimo_avaliados": MINIMO_AVALIADOS,
                 "cenario_cadinsan": CENARIO_CADINSAN, "cortes": cortes.to_dict("records"),
                 "proveniencia_catalogo": proveniencia_catalogo,
                 "formula_cadinsan_pct": "100 * Cadinsan_absoluto_cenario / Cadastros_Cadunico; sem arredondamento",
                 "municipios_selecionados_com_percentuais_csv": total_com_csv,
                 "municipios_selecionados_sem_arredondamento": total_recalculado,
                 "sensibilidade": tabela_sensibilidade.to_dict("records"), "ambiente": ambiente,
                 "hashes_entrada": hashes_entrada.to_dict("records"), "malha": metadados_malha,
                 "codigo_analise_sha256": CODIGO_ANALISE_SHA256,
                 "regra": "IVS >= 0.401 e IDHM < 0.600 e CadInsan >= corte e DAI >= corte; dados e denominadores válidos",
                 "criterios_primarios": ["ivs", "idhm", "cadinsan", "dai"],
                 "cortes_sociais_fixos": {indicador: {"corte": valor, "operador": operador}
                                         for indicador, (valor, operador) in FIXED_CUTS.items()},
                 "indicadores_com_quantil": ["cadinsan", "dai"],
                 "limites": ["Estudo ecológico exploratório", "Sem inferência causal",
                             "Sem cobertura populacional calculada", "Referências temporais distintas",
                             "Pessoas CadÚnico de junho/2026 e famílias CadInsan de janeiro/2025 não são intercambiáveis"]}
    (destino / "manifesto_execucao.json").write_text(json.dumps(manifesto, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
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
    ## Referências

    - [Repositório de Cozinhas Solidárias — procedência das bases sociais](https://github.com/TriangulosTecnologia/cozsolidarias).
    - [Atlas do Desenvolvimento Humano — PNUD, Ipea e FJP](https://www.undp.org/pt/brazil/desenvolvimento-humano/atlas-do-desenvolvimento-humano-no-brasil).
    - [Cadastro Único — fonte SAGI/MDS](https://aplicacoes.mds.gov.br/sagi/servicos/misocial).
    - [CadInsan — MDS](https://www.gov.br/mds/pt-br/Sisan/vigilancia-do-sisan/CADinsan).
    - [Relatório CadInsan com referência janeiro/2025 — MDS](https://www.gov.br/mds/pt-br/Sisan/vigilancia-do-sisan/CADINSAN2025.pdf).
    - [SISVAN — Ministério da Saúde](https://www.gov.br/saude/pt-br/composicao/saps/vigilancia-alimentar-e-nutricional/sisvan).
    - [IVS e IDHM — Ipea](https://repositorio.ipea.gov.br/bitstream/11058/8257/2/vulnerability.pdf).
    - [Faixas do IVS — Atlas do Ipea](https://repositorio.ipea.gov.br/bitstream/11058/4381/1/Atlas_da_vulnerabilidade_social_nos_municipios_brasileiros.pdf).
    - [Faixas do IDHM — PNUD](https://www.undp.org/sites/g/files/zskgke326/files/2024-05/anexo_estatistico_pnud_21maio24_isbn_web2.pdf).
    - [API de malhas simplificadas v4 — IBGE](https://servicodados.ibge.gov.br/api/docs/malhas?versao=4).
    """)
    # Hash do código-fonte incorporado, para rastrear a análise do manifesto.
    digest = hashlib.sha256((ROOT / "scripts/analise_sobreposicao.py").read_bytes()).hexdigest()
    setup_cell.source += f'\nCODIGO_ANALISE_SHA256 = "{digest}"'
    for index, cell in enumerate(cells):
        cell.id = f"sobreposicao-{index:02d}"
    nb.cells = cells
    nbformat.validate(nb)
    NOTEBOOK.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(nb, NOTEBOOK)
    print(f"Notebook gerado: {NOTEBOOK} ({NOTEBOOK.stat().st_size:,} bytes)")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coletar-malha", action="store_true", help="Obtém a malha de apoio do IBGE.")
    args = parser.parse_args()
    if args.coletar_malha:
        fetch_mesh()
    build()


if __name__ == "__main__":
    main()
