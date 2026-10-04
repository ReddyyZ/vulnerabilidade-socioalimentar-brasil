"""Análise municipal exploratória usada pelo notebook autocontido do Colab."""

from __future__ import annotations

import hashlib
import json
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd


DATA_FILES = {
    "ivs_idhm": "ivs_idhm/atlasivs_municipios_2010.csv",
    "cadunico": "cadunico/municipios-cadunico.json",
    "cadinsan": "cadinsan/CADINSAN_2025_dados_municipais.csv",
    "sisvan": "sisvan/indicadores_altura_peso_idade_menores_5_2025.csv",
}
GROUP_COLORS = {
    "Convergência dos três critérios": "#9e1b32",
    "IVS e CadInsan elevados, DAI abaixo do corte": "#e89c38",
    "DAI elevado sem convergência social-alimentar": "#377eb8",
    "Outras combinações": "#d7e4df",
    "Informação insuficiente": "#b9b9b9",
}
UF_REGIONS = {
    "11": ("RO", "Norte"), "12": ("AC", "Norte"),
    "13": ("AM", "Norte"), "14": ("RR", "Norte"),
    "15": ("PA", "Norte"), "16": ("AP", "Norte"),
    "17": ("TO", "Norte"), "21": ("MA", "Nordeste"),
    "22": ("PI", "Nordeste"), "23": ("CE", "Nordeste"),
    "24": ("RN", "Nordeste"), "25": ("PB", "Nordeste"),
    "26": ("PE", "Nordeste"), "27": ("AL", "Nordeste"),
    "28": ("SE", "Nordeste"), "29": ("BA", "Nordeste"),
    "31": ("MG", "Sudeste"), "32": ("ES", "Sudeste"),
    "33": ("RJ", "Sudeste"), "35": ("SP", "Sudeste"),
    "41": ("PR", "Sul"), "42": ("SC", "Sul"), "43": ("RS", "Sul"),
    "50": ("MS", "Centro-Oeste"), "51": ("MT", "Centro-Oeste"),
    "52": ("GO", "Centro-Oeste"), "53": ("DF", "Centro-Oeste"),
}


def verify_hashes(directory):
    directory = Path(directory)
    records = []
    for line in (directory / "SHA256SUMS").read_text().splitlines():
        if not line.strip():
            continue
        expected, relative = line.split(maxsplit=1)
        relative = relative.lstrip("*")
        path = directory / relative
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f"Integridade inválida: {relative}")
        records.append({"arquivo": relative, "sha256": actual, "integridade": "OK"})
    if {r["arquivo"] for r in records} != set(DATA_FILES.values()):
        raise ValueError("O manifesto deve identificar exatamente as quatro bases.")
    return pd.DataFrame(records)


def numeric(values, label):
    """Lê ponto/vírgula decimal e %, sem converter ausência em zero."""
    clean = values.astype("string").str.strip()
    clean = clean.str.replace("%", "", regex=False).str.replace(",", ".", regex=False)
    present = clean.notna() & clean.ne("")
    result = pd.to_numeric(clean.mask(~present), errors="coerce").astype(float)
    invalid = present & result.isna()
    if invalid.any():
        raise ValueError(f"Valores não numéricos em {label}: {values[invalid].head().tolist()}")
    if not np.isfinite(result.dropna()).all():
        raise ValueError(f"Valores infinitos em {label}")
    return result


def codes(values, length, source):
    result = values.astype("string").str.strip()
    if not result.str.fullmatch(rf"\d{{{length}}}").fillna(False).all():
        raise ValueError(f"{source}: códigos devem ter {length} dígitos.")
    if result.duplicated().any():
        raise ValueError(f"{source}: código municipal duplicado.")
    return result


def check_range(values, low, high, label):
    if not values.dropna().between(low, high).all():
        raise ValueError(f"{label}: valores fora de [{low}, {high}].")


