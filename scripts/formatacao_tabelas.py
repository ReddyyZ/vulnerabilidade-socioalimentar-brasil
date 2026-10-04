"""Formatação brasileira de tabelas, sem transformar os dados analíticos."""

import pandas as pd
from pandas.api.types import is_bool_dtype, is_integer_dtype, is_numeric_dtype


COLUNAS_CONTAGEM = {
    "municipios", "registros_origem", "municipios_na_uniao",
    "correspondencias_sisvan", "sisvan_sem_fonte", "fonte_sem_sisvan",
    "numerador", "denominador", "municipios_referencia", "municipios_no_criterio",
    "percentil", "elegiveis", "prioritarios", "coincidentes_principal",
    "minimo_avaliados", "cenarios_elegiveis", "cenarios_selecionado", "cenarios_testados",
    "cadastros_cadunico_cadinsan", "cadunico_pessoas_2026_06",
}


def numero_br(valor, casas=3):
    if pd.isna(valor):
        return "—"
    return f"{valor:,.{casas}f}".translate(str.maketrans({",": ".", ".": ","}))


def contagem_br(valor):
    return numero_br(valor, 0)


def percentual_br(valor):
    return "—" if pd.isna(valor) else numero_br(valor, 2) + "%"


def quantil_br(valor):
    return numero_br(valor, 2)


def tabela_br(tabela):
    """Retorna apenas um Styler; mantém valores, tipos, índices e colunas.

    Percentuais já estão na escala 0–100. Não multiplica razões por 100,
    não converte códigos em números e não muda contagens na base exportada.
    """
    formatos = {}
    for coluna in tabela.columns:
        nome = str(coluna).lower()
        if is_bool_dtype(tabela[coluna]):
            continue
        if nome in COLUNAS_CONTAGEM or nome.endswith("_n") or nome.startswith(
            ("avaliados_", "pessoas ", "famílias ", "avaliações ")
        ):
            formatos[coluna] = contagem_br
        elif "(%)" in nome or "_pct" in nome or nome.startswith("pct_") or nome == "percentual_agregado":
            formatos[coluna] = percentual_br
        elif nome == "quantil":
            formatos[coluna] = quantil_br
        elif is_numeric_dtype(tabela[coluna]):
            formatos[coluna] = contagem_br if is_integer_dtype(tabela[coluna]) else numero_br
    visualizacao = tabela.style.format(formatos, na_rep="—", escape="html")
    # O corte combina índices (0–1) e percentuais (0–100) na mesma coluna.
    if {"indicador", "corte"}.issubset(tabela.columns):
        indices = tabela.index[tabela["indicador"].isin(["ivs", "idhm"])]
        percentuais = tabela.index[tabela["indicador"].isin(["cadinsan", "dai"])]
        if len(indices):
            visualizacao.format(numero_br, subset=(indices, ["corte"]), na_rep="—")
        if len(percentuais):
            visualizacao.format(percentual_br, subset=(percentuais, ["corte"]), na_rep="—")
    return visualizacao
