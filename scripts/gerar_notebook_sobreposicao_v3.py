"""Aplica ajustes delimitados à cópia da v2, preservando entradas e células úteis."""

from __future__ import annotations

import ast
import copy
import hashlib
import textwrap
from pathlib import Path

import nbformat

from scripts.gerar_notebook_sobreposicao_v2 import analysis_source as source_v2, SHARED_NAMES

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT / "notebooks/01_sobreposicao_criterios_v2.ipynb"
NOTEBOOK = ROOT / "notebooks/01_sobreposicao_criterios_v3.ipynb"


def analysis_source():
    common = source_v2()
    fragments = []
    for node in ast.parse(common).body:
        name = node.name if isinstance(node, ast.FunctionDef) else (
            node.targets[0].id if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) else None)
        if name in SHARED_NAMES:
            fragments.append(ast.get_source_segment(common, node))
    source = (ROOT / "scripts/analise_sobreposicao_v3.py").read_text()
    node = next(n for n in ast.parse(source).body
                if isinstance(n, ast.ImportFrom) and n.module == "scripts.analise_sobreposicao")
    return source.replace(ast.get_source_segment(source, node),
                          "from decimal import Decimal, InvalidOperation\n\n" + "\n\n".join(fragments))


def build():
    before = hashlib.sha256(ORIGINAL.read_bytes()).hexdigest()
    previous = nbformat.read(ORIGINAL, as_version=4)
    # Garante que o código lido é o da versão de referência, antes de aplicar ajustes.
    if previous.cells[7].source.split("\n", 1)[1].rstrip() != source_v2().rstrip():
        raise ValueError("Código da v2 diverge de seu gerador; revisar antes de atualizar a cópia")
    notebook = copy.deepcopy(previous)
    notebook.metadata["colab"]["name"] = NOTEBOOK.name
    notebook.metadata["origem_v2_sha256"] = before
    for cell in notebook.cells:
        if cell.cell_type == "code":
            cell.outputs = []
            cell.execution_count = None

    def replace(index, old, new):
        if old not in notebook.cells[index].source:
            raise ValueError(f"Trecho esperado ausente na célula {index}: {old[:70]}")
        notebook.cells[index].source = notebook.cells[index].source.replace(old, new)

    def append(index, source):
        notebook.cells[index].source += "\n\n" + textwrap.dedent(source).strip()

    def set_cell(index, source):
        notebook.cells[index].source = textwrap.dedent(source).strip()

    replace(0, "versão 2", "versão 3")
    replace(0, "a alimentar; DAI, a nutricional. DPI é complementar.",
            "a alimentar; DAI + DPI, a nutricional. DAI isolado é a alternativa comparativa.")
    replace(2, "**Nutricional:** utiliza-se **DAI ≥ 6,7% com pelo menos 20 avaliações de altura**.",
            "**Nutricional principal:** exige-se **DAI ≥6,7% E DPI ≥1,8%, com pelo menos 20 avaliações em cada relatório de altura e peso**.\n"
            "DAI representa déficit de altura para idade; DPI, déficit de peso para idade. Ambos se referem a crianças menores de cinco anos.")
    replace(2, "não filtram exclusivamente esse público, DAI é o critério principal e não há\nclusterização. A comparação DAI+DPI exige os mínimos separadamente em cada\nrelatório, sem afirmar que seus denominadores representam as mesmas crianças.\nDPI permanece complementar e não interfere na seleção principal.",
            "não filtram exclusivamente esse público e não há clusterização. O uso conjunto de\nDAI + DPI aproxima a análise da lógica de triagem do Mapa, mas não a reproduz\nliteralmente. Exigem-se mínimos separados em cada relatório, sem afirmar que\nos denominadores representam as mesmas crianças. DAI isolado é uma definição\nalternativa mais abrangente, mantida para comparação e sensibilidade.")
    replace(3, "# porcentagem; indicador complementar", "# porcentagem; componente nutricional principal")
    replace(5, "resultados_sobreposicao_v2", "resultados_sobreposicao_v3")
    replace(5, '"prioritarios", ', '')
    replace(5, '"convergencia_total",', '"convergencia_total", "convergencia_total_dai", "elegiveis_dai",')
    source = analysis_source()
    source_hash = hashlib.sha256(source.encode()).hexdigest()
    replace(5, notebook.cells[5].source.split('CODIGO_ANALISE_SHA256 = ')[1], f'"{source_hash}"')
    set_cell(7, "# @title Funções de análise — executar sem editar\n" + source)

    append(8, """
    ### Cobertura territorial e diferença entre períodos

    As 5.571 unidades da malha e do SISVAN são compatíveis com a estrutura
    territorial publicada pelo IBGE após a instalação de Boa Esperança do Norte:
    **5.569 municípios, mais Brasília (Distrito Federal) e Fernando de Noronha
    (Distrito Estadual)**, tratados como unidades municipais nas estatísticas.
    [IBGE — novo município](https://educa.ibge.gov.br/criancas/voce-sabia/22741-novo-municipio.html).
    O total de 5.570 corresponde ao período anterior à inclusão de Boa Esperança
    do Norte, não a um total imutável. A entrada IVS/IDHM contém 5.565 registros
    de referência 2010; CadInsan, 5.570; os dois relatórios SISVAN, 5.571.
    Os totais efetivos e as ausências são conferidos nas tabelas da execução.

    **Ausências de IVS/IDHM não são automaticamente erros de integração.**
    O IBGE confirma a instalação em 2013 de Mojuí dos Campos (PA), Pescaria
    Brava (SC), Balneário Rincão (SC), Pinto Bandeira (RS) e Paraíso das Águas
    (MS) nas [notas técnicas da MUNIC 2013, abrangência geográfica](https://ftp.ibge.gov.br/Perfil_Municipios/2013/nota_tecnica2013.pdf).
    Boa Esperança do Norte (MT) foi instalado em 1º de janeiro de 2025
    ([IBGE](https://educa.ibge.gov.br/criancas/voce-sabia/22741-novo-municipio.html)).
    Assim, sua ausência no arquivo de referência 2010 é compatível com a mudança
    temporal da malha, sem imputar os índices de municípios de origem. A tabela
    identifica as ausências diretamente nos dados e associa a justificativa
    somente aos códigos com confirmação documental. Casos adicionais exigem revisão.
    """)
    append(9, """
    fonte_instalacao_2013 = "https://ftp.ibge.gov.br/Perfil_Municipios/2013/nota_tecnica2013.pdf"
    fonte_instalacao_2025 = "https://educa.ibge.gov.br/criancas/voce-sabia/22741-novo-municipio.html"
    instalacoes_confirmadas = {
        "150475": (2013, fonte_instalacao_2013), "421265": (2013, fonte_instalacao_2013),
        "422000": (2013, fonte_instalacao_2013), "431454": (2013, fonte_instalacao_2013),
        "500627": (2013, fonte_instalacao_2013), "510183": (2025, fonte_instalacao_2025)}
    municipios_sem_ivs_idhm = base.loc[base[["ivs", "idhm"]].isna().any(axis=1),
        ["codigo_ibge", "codigo_ibge_6", "municipio", "uf", "ivs", "idhm"]].copy()
    municipios_sem_ivs_idhm["ano_instalacao_confirmado"] = municipios_sem_ivs_idhm["codigo_ibge_6"].map(
        lambda c: instalacoes_confirmadas.get(c, (None, None))[0]).astype("Int64")
    municipios_sem_ivs_idhm["fonte_oficial_instalacao"] = municipios_sem_ivs_idhm["codigo_ibge_6"].map(
        lambda c: instalacoes_confirmadas.get(c, (None, None))[1])
    municipios_sem_ivs_idhm["interpretacao_ausencia"] = municipios_sem_ivs_idhm["ano_instalacao_confirmado"].map(
        lambda ano: "Instalação posterior a 2010; ausência compatível com diferença temporal" if pd.notna(ano)
        else "Sem confirmação documental nesta análise; requer revisão")
    display(tabela_br(municipios_sem_ivs_idhm))
    """)
    replace(10, "CadInsan é recalculado sem arredondamento; seus percentuais de origem ficam\nem colunas próprias.",
            "A fonte CadInsan também fornece percentuais arredondados. Como numerador e\ndenominador estão disponíveis, a classificação utiliza a razão recalculada com\nmaior precisão entre famílias em risco estimado e o universo considerado pelo\nCadInsan. Isso evita alterações causadas apenas pelo arredondamento publicado.\nO percentual oficial permanece em colunas próprias para auditoria e apresentação.")
    replace(13, "DAI ≥ 6,7% com ≥20 avaliações de altura", "DAI ≥6,7% **e** DPI ≥1,8%, com ≥20 avaliações **em cada relatório**")
    replace(13, "0 = sem sinais pelos critérios adotados; 1 = atenção; 2 = prioridade alta;\n3 = prioridade muito alta.",
            "0 = sem convergência pelos critérios adotados; 1 = convergência em uma dimensão;\n2 = convergência em duas dimensões; 3 = convergência nas três dimensões.")
    replace(13, "significa que nenhum dos três critérios dimensionais foi satisfeito.",
            "significa que o município não apresentou convergência de sinais segundo os\nindicadores e critérios utilizados nesta análise.")
    replace(13, "DPI ausente ou com poucas avaliações impede apenas sua classificação\ncomplementar e a comparação DAI+DPI, não a seleção principal baseada em DAI.",
            "DAI, DPI ou algum denominador ausente, ou contagem abaixo do mínimo, impede\na classificação nutricional principal: a flag recebe ausência, não `False`,\nmesmo quando outro componente é conhecido e negativo. A convergência geral e\na contagem de dimensões também permanecem ausentes se falta qualquer dimensão.\nA alternativa `dim_nutricional_dai` requer somente DAI e avaliações de altura;\n`convergencia_total_dai` utiliza essa alternativa exclusivamente para comparação.")
    replace(14, "classe_prioridade", "classe_convergencia")
    replace(14, "PRIORITY_LABELS", "CONVERGENCE_LABELS")
    replace(14, '"avaliados_altura", "motivo_nao_classificacao"',
            '"avaliados_altura", "avaliados_peso", "dai_pct", "dpi_pct", "motivo_nao_classificacao"')
    replace(14, "CENARIO_CADINSAN, CORTE_DAI)", "CENARIO_CADINSAN, CORTE_DAI, CORTE_DPI)")
    append(14, """
    mudou_lado_p75 = int(comparacao_arredondamento["mudou_criterio_cadinsan"].sum())
    display(Markdown(f"Usar o percentual arredondado mudaria o lado do corte alimentar "
        f"para **{contagem_br(mudou_lado_p75)} municípios**, recalculando P75 em cada versão. "
        f"Isso não equivale necessariamente a alterar a convergência total: "
        f"Total de mudanças na seleção final: **{contagem_br(int(comparacao_arredondamento['mudou_selecao'].sum()))}**."))
    """)
    append(15, "A dimensão nutricional principal utiliza DAI + DPI; a convergência baseada apenas em DAI não integra estes totais ou mapas principais.")
    replace(16, '"dai_pct": "DAI (%)",', '"dai_pct": "DAI (%)", "dpi_pct": "DPI (%)", "avaliados_peso": "Avaliações de peso",')
    replace(18, "A alternativa nutricional exige **DAI ≥6,7% E DPI ≥1,8%**, com pelo menos\n20 avaliações **em cada relatório**.",
            "A definição principal exige **DAI ≥6,7% E DPI ≥1,8%**, com pelo menos\n20 avaliações **em cada relatório**. A alternativa utiliza apenas DAI ≥6,7% e\no mínimo de altura, sendo mais abrangente.")
    replace(18, "A alternativa não muda a seleção principal.",
            "DAI isolado serve para comparação, não substitui a definição principal DAI + DPI.")
    append(19, """
    total_dai = int(classificados["convergencia_total_dai"].sum())
    total_combinado = int(classificados["convergencia_total"].sum())
    diferenca_nutricional = total_dai - total_combinado
    display(Markdown(f"**Convergência com DAI isolado:** {contagem_br(total_dai)} municípios.\\n\\n"
        f"**Convergência com DAI + DPI (principal):** {contagem_br(total_combinado)}.\\n\\n"
        f"**Diferença:** {contagem_br(diferenca_nutricional)}. O critério conjunto requer "
        "sinais desfavoráveis nos dois indicadores municipais. Não identifica necessariamente "
        "as mesmas crianças com os dois déficits; diferenças de elegibilidade são mostradas acima."))
    """)
    replace(21, '"Convergência social, alimentar e nutricional"', '"Convergência social, alimentar e nutricional (DAI + DPI)"')
    append(23, """
    rho_nutricional = correlacoes.loc["dai_pct", "dpi_pct"]
    display(Markdown(f"**DAI–DPI:** Spearman = {numero_br(rho_nutricional)}; "
        "indicadores relacionados, mas não intercambiáveis. As relações entre dimensões "
        "(social, CadInsan e nutrição) devem ser lidas na matriz, não como efeitos causais."))
    pares_entre_dimensoes = pd.DataFrame([
        {"par": f"{a.upper()} × {b.upper()}", "spearman": correlacoes.loc[a, b],
         "municipios": n_pares.loc[a, b]}
        for a in ["ivs", "idhm", "cadinsan_pct"] for b in ["dai_pct", "dpi_pct"]])
    display(tabela_br(pares_entre_dimensoes))
    """)
    append(24, """
    Nesta sensibilidade, **DAI + DPI permanece a definição principal**: o corte
    DPI é mantido em 1,8% (ou no valor da célula de parâmetros), enquanto o
    componente DAI varia. O mínimo aplica-se **separadamente a altura e peso**.
    A coluna `convergencia_total_dai` mostra, em cada cenário, a alternativa DAI
    isolado. Não se misturam seus totais com a convergência principal.
    A interpretação compara separadamente o efeito dos mínimos, do CadInsan
    e do DAI, não apenas a amplitude das combinações.
    """)
    replace(25, "list(dict.fromkeys(CORTES_DAI_SENSIBILIDADE + [CORTE_DAI])))",
            "list(dict.fromkeys(CORTES_DAI_SENSIBILIDADE + [CORTE_DAI])), CORTE_DPI)")
    append(26, """
    - **DAI e DPI:** descrevem dimensões relacionadas do estado nutricional
      infantil, mas não capturam toda a complexidade da insegurança alimentar.
      A exigência conjunta é municipal, não comprova coocorrência individual.
      Denominadores menores continuam sujeitos a maior variabilidade mesmo ≥20.
    """)
    set_cell(28, r'''
    selecionados = len(convergentes)
    # Empates regionais são preservados: não se escolhe arbitrariamente uma região.
    max_absoluto = resumo_regional["convergencia_total"].max()
    max_proporcao = resumo_regional["pct_convergencia_elegiveis"].max()
    regioes_absoluto = ", ".join(resumo_regional.loc[resumo_regional["convergencia_total"].eq(max_absoluto), "regiao"])
    regioes_proporcao = ", ".join(resumo_regional.loc[resumo_regional["pct_convergencia_elegiveis"].eq(max_proporcao), "regiao"])
    linhas_regionais = "\n".join(
        f"- {r.regiao}: {contagem_br(r.convergencia_total)} de {contagem_br(r.elegiveis)} elegíveis "
        f"({percentual_br(r.pct_convergencia_elegiveis)})." for r in resumo_regional.itertuples())
    def descrever_cenarios(tabela, parametro):
        def rotulo(valor):
            if parametro == "quantil":
                return f"P{valor * 100:.0f}"
            if parametro == "referencia_dai":
                return "P75" if valor == "P75" else numero_br(float(valor), 1) + "%"
            return f"n ≥ {valor}"
        return "; ".join(f"{rotulo(getattr(r, parametro))} → {contagem_br(r.convergencia_total)}" for r in tabela.itertuples())
    def amplitude(tabela):
        return int(tabela["convergencia_total"].max() - tabela["convergencia_total"].min())
    amplitudes = {"mínimo SISVAN": amplitude(sensibilidade_minimos),
                  "quantil CadInsan": amplitude(sensibilidade_cadinsan),
                  "componente DAI": amplitude(sensibilidade_dai)}
    maior_amplitude = max(amplitudes.values())
    menor_amplitude = min(amplitudes.values())
    parametros_maior = ", ".join(k for k, v in amplitudes.items() if v == maior_amplitude)
    parametros_menor = ", ".join(k for k, v in amplitudes.items() if v == menor_amplitude)
    mudanca_maxima_minimo = max(
        sensibilidade_minimos["entram_vs_principal"].max(),
        sensibilidade_minimos["saem_vs_principal"].max())
    interpretacao_minimos = (
        f"Maior número de entradas/saídas em relação ao cenário principal: {contagem_br(mudanca_maxima_minimo)} "
        f"(seleção principal: {contagem_br(selecionados)} unidades). "
        "Isso não demonstra precisão ou representatividade das estimativas."
    )
    if amplitudes["mínimo SISVAN"] < min(amplitudes["quantil CadInsan"], amplitudes["componente DAI"]):
        interpretacao_minimos += " A classificação mostrou-se comparativamente pouco sensível ao mínimo entre 20 e 100 neste conjunto."
    resumo_execucao = f"""# Síntese da análise municipal — v3

    **Universo:** {contagem_br(len(base))} unidades municipais; **{contagem_br(elegiveis)} avaliáveis**
    nas três dimensões principais e **{contagem_br(len(base) - elegiveis)} com dados insuficientes**.
    As contagens de cada dimensão entre todos os classificáveis nela são:
    **social {contagem_br(int(classificados['dim_social'].sum()))}**,
    **alimentar {contagem_br(int(classificados['dim_alimentar'].sum()))}** e
    **nutricional DAI + DPI {contagem_br(int(classificados['dim_nutricional'].sum()))}**.
    Esses universos dimensionais podem diferir; no universo comum de elegíveis,
    as contagens são, respectivamente,
    {contagem_br(int(classificados.loc[classificados.elegivel_principal, 'dim_social'].sum()))},
    {contagem_br(int(classificados.loc[classificados.elegivel_principal, 'dim_alimentar'].sum()))} e
    {contagem_br(int(classificados.loc[classificados.elegivel_principal, 'dim_nutricional'].sum()))}.

    **Convergência principal: {contagem_br(selecionados)} unidades**, ou
    **{percentual_br(selecionados / elegiveis * 100 if elegiveis else np.nan)} dos elegíveis**;
    {percentual_br(selecionados_na_malha / len(universo_ibge) * 100)} da malha IBGE incorporada.
    Esses municípios apresentam convergência dos indicadores desfavoráveis segundo
    os critérios adotados, não constituem um ranking dos mais vulneráveis do Brasil.
    Regra: IVS ≥0,401 E IDHM <0,600; CadInsan ≥P{QUANTIL_CADINSAN * 100:.0f}
    ({CENARIO_CADINSAN}); DAI ≥{numero_br(CORTE_DAI, 1)}% E DPI ≥{numero_br(CORTE_DPI, 1)}%,
    com ≥{MINIMO_AVALIADOS} avaliações em cada relatório.

    **Distribuição regional — convergência / elegíveis da própria região:**

    {linhas_regionais}

    A maior concentração absoluta está em **{regioes_absoluto}**
    ({contagem_br(max_absoluto)} unidades); a maior proporção entre elegíveis
    está em **{regioes_proporcao}** ({percentual_br(max_proporcao)}).
    Prevalência regional da classificação municipal não equivale à prevalência
    de fome nas pessoas; concentração absoluta e proporção têm denominadores distintos.

    **Comparação nutricional:** DAI isolado seleciona {contagem_br(total_dai)};
    DAI + DPI seleciona {contagem_br(total_combinado)}; diferença de
    {contagem_br(diferenca_nutricional)} unidades. A alternativa é mais abrangente.

    **Sensibilidade — uma mudança por vez, mantendo os demais parâmetros principais:**

    - Mínimo SISVAN (altura e peso): {descrever_cenarios(sensibilidade_minimos, 'minimo_avaliados')}.
      {interpretacao_minimos}
    - CadInsan: {descrever_cenarios(sensibilidade_cadinsan, 'quantil')}.
      Amplitude de {contagem_br(amplitudes['quantil CadInsan'])} unidades; P75 não é corte oficial.
    - DAI: {descrever_cenarios(sensibilidade_dai, 'referencia_dai')}.
      Amplitude de {contagem_br(amplitudes['componente DAI'])} unidades, mantendo DPI fixo.
      6,7% é referência Mapa InSAN, 10% inicia categoria OMS média, P75 é distributivo.

    Nos intervalos testados, **{parametros_menor}** tem menor amplitude
    ({contagem_br(menor_amplitude)}), e **{parametros_maior}** tem maior
    ({contagem_br(maior_amplitude)}). Trata-se de dependência nos cenários escolhidos,
    não de uma medida universal de importância. As listas e entradas/saídas
    mostram quais conclusões resistem a cada mudança; o total isolado não basta.
    As {len(tabela_sensibilidade)} combinações variam entre
    {contagem_br(tabela_sensibilidade.convergencia_total.min())} e
    {contagem_br(tabela_sensibilidade.convergencia_total.max())}; essa amplitude é
    secundária e não é intervalo de confiança.

    **Associações:** IVS–IDHM, Spearman {numero_br(rho_social)} ({relacao_social});
    DAI–DPI, {numero_br(rho_nutricional)}. As relações entre dimensões estão
    na matriz de pares disponíveis; nenhuma demonstra causalidade.

    **Limitações centrais:** dimensão social histórica (2010), fontes alimentares e
    nutricionais de 2025, população SISVAN não necessariamente representativa,
    variabilidade dos denominadores, P75 exploratório e ausência de ligação
    individual altura/peso. DAI e DPI não esgotam a insegurança alimentar.
    Os {contagem_br(len(municipios_sem_ivs_idhm))} casos sem IVS/IDHM são listados
    com fontes oficiais; não se imputam índices históricos de municípios de origem.
    Validar a interpretação científica dessas escolhas com o orientador antes de
    extrapolar os resultados a toda a população ou usá-los para recomendação de políticas.
    """
    # Remove indentação de apresentação sem alterar cálculos ou valores exportados.
    resumo_execucao = "\n".join(line[4:] if line.startswith("    ") else line for line in resumo_execucao.splitlines())
    display(Markdown(resumo_execucao))
    ''')
    replace(30, '"versao": 2', '"versao": 3')
    replace(30, '"corte_dpi_pct_complementar"', '"corte_dpi_pct"')
    replace(30, '"DAI >= corte principal E altura com denominador mínimo"',
            '"DAI >= corte E DPI >= corte E mínimos separados de altura e peso"')
    replace(30, '"Convergência das três dimensões; DPI não integra seleção principal"',
            '"Convergência das três dimensões; nutrição DAI + DPI; DAI isolado é alternativa"')
    replace(30, '"base_municipal_final": classificados,',
            '"base_municipal_final": classificados, "municipios_sem_ivs_idhm": municipios_sem_ivs_idhm,')
    replace(30, '"cortes": cortes.to_dict("records")',
            '"cortes": json.loads(cortes.to_json(orient="records"))')
    replace(30, 'ensure_ascii=False, indent=2)', 'ensure_ascii=False, indent=2, allow_nan=False)')
    append(31, """
    - IBGE. [MUNIC 2013 — notas técnicas](https://ftp.ibge.gov.br/Perfil_Municipios/2013/nota_tecnica2013.pdf), abrangência geográfica: instalação dos cinco municípios posteriores a 2010 e tratamento de Brasília/Fernando de Noronha.
    - IBGE. [Boa Esperança do Norte — novo município](https://educa.ibge.gov.br/criancas/voce-sabia/22741-novo-municipio.html), instalação em 1º/1/2025: 5.569 municípios mais Distrito Federal e Distrito Estadual, total estatístico de 5.571 unidades.
    """)
    nbformat.validate(notebook)
    for i, cell in enumerate(notebook.cells):
        if cell.cell_type == "code":
            compile(cell.source, f"<v3-celula-{i}>", "exec")
    nbformat.write(notebook, NOTEBOOK)
    if hashlib.sha256(ORIGINAL.read_bytes()).hexdigest() != before:
        raise RuntimeError("A v2 foi alterada")
    return NOTEBOOK


if __name__ == "__main__":
    print(build())