def read_sources(directory):
    directory = Path(directory)
    hashes = verify_hashes(directory)
    sources = {}
    for key, relative in DATA_FILES.items():
        if key == "cadunico":
            def unique_keys(pairs):
                result = {}
                for code, value in pairs:
                    if code in result:
                        raise ValueError(f"CadÚnico: chave JSON duplicada: {code}")
                    result[code] = value
                return result
            data = json.loads((directory / relative).read_text(encoding="utf-8"),
                              object_pairs_hook=unique_keys)
            sources[key] = pd.DataFrame({"codigo_ibge_7": list(data),
                                         "cadunico_valor_original": list(data.values())})
        else:
            sources[key] = pd.read_csv(directory / relative, dtype="string",
                                      encoding="utf-8-sig", keep_default_na=False)
    return sources, hashes


def prepare_base(directory):
    """Normaliza cópias em memória e integra por prefixos únicos, com auditoria."""
    sources, hashes = read_sources(directory)
    tables = {}
    ivs = sources["ivs_idhm"]
    tables["ivs_idhm"] = pd.DataFrame({
        "codigo_ivs_original": codes(ivs["municipio"], 7, "IVS/IDHM"),
        "municipio_ivs": ivs["nome_municipio_uf"],
    })
    for column in ivs.columns:
        if column not in ("municipio", "nome_municipio_uf"):
            tables["ivs_idhm"][column] = numeric(ivs[column], column)
            check_range(tables["ivs_idhm"][column], 0, 1, column)

    cad = sources["cadunico"]
    tables["cadunico"] = pd.DataFrame({
        "codigo_cadunico_original": codes(cad["codigo_ibge_7"], 7, "CadÚnico"),
        "cadunico_valor_original": numeric(cad["cadunico_valor_original"], "CadÚnico"),
    })
    ci = sources["cadinsan"]
    tables["cadinsan"] = pd.DataFrame({
        "codigo_cadinsan_original": codes(ci["Cod_IBGE"], 7, "CadInsan"),
        "municipio_cadinsan": ci["Município"],
    })
    renames = {
        "Cadastros_Cadunico": "cadastros_cadunico_cadinsan",
        "Cadinsan_absoluto_com_PBF": "cadinsan_n_com_PBF",
        "Cadinsan_absoluto_sem_PBF": "cadinsan_n_sem_PBF",
        "Cadinsan_proporcional_com_PBF": "cadinsan_pct_com_PBF",
        "Cadinsan_proporcional_sem_PBF": "cadinsan_pct_sem_PBF",
    }
    for original, new in renames.items():
        tables["cadinsan"][new] = numeric(ci[original], original)
    sv = sources["sisvan"]
    if not sv["Ano"].eq("2025").all() or not sv["Faixa etária"].eq("0 a < 5 anos").all():
        raise ValueError("SISVAN fora do recorte previsto: 2025, menores de 5 anos.")
    if not sv["Fase da vida"].eq("CRIANÇA").all():
        raise ValueError("SISVAN contém outra fase da vida.")
    tables["sisvan"] = pd.DataFrame({
        "codigo_sisvan_original": codes(sv["Código IBGE"], 6, "SISVAN"),
        "municipio_sisvan": sv["Município"], "uf_sisvan": sv["UF"],
        "ano_sisvan": numeric(sv["Ano"], "Ano"),
    })
    counts = {
        "Altura Muito Baixa para a Idade - Quantidade": "altura_muito_baixa_n",
        "Altura Baixa para a Idade - Quantidade": "altura_baixa_n",
        "Altura Adequada para a Idade - Quantidade": "altura_adequada_n",
        "Total avaliado - Altura X Idade": "avaliados_altura",
        "Peso Muito Baixo para a Idade - Quantidade": "peso_muito_baixo_n",
        "Peso Baixo para a Idade - Quantidade": "peso_baixo_n",
        "Peso Adequado ou Eutrófico - Quantidade": "peso_adequado_n",
        "Peso Elevado para a Idade - Quantidade": "peso_elevado_n",
        "Total avaliado - Peso X Idade": "avaliados_peso",
        "Déficit de estatura - Quantidade": "dai_n_arquivo",
        "Déficit de peso para idade - Quantidade": "dpi_n_arquivo",
        "Déficit de estatura - %": "dai_pct_arquivo",
        "Déficit de peso para idade - %": "dpi_pct_arquivo",
    }
    for original, new in counts.items():
        tables["sisvan"][new] = numeric(sv[original], original)
    for source, table in tables.items():
        original = next(c for c in table if c.startswith("codigo_"))
        table["codigo_ibge_6"] = table[original].str[:6]
        if table["codigo_ibge_6"].duplicated().any():
            raise ValueError(f"{source}: prefixos municipais não são únicos.")
        table[f"tem_{source}"] = True

    # União externa: ausência de uma fonte não elimina o território das demais.
    base = tables["sisvan"]
    for source in ("ivs_idhm", "cadunico", "cadinsan"):
        base = base.merge(tables[source], on="codigo_ibge_6", how="outer",
                          validate="one_to_one")
    for source in tables:
        base[f"tem_{source}"] = base[f"tem_{source}"].fillna(False).astype(bool)
    original_7 = ["codigo_cadinsan_original", "codigo_ivs_original", "codigo_cadunico_original"]
    base["codigo_ibge_7"] = base[original_7].bfill(axis=1).iloc[:, 0]
    for column in original_7:
        conflict = base[column].notna() & base["codigo_ibge_7"].ne(base[column])
        if conflict.any():
            raise ValueError("Conflito entre códigos de sete dígitos das fontes.")
    # O código de 7 dígitos desconhecido permanece ausente; nunca inventar DV.
    base["municipio"] = base[["municipio_sisvan", "municipio_cadinsan", "municipio_ivs"]].bfill(axis=1).iloc[:, 0]
    base["uf"] = base["codigo_ibge_6"].str[:2].map(lambda c: UF_REGIONS[c][0])
    base["regiao"] = base["codigo_ibge_6"].str[:2].map(lambda c: UF_REGIONS[c][1])
    sv_rows = base["tem_sisvan"]
    if base.loc[sv_rows, "uf"].ne(base.loc[sv_rows, "uf_sisvan"]).any():
        raise ValueError("UF SISVAN incompatível com o prefixo municipal.")

    nonnegative = [c for c in base if c.endswith("_n") or c.startswith("avaliados_")]
    nonnegative += ["cadunico_valor_original", "cadastros_cadunico_cadinsan",
                    "cadinsan_n_com_PBF", "cadinsan_n_sem_PBF"]
    for column in nonnegative:
        values = base[column].dropna()
        if (values < 0).any() or not np.isclose(values % 1, 0).all():
            raise ValueError(f"{column}: contagem negativa ou não inteira.")
    for prefix, parts, total in (
        ("dai", ["altura_muito_baixa_n", "altura_baixa_n", "altura_adequada_n"], "avaliados_altura"),
        ("dpi", ["peso_muito_baixo_n", "peso_baixo_n", "peso_adequado_n", "peso_elevado_n"], "avaliados_peso"),
    ):
        component_total = base[parts].sum(axis=1, min_count=len(parts))
        if not np.allclose(component_total[sv_rows], base.loc[sv_rows, total], equal_nan=False):
            raise ValueError(f"Soma das categorias incompatível com {total}.")
        base[f"{prefix}_n"] = base[parts[:2]].sum(axis=1, min_count=2)
        if not np.allclose(base.loc[sv_rows, f"{prefix}_n"], base.loc[sv_rows, f"{prefix}_n_arquivo"]):
            raise ValueError(f"Numerador {prefix} incompatível com o CSV.")
        base[f"{prefix}_pct"] = base[f"{prefix}_n"].div(base[total].where(base[total] > 0)) * 100
        valid = base[total] > 0
        if not np.allclose(base.loc[valid, f"{prefix}_pct"],
                           base.loc[valid, f"{prefix}_pct_arquivo"], atol=0.011):
            raise ValueError(f"Percentual {prefix} incompatível com a fórmula.")
        check_range(base[f"{prefix}_pct"], 0, 100, prefix)
    for scenario in ("com_PBF", "sem_PBF"):
        check_range(base[f"cadinsan_pct_{scenario}"], 0, 100, "CadInsan")
        denominator = base["cadastros_cadunico_cadinsan"]
        absolute = base[f"cadinsan_n_{scenario}"]
        if (absolute > denominator).fillna(False).any():
            raise ValueError("CadInsan absoluto excede o total de cadastros informado.")
        calculated = absolute.div(denominator.where(denominator > 0)) * 100
        reported = base[f"cadinsan_pct_{scenario}"]
        complete = calculated.notna() & reported.notna()
        if not np.allclose(calculated[complete], reported[complete], atol=0.11):
            raise ValueError("Percentual CadInsan diverge da razão no arquivo.")
    audit = pd.DataFrame([
        {"fonte": source, "registros_origem": len(table),
         "municipios_na_uniao": len(base), "correspondencias_sisvan": int((base[f"tem_{source}"] & sv_rows).sum()),
         "sisvan_sem_fonte": int((sv_rows & ~base[f"tem_{source}"]).sum()),
         "fonte_sem_sisvan": int((~sv_rows & base[f"tem_{source}"]).sum())}
        for source, table in tables.items()
    ])
    base = base.sort_values("codigo_ibge_6").reset_index(drop=True)
    return base, audit, hashes


