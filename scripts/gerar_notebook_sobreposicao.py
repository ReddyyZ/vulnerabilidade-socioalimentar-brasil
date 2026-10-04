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
    files["documentacao/README_SISVAN.md"] = ROOT / "dados/tratados/sisvan/criancas_menores_5/README.md"
    files["documentacao/SISVAN.metadados.json"] = ROOT / "dados/tratados/sisvan/criancas_menores_5/indicadores_altura_peso_idade_menores_5_2025.metadados.json"
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

    md("""
    # Áreas de risco alimentar e vulnerabilidade social no Brasil

    **Estudo ecológico municipal — sobreposição de critérios.**

    Pergunta: onde coincidem IVS elevado, IDHM baixo, risco alimentar estimado elevado no
    CadInsan e déficit de altura/estatura para idade (DAI) elevado no SISVAN?

    IVS/IDHM: **2010**. CadInsan: **famílias, janeiro de 2025**.
    CadÚnico JSON: **pessoas, junho de 2026**. SISVAN: crianças de
    **0 a menos de 5 anos acompanhadas pelo sistema durante 2025**.
    O catálogo corresponde por hash às três bases sociais. A análise é exploratória e não estabelece
    causalidade nem estima a prevalência de fome na população inteira.

    **Como executar:** no Colab, abrir este `.ipynb` pelo menu **Arquivo → Abrir
    notebook → Upload**, revisar os parâmetros abaixo e usar **Ambiente de
    execução → Executar tudo**. As quatro bases e a malha de apoio estão
    incorporadas; não é necessário fornecer outros arquivos ou credenciais.
    A instalação de dependências pode exigir internet. As fontes embutidas
    ficam preservadas; os resultados vão para uma pasta separada.

    **Versão das quatro bases selecionadas:** commit `3391236`. O processamento
    abaixo deriva indicadores analíticos e mantém também os valores do arquivo.
    """)
    md("""
    ## 1. Parâmetros da análise

    A regra principal exige **os quatro critérios simultaneamente**: IVS,
    CadInsan e DAI elevados, e IDHM baixo. DPI e CadÚnico contextualizam os
    resultados, sem participar da seleção principal.

    P75 e mínimo de 100 avaliações são pontos de partida exploratórios, editáveis
    e sem caráter oficial. O corte do DAI é calculado sobre municípios com o
    denominador mínimo; IVS, IDHM e CadInsan usam seus próprios municípios disponíveis.
    O IDHM usa o percentil `100 × (1 − QUANTIL)`: com `0.75`, exige IDHM ≤ P25;
    com `0.80`, IDHM ≤ P20. Nenhuma transformação do valor original é necessária.
    Cada município tem o mesmo peso nos quantis; empates no corte são incluídos.
    Por isso o grupo elevado pode conter mais de 25% dos municípios.

    `com_PBF` é o cenário inicial, considerando o efeito do benefício na renda.
    `sem_PBF` é o cenário contrafactual que desconsidera esse efeito e entra na
    sensibilidade. Não são dois grupos de beneficiários e não beneficiários.
    O catálogo e o relatório do MDS documentam unidades e cenários; o relatório
    indica janeiro/2025 e famílias com cadastro atualizado nos últimos 12 meses.
    O denominador é o universo de famílias considerado no arquivo CadInsan.
    O JSON de pessoas em junho/2026 não substitui esse denominador.

    Os percentuais CadInsan são **recalculados sem arredondamento** pelos
    valores absolutos e denominadores do CSV. As proporções originais ficam
    preservadas em `*_arquivo`. Essa escolha evita empates artificiais por
    arredondamento e reproduz o procedimento descrito no catálogo.
    """)
    code("""
    QUANTIL = 0.75
    MINIMO_AVALIADOS = 100
    CENARIO_CADINSAN = "com_PBF"  # opções: "com_PBF", "sem_PBF"
    QUANTIS_SENSIBILIDADE = [0.75, 0.80]
    MINIMOS_SENSIBILIDADE = [30, 50, 100]
    CENARIOS_SENSIBILIDADE = ["com_PBF", "sem_PBF"]
    GERAR_MAPAS = True
    BAIXAR_RESULTADOS_NO_COLAB = False  # True solicita download do ZIP no final

    """)
    md("""
    ## 2. Ambiente e recuperação das bases incorporadas

    Esta célula confere bibliotecas e restaura o pacote autocontido em uma pasta
    da sessão. A próxima célula contém o pacote compactado e pode ficar recolhida.
    Os hashes das quatro bases são conferidos antes do processamento. A malha
    tem hash próprio. Não há nova consulta ao SISVAN ou às fontes sociais.
    """)
    code("""
    import importlib.util
    import subprocess
    import sys
    from pathlib import Path

    packages = {"pandas": "pandas>=2.2,<4", "numpy": "numpy>=1.26,<3",
                "matplotlib": "matplotlib>=3.8,<4", "scipy": "scipy>=1.11,<2"}
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
    pd.set_option("display.float_format", lambda x: f"{x:.3f}")
    print("Resultados:", PASTA_SAIDA)
    """)
    encoded = payload()
    code('# @title Bases e malha incorporadas — executar sem editar\n'
         f'PACOTE_BASE64 = "{encoded}"\n'
         'with zipfile.ZipFile(io.BytesIO(base64.b64decode(PACOTE_BASE64))) as pacote:\n'
         '    for membro in pacote.infolist():\n'
         '        destino = (PASTA_DADOS / membro.filename).resolve()\n'
         '        if not destino.is_relative_to(PASTA_DADOS.resolve()):\n'
         '            raise ValueError("Caminho inválido no pacote de dados")\n'
         '    pacote.extractall(PASTA_DADOS)\n'
         'print("Pacote recuperado. As quatro bases mantêm seus bytes originais.")', hidden=True)
    md("""
    ## 3. Funções reproduzíveis de leitura e análise

    O código abaixo é incorporado de `scripts/analise_sobreposicao.py`. Ele
    converte números somente em memória, valida categorias e denominadores,
    realiza junções externas `one_to_one` por prefixos únicos e calcula as flags
    com valores ausentes quando a classificação não é possível. Pode ser
    expandido para auditoria; as células seguintes mostram a execução.
    """)
    code('# @title Funções de análise — executar sem editar\n' +
         (ROOT / "scripts/analise_sobreposicao.py").read_text(encoding="utf-8"), hidden=True)
    code("""
    validacao_catalogo, proveniencia_catalogo = validate_catalogue(
        PASTA_DADOS / "documentacao/dataset_catalogue.json", PASTA_DADOS)
    base, controle_integracao, hashes_entrada = prepare_base(PASTA_DADOS)
    figure_style()
    print("Municípios na união:", len(base))
    display(hashes_entrada)
    display(validacao_catalogo)
    display(controle_integracao)
    ausencias = base.loc[~base[["tem_ivs_idhm", "tem_cadunico", "tem_cadinsan", "tem_sisvan"]].all(axis=1),
                         ["codigo_ibge_6", "codigo_ibge_7", "municipio", "uf",
                          "tem_ivs_idhm", "tem_cadunico", "tem_cadinsan", "tem_sisvan"]]
    display(ausencias)
    display(dictionary())
    """)
    md("""
    **Interpretação:** a união preserva municípios sem informações sociais.
    Código SISVAN tem seis dígitos; as fontes sociais têm sete. Prefixos e códigos
    são conferidos quanto à unicidade e a conflitos. A malha será auditada mais
    adiante. Isso não demonstra que limites territoriais de 2010 e 2025 sejam
    idênticos. CadÚnico JSON (pessoas, junho/2026) e `Cadastros_Cadunico`
    (famílias, janeiro/2025) ficam separados. Sem denominador populacional
    compatível, a contagem de pessoas não se transforma em proporção de cobertura.
    """)
    md(r"""
    ## 4. Indicadores recalculados e qualidade

    $$DAI(\%)=100\times\frac{N(\text{altura muito baixa})+N(\text{altura baixa})}
    {N(\text{avaliados em altura por idade})}$$

    $$DPI(\%)=100\times\frac{N(\text{peso muito baixo})+N(\text{peso baixo})}
    {N(\text{avaliados em peso por idade})}$$

    $$CadInsan_{cenario}(\%)=100\times
    \frac{Cadinsan\_absoluto\_{cenario}}{Cadastros\_Cadunico}$$

    Os indicadores são recalculados **sem arredondamento** para comparação e
    classificação. Os valores arredondados do CSV ficam preservados nas colunas
    `*_pct_arquivo`. Denominador zero produz `NaN` analítico, mesmo que o CSV
    informe `0.0`. DAI e DPI não podem ser somados, nem os seus denominadores.
    """)
    code("""
    qualidade_sisvan = pd.DataFrame({
        "controle": ["Sem avaliações de altura", "Sem avaliações de peso",
                     "Denominadores distintos", "Altura abaixo do mínimo principal",
                     "Peso abaixo do mínimo principal"],
        "municipios": [int(base["avaliados_altura"].eq(0).sum()),
                       int(base["avaliados_peso"].eq(0).sum()),
                       int((base["tem_sisvan"] & base["avaliados_altura"].ne(base["avaliados_peso"])).sum()),
                       int(base["avaliados_altura"].between(1, MINIMO_AVALIADOS - 1).sum()),
                       int(base["avaliados_peso"].between(1, MINIMO_AVALIADOS - 1).sum())]})
    display(qualidade_sisvan)
    display(base.loc[base["avaliados_altura"].eq(0),
                     ["municipio", "uf", "dai_pct_arquivo", "dai_pct", "avaliados_altura"]])
    totais = []
    for indicador, denominador in [("dai", "avaliados_altura"), ("dpi", "avaliados_peso")]:
        n = base[f"{indicador}_n"].sum()
        d = base[denominador].sum()
        totais.append({"indicador": indicador.upper(), "numerador": n,
                       "denominador": d, "percentual_agregado": n / d * 100})
    display(pd.DataFrame(totais))
    """)
    md("""
    **Interpretação:** esses totais descrevem os registros dos relatórios
    consultados, sem demonstração de cobertura ou unicidade individual além da
    metodologia da fonte. Os percentuais agregados são razões entre somas, não
    médias dos percentuais municipais. Muitos registros não garantem
    representatividade. A população municipal de menores de cinco anos não está
    disponível neste pacote; portanto não calculamos cobertura populacional.
    """)
    md("""
    ## 5. Classificação exploratória

    Ser prioritário exige IVS ≥ corte, IDHM ≤ corte, CadInsan ≥ corte e DAI ≥ corte,
    além de dados válidos para os quatro critérios e do mínimo de avaliações de
    altura. IDHM ausente impede a classificação principal. DPI é complementar
    e tem seu próprio mínimo de avaliações.
    Informação insuficiente é diferente de ausência de risco.
    """)
    code("""
    classificados, cortes = classify(base, QUANTIL, MINIMO_AVALIADOS, CENARIO_CADINSAN)
    display(cortes)
    display(classificados["perfil"].value_counts().rename_axis("perfil").reset_index(name="municipios"))
    sem_classificacao = classificados.loc[~classificados["elegivel_principal"],
        ["codigo_ibge_6", "municipio", "uf", "avaliados_altura", "motivo_nao_classificacao"]]
    display(sem_classificacao)
    comparacao_arredondamento, cortes_percentuais_csv = compare_rounding(
        base, classificados, QUANTIL, MINIMO_AVALIADOS, CENARIO_CADINSAN)
    total_com_csv = int(comparacao_arredondamento["selecionado_percentual_csv"].fillna(False).sum())
    total_recalculado = int(classificados["prioritario"].fillna(False).sum())
    display(Markdown(f"**Efeito do arredondamento:** {total_com_csv} municípios com percentuais do CSV; "
                     f"{total_recalculado} com as razões sem arredondamento usadas na análise."))
    display(comparacao_arredondamento.loc[comparacao_arredondamento["mudou_selecao"]])
    display(Markdown("**CadÚnico:** pessoas de junho/2026 são informação contextual; "
                     "a regra principal é IVS elevado + IDHM baixo + CadInsan elevado + DAI elevado."))
    """)
    md("""
    ## 6. Distribuições, associações e redundância

    As distribuições nutricionais mostram todos os municípios com avaliações.
    Os gráficos de associação usam municípios elegíveis para a regra principal.
    A correlação usa pares disponíveis, com denominadores nutricionais acima do
    mínimo; cada par apresenta seu número de municípios. As linhas tracejadas
    são os cortes exploratórios. Vermelho indica convergência dos quatro critérios.
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

    A malha simplificada incorporada vem da **API v4 do IBGE**. Essa versão não
    informa o ano por parâmetro; não a descrevemos como malha de 2025. A data,
    URL e hash estão nos metadados. A geometria é apoio ilustrativo: os códigos
    são auditados, mas isso não harmoniza limites históricos. Municípios sem
    informações suficientes permanecem visíveis em cinza.
    """)
    code("""
    caminho_malha = PASTA_DADOS / "apoio/ibge/malha_municipal_simplificada.geojson"
    metadados_malha = json.loads((PASTA_DADOS / "apoio/ibge/malha_municipal_simplificada.metadados.json").read_text())
    if hashlib.sha256(caminho_malha.read_bytes()).hexdigest() != metadados_malha["sha256"]:
        raise ValueError("Hash da malha diferente do registrado")
    geometria = json.loads(caminho_malha.read_text())
    controle_geometria = geometry_audit(geometria, base)
    display(pd.DataFrame([metadados_malha]))
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

    A tabela exibe os municípios com convergência e os indicadores que justificam
    sua seleção. Está ordenada por UF e município, **sem ranking composto**.
    As regiões apresentam DAI/DPI pela razão entre somas de numeradores e
    denominadores, usando todos os registros válidos do respectivo índice.
    """)
    code("""
    colunas_apresentacao = ["codigo_ibge_6", "codigo_ibge_7", "municipio", "uf", "ivs", "idhm",
                           "cadinsan_pct", "cadinsan_n", "dai_pct", "avaliados_altura",
                           "dpi_pct", "avaliados_peso", "cadunico_pessoas_2026_06", "cadastros_cadunico_cadinsan",
                           "criterio_idhm", "criterio_dpi"]
    prioritarios = classificados.loc[classificados["prioritario"].fillna(False)].sort_values(["uf", "municipio"])
    print("Municípios com convergência:", len(prioritarios))
    display(prioritarios[colunas_apresentacao].head(30))
    print("Prévia dos primeiros 30; a tabela completa será exportada.")
    resumo_regional = regional_summary(classificados)
    display(resumo_regional)
    """)
    md("""
    ## 9. Sensibilidade e estabilidade da seleção

    Cada cenário recalcula os cortes nacionais, inclusive o corte do DAI sobre
    municípios com o mínimo escolhido. Portanto a comparação avalia tanto a
    mudança de elegibilidade quanto a mudança da referência do corte. O Jaccard
    compara a interseção das listas com sua união, em relação à regra principal.
    Percentis 75/80 nos indicadores elevados correspondem aos percentis 25/20
    no IDHM; os quatro critérios permanecem obrigatórios em todas as especificações.

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
    display(tabela_sensibilidade)
    display(sensitivity_figure(tabela_sensibilidade, PASTA_FIGURAS))
    plt.close("all")
    display(prioritarios[["municipio", "uf", "cenarios_elegiveis", "cenarios_selecionado",
                          "cenarios_testados", "fracao_cenarios_selecionado"]].head(30))
    """)
    md("""
    ## 10. Síntese para o laboratório e limitações

    A síntese abaixo é preenchida com os resultados da execução. Antes de usar
    como conclusão definitiva, discutir os cortes exploratórios e a
    compatibilidade temporal e territorial das fontes.
    """)
    code(r'''
    elegiveis = int(classificados["elegivel_principal"].sum())
    selecionados = len(prioritarios)
    resumo_execucao = f"""# Síntese exploratória\n\nForam preservados {len(base):,} municípios na união das fontes; \
    {elegiveis:,} são elegíveis para a regra principal e {selecionados:,} apresentam convergência de IVS, \
    CadInsan e DAI elevados e IDHM baixo ({selecionados / elegiveis * 100 if elegiveis else 0:.2f}% dos elegíveis).\n\n\
    Parâmetros: percentil {QUANTIL * 100:.0f} para IVS/CadInsan/DAI, \
    percentil {(1 - QUANTIL) * 100:.0f} para IDHM, cenário `{CENARIO_CADINSAN}`, mínimo de \
    {MINIMO_AVALIADOS} avaliações de altura. Os cortes são relativos e não classificações oficiais.\n\n\
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
    {total_com_csv} municípios. O catálogo incorporado corresponde às três bases sociais por hash.\n"""
    display(Markdown(resumo_execucao))
    ''')
    md("""
    ## 11. Exportação e reprodução

    Exportamos a base derivada, lista completa de municípios com convergência,
    cortes, controles de qualidade, sensibilidade, dicionário, resumo e figuras
    PNG/SVG. Os CSVs usam UTF-8 com BOM. O manifesto registra parâmetros, hashes e
    versões efetivamente utilizadas. A execução não modifica as quatro bases.

    Cada execução recebe uma pasta própria, evitando mistura de figuras de
    configurações distintas. Um ZIP reúne resultados e documentação das entradas.
    Para baixar no Colab, ativar `BAIXAR_RESULTADOS_NO_COLAB` no início ou usar
    a aba de arquivos. A exportação não inclui dados pessoais individuais.
    """)
    code("""
    identificador = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    destino = PASTA_SAIDA / f"execucao_{identificador}"
    destino.mkdir()
    tabelas = {"base_analitica": classificados, "municipios_prioritarios": prioritarios,
               "cortes": cortes, "controle_integracao": controle_integracao,
               "municipios_sem_correspondencia": ausencias, "sem_classificacao": sem_classificacao,
               "qualidade_sisvan": qualidade_sisvan, "controle_geometria": controle_geometria,
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
                 "versao_bases": "3391236", "quantil": QUANTIL, "minimo_avaliados": MINIMO_AVALIADOS,
                 "cenario_cadinsan": CENARIO_CADINSAN, "cortes": cortes.to_dict("records"),
                 "proveniencia_catalogo": proveniencia_catalogo,
                 "formula_cadinsan_pct": "100 * Cadinsan_absoluto_cenario / Cadastros_Cadunico; sem arredondamento",
                 "municipios_selecionados_com_percentuais_csv": total_com_csv,
                 "municipios_selecionados_sem_arredondamento": total_recalculado,
                 "sensibilidade": tabela_sensibilidade.to_dict("records"), "ambiente": ambiente,
                 "hashes_entrada": hashes_entrada.to_dict("records"), "malha": metadados_malha,
                 "codigo_analise_sha256": CODIGO_ANALISE_SHA256,
                 "regra": "IVS >= corte e IDHM <= corte e CadInsan >= corte e DAI >= corte; dados e denominadores válidos",
                 "criterios_primarios": ["ivs", "idhm", "cadinsan", "dai"],
                 "quantil_idhm": 1 - QUANTIL,
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
    display(pd.DataFrame([ambiente]))
    if BAIXAR_RESULTADOS_NO_COLAB:
        try:
            from google.colab import files
        except ImportError:
            print("Fora do Colab: utilizar o ZIP no caminho informado.")
        else:
            files.download(arquivo_zip)
    """)
    md("""
    ## Referências e documentação

    - [CadInsan — MDS](https://www.gov.br/mds/pt-br/Sisan/monitoramento-da-san/cadinsan).
    - [Relatório CadInsan com referência janeiro/2025 — MDS](https://www.gov.br/mds/pt-br/Sisan/vigilancia-do-sisan/CADINSAN2025.pdf).
    - [SISVAN — Ministério da Saúde](https://www.gov.br/saude/pt-br/composicao/saps/vigilancia-alimentar-e-nutricional/sisvan).
    - [IVS e IDHM — Ipea](https://repositorio.ipea.gov.br/bitstream/11058/8257/2/vulnerability.pdf).
    - [API de malhas simplificadas v4 — IBGE](https://servicodados.ibge.gov.br/api/docs/malhas?versao=4).
    - No projeto: `docs/metodologia/PLANO_ANALISE_NOTEBOOK_COLAB.md`,
      `dados/pesquisa/README.md`, `dataset_catalogue.json`, `scripts/analise_sobreposicao.py` e
      `scripts/gerar_notebook_sobreposicao.py`.

    Unidades e períodos são documentados no catálogo, com correspondência de
    hashes. O relatório oficial complementa a referência mensal e os cenários
    do CadInsan. Essa validação documental não elimina limites de desenho,
    cobertura, compatibilidade territorial ou escolhas exploratórias de corte.
    """)
    # Hash do código-fonte incorporado, para rastrear a análise do manifesto.
    digest = hashlib.sha256((ROOT / "scripts/analise_sobreposicao.py").read_bytes()).hexdigest()
    cells[2].source += f'\nCODIGO_ANALISE_SHA256 = "{digest}"'
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