def classify(base, quantile=0.75, min_evaluated=100, scenario="com_PBF"):
    """Cortes nacionais por indicador; DAI usa apenas denominadores elegíveis."""
    if not 0 < quantile < 1 or not isinstance(min_evaluated, int) or min_evaluated < 1:
        raise ValueError("Quantil deve estar entre 0 e 1 e o mínimo deve ser inteiro positivo.")
    if scenario not in ("com_PBF", "sem_PBF"):
        raise ValueError("Cenário deve ser com_PBF ou sem_PBF.")
    result = base.copy()
    result["cadinsan_pct"] = result[f"cadinsan_pct_{scenario}"]
    result["cadinsan_n"] = result[f"cadinsan_n_{scenario}"]
    specs = [
        ("ivs", "ivs", True, pd.Series(True, index=result.index)),
        ("cadinsan", "cadinsan_pct", True, result["cadastros_cadunico_cadinsan"] > 0),
        ("dai", "dai_pct", True, result["avaliados_altura"] >= min_evaluated),
        ("idhm", "idhm", False, pd.Series(True, index=result.index)),
        ("dpi", "dpi_pct", True, result["avaliados_peso"] >= min_evaluated),
    ]
    thresholds = []
    for label, column, high, eligible in specs:
        valid = eligible & result[column].notna()
        if not valid.any():
            raise ValueError(f"Nenhum município elegível para {label}.")
        cutoff = result.loc[valid, column].quantile(quantile if high else 1 - quantile)
        flag = pd.Series(pd.NA, index=result.index, dtype="boolean")
        flag.loc[valid] = (result.loc[valid, column] >= cutoff if high
                           else result.loc[valid, column] <= cutoff)
        result[f"criterio_{label}"] = flag
        thresholds.append({"indicador": label, "corte": float(cutoff),
                           "operador": ">=" if high else "<=",
                           "municipios_referencia": int(valid.sum()),
                           "municipios_no_criterio": int(flag.fillna(False).sum()),
                           "percentil": quantile * 100 if high else (1 - quantile) * 100})
    primary = ["criterio_ivs", "criterio_cadinsan", "criterio_dai"]
    result["elegivel_principal"] = result[primary].notna().all(axis=1)
    result["prioritario"] = result[primary].all(axis=1).where(result["elegivel_principal"]).astype("boolean")
    result["numero_criterios_primarios"] = result[primary].sum(axis=1).where(result["elegivel_principal"]).astype("Int64")
    social = (result["criterio_ivs"] & result["criterio_cadinsan"]).fillna(False)
    height = result["criterio_dai"].fillna(False)
    eligible = result["elegivel_principal"]
    groups = list(GROUP_COLORS)
    result["perfil"] = groups[4]
    result.loc[eligible, "perfil"] = groups[3]
    result.loc[eligible & height & ~social, "perfil"] = groups[2]
    result.loc[eligible & social & ~height, "perfil"] = groups[1]
    result.loc[eligible & social & height, "perfil"] = groups[0]
    reasons = []
    for row in result.itertuples():
        missing = []
        if pd.isna(row.ivs): missing.append("IVS ausente")
        if pd.isna(row.cadinsan_pct) or not row.cadastros_cadunico_cadinsan > 0:
            missing.append("CadInsan ausente ou denominador inválido")
        if pd.isna(row.avaliados_altura) or row.avaliados_altura <= 0:
            missing.append("sem avaliações de altura")
        elif row.avaliados_altura < min_evaluated:
            missing.append(f"menos de {min_evaluated} avaliações de altura")
        elif pd.isna(row.dai_pct): missing.append("DAI ausente")
        reasons.append("; ".join(missing))
    result["motivo_nao_classificacao"] = reasons
    result["cenario_cadinsan"] = scenario
    result["quantil_classificacao"] = quantile
    result["minimo_avaliados"] = min_evaluated
    return result, pd.DataFrame(thresholds)


def sensitivity(base, reference, quantiles=(0.75, 0.80), minima=(30, 50, 100),
                scenarios=("com_PBF", "sem_PBF")):
    reference_set = set(reference.loc[reference["prioritario"].fillna(False), "codigo_ibge_6"])
    records, selections = [], []
    for scenario, quantile, minimum in product(scenarios, quantiles, minima):
        result, _ = classify(base, quantile, minimum, scenario)
        selected = set(result.loc[result["prioritario"].fillna(False), "codigo_ibge_6"])
        union = reference_set | selected
        records.append({"cenario": scenario, "quantil": quantile, "minimo_avaliados": minimum,
                        "elegiveis": int(result["elegivel_principal"].sum()),
                        "prioritarios": len(selected), "coincidentes_principal": len(reference_set & selected),
                        "jaccard_principal": len(reference_set & selected) / len(union) if union else 1.0})
        selections.append(pd.DataFrame({"codigo_ibge_6": result["codigo_ibge_6"],
                                        "elegivel": result["elegivel_principal"],
                                        "selecionado": result["prioritario"].fillna(False).astype(int)}))
    all_selections = pd.concat(selections, ignore_index=True)
    stability = all_selections.groupby("codigo_ibge_6").agg(
        cenarios_elegiveis=("elegivel", "sum"), cenarios_selecionado=("selecionado", "sum"))
    stability["cenarios_testados"] = len(records)
    stability["fracao_cenarios_selecionado"] = stability["cenarios_selecionado"] / len(records)
    return pd.DataFrame(records), stability.reset_index()


def regional_summary(result):
    records = []
    for region, table in result.groupby("regiao", sort=True):
        record = {"regiao": region, "municipios": len(table),
                  "elegiveis": int(table["elegivel_principal"].sum()),
                  "prioritarios": int(table["prioritario"].fillna(False).sum())}
        record["pct_prioritarios_entre_elegiveis"] = (
            record["prioritarios"] / record["elegiveis"] * 100 if record["elegiveis"] else np.nan)
        for label, total in (("dai", "avaliados_altura"), ("dpi", "avaliados_peso")):
            valid = table[total].gt(0) & table[f"{label}_n"].notna()
            denominator = table.loc[valid, total].sum()
            record[f"{label}_n"] = table.loc[valid, f"{label}_n"].sum()
            record[total] = denominator
            record[f"{label}_pct_agregado"] = (
                record[f"{label}_n"] / denominator * 100 if denominator else np.nan)
        records.append(record)
    return pd.DataFrame(records)


def dictionary():
    rows = [
        ("codigo_ibge_6", "Chave analítica por prefixo único", "texto", "Fontes; origem preservada", "Não implica harmonização histórica completa"),
        ("codigo_ibge_7", "Código informado nas fontes sociais", "texto", "IVS/CadÚnico/CadInsan", "Ausente quando nenhuma fonte social fornece o código"),
        ("ivs", "Índice de Vulnerabilidade Social", "0–1", "IVS, 2010", "Maior: maior vulnerabilidade"),
        ("idhm", "Índice de Desenvolvimento Humano Municipal", "0–1", "IDHM, 2010", "Menor: menor desenvolvimento; contextual"),
        ("cadunico_valor_original", "Valor municipal do JSON", "não confirmada", "CadÚnico, período não informado", "Unidade e período pendentes; não integra a regra"),
        ("cadastros_cadunico_cadinsan", "Cadastros_Cadunico no CSV", "conforme arquivo", "CADINSAN_2025", "Não equivale automaticamente ao JSON"),
        ("cadinsan_pct", "Percentual do cenário selecionado", "%", "CADINSAN_2025", "com_PBF/sem_PBF são cenários; documentação local pendente"),
        ("cadinsan_n", "Quantidade do cenário selecionado", "conforme arquivo", "CADINSAN_2025", "Dimensão absoluta; não soma com SISVAN"),
        ("dai_n", "Altura muito baixa + altura baixa", "registros avaliados", "SISVAN, 2025", "Numerador recalculado"),
        ("dai_pct", "100 × dai_n / avaliados_altura", "%", "SISVAN, 2025", "Sem arredondamento; denominador zero gera NaN"),
        ("dpi_n", "Peso muito baixo + peso baixo", "registros avaliados", "SISVAN, 2025", "Indicador complementar"),
        ("dpi_pct", "100 × dpi_n / avaliados_peso", "%", "SISVAN, 2025", "Não somar com DAI"),
        ("avaliados_altura", "Total avaliado em Altura X Idade", "registros avaliados", "SISVAN, 2025", "Não é medida de cobertura populacional"),
        ("avaliados_peso", "Total avaliado em Peso X Idade", "registros avaliados", "SISVAN, 2025", "Denominador específico de DPI"),
        ("criterio_*", "Flag relativa ao corte nacional", "booleano anulável", "Análise derivada", "Ausente quando indicador não é elegível"),
        ("prioritario", "Coincidência de IVS, CadInsan e DAI elevados", "booleano anulável", "Análise derivada", "Ausente para informação insuficiente"),
        ("perfil", "Grupo exploratório de sobreposição", "categoria", "Análise derivada", "Não é classificação oficial"),
        ("fracao_cenarios_selecionado", "Fração das especificações que selecionam o município", "0–1", "Sensibilidade", "Não é probabilidade ou intervalo de confiança"),
    ]
    return pd.DataFrame(rows, columns=["variavel", "definicao", "unidade", "fonte_periodo", "observacao"])


def figure_style():
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False,
                         "axes.spines.right": False, "figure.dpi": 110,
                         "savefig.dpi": 180})


def save_figure(fig, output, name):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    fig.savefig(output / f"{name}.png", bbox_inches="tight")
    fig.savefig(output / f"{name}.svg", bbox_inches="tight")


def distribution_figure(result, output):
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 3, figsize=(14, 7))
    columns = [("ivs", "IVS — 2010"), ("idhm", "IDHM — 2010"),
               ("cadinsan_pct", "CadInsan (%) — cenário selecionado"),
               ("dai_pct", "DAI (%) — todos com avaliações"),
               ("dpi_pct", "DPI (%) — todos com avaliações"),
               ("avaliados_altura", "Avaliações de altura — escala log")]
    for ax, (column, title) in zip(axes.flat, columns):
        values = result[column].dropna()
        if column == "avaliados_altura":
            values = np.log10(values[values > 0])
            ax.set_xlabel("log10(total avaliado)")
        ax.hist(values, bins=35, color="#327c81", edgecolor="white", linewidth=0.4)
        ax.set_title(title)
        ax.set_ylabel("Municípios")
    fig.tight_layout()
    save_figure(fig, output, "01_distribuicoes")
    return fig


def association_figure(result, thresholds, output):
    import matplotlib.pyplot as plt
    cuts = thresholds.set_index("indicador")["corte"]
    valid = result[result["elegivel_principal"]]
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    chosen = valid["prioritario"].fillna(False).to_numpy(dtype=bool)
    for ax, (column, label, criterion) in zip(axes, [
        ("ivs", "IVS (2010)", "ivs"), ("idhm", "IDHM (2010)", "idhm"),
        ("cadinsan_pct", "CadInsan (%)", "cadinsan")]):
        ax.scatter(valid[column], valid["dai_pct"], s=8, alpha=0.25, color="#327c81")
        ax.scatter(valid.loc[chosen, column], valid.loc[chosen, "dai_pct"],
                   s=13, alpha=0.7, color=GROUP_COLORS[list(GROUP_COLORS)[0]])
        ax.axhline(cuts["dai"], color="#777777", linestyle="--", linewidth=1)
        ax.axvline(cuts[criterion], color="#777777", linestyle="--", linewidth=1)
        ax.set(xlabel=label, ylabel="DAI (%)", title=f"{label} × DAI")
    fig.suptitle("Municípios elegíveis; vermelho = convergência dos três critérios")
    fig.tight_layout()
    save_figure(fig, output, "02_associacoes")
    return fig


def correlation_figure(result, output, minimum=100):
    import matplotlib.pyplot as plt
    cols = ["ivs", "idhm", "cadinsan_pct", "dai_pct", "dpi_pct"]
    data = result[cols].copy()
    data.loc[result["avaliados_altura"] < minimum, "dai_pct"] = np.nan
    data.loc[result["avaliados_peso"] < minimum, "dpi_pct"] = np.nan
    corr = data.corr(method="spearman", min_periods=3)
    pair_counts = data.notna().astype(int).T @ data.notna().astype(int)
    fig, ax = plt.subplots(figsize=(7, 6))
    im = ax.imshow(corr, vmin=-1, vmax=1, cmap="RdBu_r")
    ax.set_xticks(range(len(cols)), ["IVS", "IDHM", "CadInsan", "DAI", "DPI"])
    ax.set_yticks(range(len(cols)), ["IVS", "IDHM", "CadInsan", "DAI", "DPI"])
    for i in range(len(cols)):
        for j in range(len(cols)):
            ax.text(j, i, f"{corr.iloc[i, j]:.2f}\nn={pair_counts.iloc[i, j]}",
                    ha="center", va="center", fontsize=9,
                    color="white" if abs(corr.iloc[i, j]) > 0.65 else "black")
    ax.set_title("Correlação de Spearman; pares disponíveis por comparação")
    fig.colorbar(im, ax=ax, shrink=0.8)
    fig.tight_layout()
    save_figure(fig, output, "03_correlacoes")
    return fig, corr, pair_counts


def sensitivity_figure(table, output):
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(11, 4.5))
    labels = [f"{r.cenario}\nP{r.quantil * 100:.0f} / n≥{r.minimo_avaliados}" for r in table.itertuples()]
    ax.bar(range(len(table)), table["prioritarios"], color="#327c81")
    ax.set_xticks(range(len(table)), labels, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("Municípios selecionados")
    ax.set_title("Sensibilidade da seleção aos cortes, denominadores e cenários")
    fig.tight_layout()
    save_figure(fig, output, "04_sensibilidade")
    return fig


def geometry_audit(geojson, base):
    features = geojson["features"]
    codes_7 = pd.Series([str(f["properties"]["codarea"]) for f in features], dtype="string")
    codes(codes_7, 7, "Malha IBGE")
    prefixes = codes_7.str[:6]
    if prefixes.duplicated().any():
        raise ValueError("Malha com prefixos municipais duplicados.")
    existing = dict(zip(prefixes, codes_7))
    known = base["codigo_ibge_7"].notna()
    for row in base.loc[known].itertuples():
        if row.codigo_ibge_6 in existing and existing[row.codigo_ibge_6] != row.codigo_ibge_7:
            raise ValueError("Conflito de código municipal entre malha e bases sociais.")
    return pd.DataFrame({"codigo_ibge_6": base["codigo_ibge_6"],
                         "codigo_ibge_7_malha": base["codigo_ibge_6"].map(existing),
                         "tem_geometria": base["codigo_ibge_6"].isin(existing)})


def map_figure(geojson, result, column, title, output, filename, categories=None):
    """Mapa ilustrativo em coordenadas geográficas; anéis interiores preservados."""
    import matplotlib.pyplot as plt
    from matplotlib.collections import PatchCollection
    from matplotlib.colors import Normalize
    from matplotlib.path import Path as MplPath
    from matplotlib.patches import Patch, PathPatch
    lookup = result.set_index("codigo_ibge_6")[column].to_dict()
    patches, values, colors = [], [], []
    for feature in geojson["features"]:
        geometry = feature["geometry"]
        polygons = ([geometry["coordinates"]] if geometry["type"] == "Polygon"
                    else geometry["coordinates"])
        value = lookup.get(str(feature["properties"]["codarea"])[:6], np.nan)
        for polygon in polygons:
            vertices, commands = [], []
            for ring in polygon:
                coordinates = np.asarray(ring, dtype=float)[:, :2]
                if len(coordinates) < 4:
                    continue
                vertices.extend(coordinates)
                commands.extend([MplPath.MOVETO] + [MplPath.LINETO] * (len(coordinates) - 2) + [MplPath.CLOSEPOLY])
            if vertices:
                patches.append(PathPatch(MplPath(vertices, commands)))
                if categories is not None:
                    colors.append(categories.get(value, "#b9b9b9"))
                else:
                    values.append(float(value) if pd.notna(value) else np.nan)
    fig, ax = plt.subplots(figsize=(9, 9))
    collection = PatchCollection(patches, linewidths=0.08, edgecolors="#ffffff")
    if categories is not None:
        collection.set_facecolors(colors)
        ax.legend(handles=[Patch(facecolor=color, label=label) for label, color in categories.items()],
                  loc="lower left", fontsize=8, frameon=False)
    else:
        arr = np.ma.masked_invalid(values)
        collection.set_array(arr)
        cmap = plt.get_cmap("YlOrRd").copy()
        cmap.set_bad("#b9b9b9")
        collection.set_cmap(cmap)
        finite = np.asarray(values)[np.isfinite(values)]
        if finite.size:
            collection.set_norm(Normalize(vmin=float(finite.min()), vmax=float(finite.max())))
        fig.colorbar(collection, ax=ax, fraction=0.035, pad=0.015)
        ax.legend(handles=[Patch(facecolor="#b9b9b9", label="Ausente / não elegível")],
                  loc="lower left", frameon=False)
    ax.add_collection(collection)
    ax.set(xlim=(-74.5, -32), ylim=(-34.5, 6), title=title)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.text(0.15, 0.075, "IBGE: malha simplificada de apoio; coordenadas geográficas.\n"
             "Mapa ilustrativo; não mede cobertura ou concentração espacial estatística.", fontsize=8)
    save_figure(fig, output, filename)
    return fig
