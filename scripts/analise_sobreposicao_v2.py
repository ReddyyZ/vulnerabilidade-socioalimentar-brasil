"""Três dimensões municipais; mantém leitores e cartografia da primeira versão."""

from __future__ import annotations

import hashlib
import json
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd

from scripts.analise_sobreposicao import (
    UF_REGIONS, numeric, codes, check_range, interpret_sisvan_counts,
    figure_style, save_figure, geometry_audit, map_figure,
)

DATA_FILES = {
    "ivs_idhm": "ivs_idhm/atlasivs_municipios_2010.csv",
    "cadinsan": "cadinsan/CADINSAN_2025_dados_municipais.csv",
    "sisvan_altura": "sisvan/sisvan_municipios_altura_por_idade_0_a_menor_5_anos_2025.csv",
    "sisvan_peso": "sisvan/sisvan_municipios_peso_por_idade_0_a_menor_5_anos_2025.csv",
}
CATALOGUE_DATASETS = {"ivs_idhm": "municipios_ivs", "cadinsan": "municipios_cadinsan"}
FIXED_CUTS = {"ivs": (0.401, ">="), "idhm": (0.600, "<")}
DIMENSIONS = ["dim_social", "dim_alimentar", "dim_nutricional"]
PRIORITY_LABELS = {
    0: "Sem sinais pelos critérios adotados",
    1: "Atenção — uma dimensão",
    2: "Prioridade alta — duas dimensões",
    3: "Prioridade muito alta — três dimensões",
}
OMS_LABELS = ["muito baixa", "baixa", "média", "alta", "muito alta"]
OMS_COLORS = dict(zip(OMS_LABELS, ["#eff3ff", "#bdd7e7", "#fdcc8a", "#fc8d59", "#b30000"]))
OMS_COLORS["dados insuficientes"] = "#b9b9b9"
DIMENSION_COLORS = {"0": "#e0eee7", "1": "#fdd49e", "2": "#fc8d59",
                    "3": "#9e1b32", "dados insuficientes": "#b9b9b9"}


def verify_hashes(directory):
    directory = Path(directory)
    records = []
    for line in (directory / "SHA256SUMS").read_text().splitlines():
        if not line.strip():
            continue
        expected, relative = line.split(maxsplit=1)
        relative = relative.lstrip("*")
        actual = hashlib.sha256((directory / relative).read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f"Integridade inválida: {relative}")
        records.append({"arquivo": relative, "sha256": actual, "integridade": "OK"})
    if len(records) != len(DATA_FILES) or {r["arquivo"] for r in records} != set(DATA_FILES.values()):
        raise ValueError("O manifesto deve identificar exatamente as quatro entradas da v2.")
    return pd.DataFrame(records)


def validate_catalogue(catalogue_path, directory):
    raw = Path(catalogue_path).read_bytes()
    catalogue = json.loads(raw.decode("utf-8-sig"))
    records = []
    for source, dataset_id in CATALOGUE_DATASETS.items():
        dataset = catalogue["datasets"][dataset_id]
        relative = DATA_FILES[source]
        actual = hashlib.sha256((Path(directory) / relative).read_bytes()).hexdigest()
        if actual != dataset["stats"]["checkSum"].removeprefix("sha256:"):
            raise ValueError(f"Catálogo não corresponde a {relative}")
        temporal = dataset["temporal"]["extent"][0]
        records.append({"dataset_id": dataset_id, "arquivo": relative, "titulo": dataset["title"],
                        "inicio_referencia_catalogo": temporal[0], "fim_referencia_catalogo": temporal[1],
                        "fonte_original": dataset["source"]["url"], "sha256": actual,
                        "corresponde_ao_catalogo": True})
    return pd.DataFrame(records), {"catalogo_sha256": hashlib.sha256(raw).hexdigest(),
                                   "catalogo_id": catalogue["catalog"]["id"],
                                   "fontes": records, "recorte": "Somente fontes sociais usadas na v2"}


def sisvan_metadata(directory, source):
    path = Path(directory) / DATA_FILES[source]
    metadata = json.loads(path.with_suffix(".metadados.json").read_text())
    index = "altura_por_idade" if source == "sisvan_altura" else "peso_por_idade"
    expected = {"ano": 2025, "fase": "crianca", "indice": index,
                "faixa_etaria": "0_a_menor_5_anos", "nu_idade_inicio": "0", "nu_idade_fim": "5"}
    if any(metadata.get(key) != value for key, value in expected.items()):
        raise ValueError(f"{source}: recorte incompatível com menores de cinco anos, 2025")
    if metadata.get("indicadores_derivados", []) != []:
        raise ValueError("A entrada nutricional não deve conter DAI ou DPI pré-calculado")
    if "sha256_csv" in metadata and metadata["sha256_csv"] != hashlib.sha256(path.read_bytes()).hexdigest():
        raise ValueError(f"{source}: hash incompatível com os metadados")
    if set(metadata["ufs"]) != {uf for uf, _ in UF_REGIONS.values()}:
        raise ValueError(f"{source}: coleta nacional incompleta")
    return metadata


def read_nutrition(directory, source):
    metadata = sisvan_metadata(directory, source)
    raw = pd.read_csv(Path(directory) / DATA_FILES[source], dtype="string",
                      encoding="utf-8-sig", keep_default_na=False)
    if list(raw.columns) != metadata["colunas"] or len(raw) != metadata["linhas"]:
        raise ValueError(f"{source}: esquema ou linhas incompatíveis com os metadados")
    height = source == "sisvan_altura"
    parts = (["Altura Muito Baixa para a Idade", "Altura Baixa para a Idade",
              "Altura Adequada para a Idade"] if height else
             ["Peso Muito Baixo para a Idade", "Peso Baixo para a Idade",
              "Peso Adequado ou Eutrófico", "Peso Elevado para a Idade"])
    names = (["altura_muito_baixa_n", "altura_baixa_n", "altura_adequada_n"] if height else
             ["peso_muito_baixo_n", "peso_baixo_n", "peso_adequado_n", "peso_elevado_n"])
    total = "avaliados_altura" if height else "avaliados_peso"
    count_columns = [p + " - Quantidade" for p in parts] + ["Total"]
    pct_columns = [p + " - %" for p in parts]
    interpreted = [interpret_sisvan_counts([row[c] for c in count_columns],
                    [row[c] for c in pct_columns], row["Código IBGE"]) for _, row in raw.iterrows()]
    table = pd.DataFrame({f"codigo_{source}_original": codes(raw["Código IBGE"], 6, source),
                          f"municipio_{source}": raw["Município"], f"uf_{source}": raw["UF"],
                          f"ano_{source}": metadata["ano"]})
    for i, name in enumerate(names + [total]):
        table[name] = [v[0][i] for v in interpreted]
        table[name + "_valor_fonte"] = raw[count_columns[i]]
    for column, name in zip(pct_columns, names):
        table[name + "_percentual_fonte"] = raw[column]
    table[f"{source}_escala_alterada"] = [v[1] for v in interpreted]
    table[f"{source}_escalas_compativeis"] = [v[2] for v in interpreted]
    if not table[names].sum(axis=1).eq(table[total]).all():
        raise ValueError(f"{source}: soma das categorias difere do total")
    indicator = "dai" if height else "dpi"
    table[indicator + "_n"] = table[names[:2]].sum(axis=1, min_count=2)
    table[indicator + "_pct"] = table[indicator + "_n"].div(table[total].where(table[total] > 0)) * 100
    check_range(table[indicator + "_pct"], 0, 100, indicator)
    return table


def prepare_base(directory):
    directory = Path(directory)
    hashes = verify_hashes(directory)
    ivs = pd.read_csv(directory / DATA_FILES["ivs_idhm"], dtype="string", keep_default_na=False)
    tables = {"ivs_idhm": pd.DataFrame({"codigo_ivs_original": codes(ivs["municipio"], 7, "IVS/IDHM"),
                                        "municipio_ivs": ivs["nome_municipio_uf"]})}
    for column in ivs.columns:
        if column not in ("municipio", "nome_municipio_uf"):
            tables["ivs_idhm"][column] = numeric(ivs[column], column)
            check_range(tables["ivs_idhm"][column], 0, 1, column)
    ci = pd.read_csv(directory / DATA_FILES["cadinsan"], dtype="string", keep_default_na=False)
    tables["cadinsan"] = pd.DataFrame({"codigo_cadinsan_original": codes(ci["Cod_IBGE"], 7, "CadInsan"),
                                      "municipio_cadinsan": ci["Município"]})
    # Este campo pertence ao próprio CSV CadInsan: é seu denominador de famílias.
    tables["cadinsan"]["familias_cadinsan"] = numeric(ci["Cadastros_Cadunico"], "famílias CadInsan")
    for scenario in ("com_PBF", "sem_PBF"):
        for original, name in [(f"Cadinsan_absoluto_{scenario}", f"cadinsan_n_{scenario}"),
                               (f"Cadinsan_proporcional_{scenario}", f"cadinsan_pct_{scenario}_arquivo")]:
            tables["cadinsan"][name] = numeric(ci[original], original)
    for source in ("sisvan_altura", "sisvan_peso"):
        tables[source] = read_nutrition(directory, source)
    for source, table in tables.items():
        original = next(c for c in table if c.startswith("codigo_"))
        table["codigo_ibge_6"] = table[original].str[:6]
        if table["codigo_ibge_6"].duplicated().any():
            raise ValueError(f"{source}: prefixos municipais duplicados")
        table[f"tem_{source}"] = True
    base = tables["sisvan_altura"]
    for source in ("sisvan_peso", "ivs_idhm", "cadinsan"):
        base = base.merge(tables[source], on="codigo_ibge_6", how="outer", validate="one_to_one")
    for source in tables:
        base[f"tem_{source}"] = base[f"tem_{source}"].fillna(False).astype(bool)
    original_7 = ["codigo_cadinsan_original", "codigo_ivs_original"]
    base["codigo_ibge_7"] = base[original_7].bfill(axis=1).iloc[:, 0]
    for column in original_7:
        if (base[column].notna() & base["codigo_ibge_7"].ne(base[column])).any():
            raise ValueError("Conflito entre códigos das fontes sociais")
    # Na ausência de código de sete dígitos, o prefixo original é explicitamente mantido.
    base["codigo_ibge"] = base["codigo_ibge_7"].fillna(base["codigo_ibge_6"])
    base["municipio"] = base[["municipio_sisvan_altura", "municipio_sisvan_peso",
                              "municipio_cadinsan", "municipio_ivs"]].bfill(axis=1).iloc[:, 0]
    base["uf"] = base["codigo_ibge_6"].str[:2].map(lambda c: UF_REGIONS[c][0])
    base["regiao"] = base["codigo_ibge_6"].str[:2].map(lambda c: UF_REGIONS[c][1])
    for source in ("sisvan_altura", "sisvan_peso"):
        present = base[f"tem_{source}"]
        if base.loc[present, "uf"].ne(base.loc[present, f"uf_{source}"]).any():
            raise ValueError(f"{source}: UF incompatível com código municipal")
    counts = [c for c in base if c.endswith("_n") or c.startswith("avaliados_") and not c.endswith("_fonte")]
    counts += ["familias_cadinsan", "cadinsan_n_com_PBF", "cadinsan_n_sem_PBF"]
    for column in counts:
        values = base[column].dropna()
        if (values < 0).any() or not np.isclose(values % 1, 0).all():
            raise ValueError(f"{column}: contagem negativa ou não inteira")
    for scenario in ("com_PBF", "sem_PBF"):
        absolute, denominator = base[f"cadinsan_n_{scenario}"], base["familias_cadinsan"]
        if (absolute > denominator).fillna(False).any():
            raise ValueError("CadInsan absoluto excede denominador")
        calculated = absolute.div(denominator.where(denominator > 0)) * 100
        reported = base[f"cadinsan_pct_{scenario}_arquivo"]
        check_range(reported, 0, 100, "CadInsan na fonte")
        complete = calculated.notna() & reported.notna()
        if not np.allclose(calculated[complete], reported[complete], atol=0.11):
            raise ValueError("Percentual CadInsan diverge da razão no arquivo")
        base[f"cadinsan_pct_{scenario}"] = calculated
        base[f"cadinsan_diferenca_pp_{scenario}"] = calculated - reported
        check_range(calculated, 0, 100, "CadInsan recalculado")
    base["cadinsan_referencia"] = "2025-01"
    height = base["tem_sisvan_altura"]
    audit = pd.DataFrame([{"fonte": source, "registros_origem": len(table),
                          "municipios_na_uniao": len(base),
                          "correspondencias_sisvan": int((base[f"tem_{source}"] & height).sum()),
                          "sisvan_sem_fonte": int((height & ~base[f"tem_{source}"]).sum()),
                          "fonte_sem_sisvan": int((~height & base[f"tem_{source}"]).sum())}
                         for source, table in tables.items()])
    return base.sort_values("codigo_ibge_6").reset_index(drop=True), audit, hashes


def nullable_flag(values, valid, cutoff, operator=">="):
    flag = pd.Series(pd.NA, index=values.index, dtype="boolean")
    comparison = values.ge(cutoff) if operator == ">=" else values.lt(cutoff)
    flag.loc[valid] = comparison.loc[valid]
    return flag


def classify(base, quantile=0.75, min_evaluated=20, scenario="com_PBF", dai_cutoff=6.7, dpi_cutoff=1.8):
    if not 0 < quantile < 1 or not isinstance(min_evaluated, int) or min_evaluated < 1:
        raise ValueError("Quantil deve estar entre 0 e 1; mínimo deve ser inteiro positivo")
    if scenario not in ("com_PBF", "sem_PBF"):
        raise ValueError("Cenário inválido")
    if not np.isfinite(dpi_cutoff) or not 0 <= dpi_cutoff <= 100:
        raise ValueError("Corte DPI deve ser percentual entre 0 e 100")
    result = base.copy()
    result["cadinsan_pct"] = result[f"cadinsan_pct_{scenario}"]
    result["cadinsan_pct_arquivo"] = result[f"cadinsan_pct_{scenario}_arquivo"]
    result["cadinsan_n"] = result[f"cadinsan_n_{scenario}"]
    valid_ci = result["cadinsan_pct"].notna() & result["familias_cadinsan"].gt(0)
    valid_height = result["dai_pct"].notna() & result["avaliados_altura"].ge(min_evaluated)
    valid_weight = result["dpi_pct"].notna() & result["avaliados_peso"].ge(min_evaluated)
    if not valid_ci.any():
        raise ValueError("Nenhum município válido para quantil CadInsan")
    ci_cut = result.loc[valid_ci, "cadinsan_pct"].quantile(quantile)
    if dai_cutoff == "P75":
        if not valid_height.any():
            raise ValueError("Nenhum município válido para quantil DAI")
        height_cut = result.loc[valid_height, "dai_pct"].quantile(0.75)
        dai_method = "quantil exploratório"
    else:
        height_cut, dai_method = float(dai_cutoff), "referência Mapa InSAN" if float(dai_cutoff) == 6.7 else "referência OMS"
        if not np.isfinite(height_cut) or not 0 <= height_cut <= 100:
            raise ValueError("Corte DAI deve ser percentual entre 0 e 100")
    specs = [("ivs", "ivs", result["ivs"].notna(), 0.401, ">=", "faixa IVS/Ipea"),
             ("idhm", "idhm", result["idhm"].notna(), 0.600, "<", "baixo desenvolvimento adotado"),
             ("cadinsan", "cadinsan_pct", valid_ci, ci_cut, ">=", "quantil exploratório"),
             ("dai", "dai_pct", valid_height, height_cut, ">=", dai_method),
             ("dpi", "dpi_pct", valid_weight, dpi_cutoff, ">=", "referência Mapa InSAN complementar")]
    cuts = []
    for label, column, valid, cutoff, operator, method in specs:
        result[f"criterio_{label}"] = nullable_flag(result[column], valid, cutoff, operator)
        cuts.append({"indicador": label, "corte": float(cutoff), "operador": operator,
                     "metodo": method, "municipios_referencia": int(valid.sum()),
                     "municipios_no_criterio": int(result[f"criterio_{label}"].sum()),
                     "percentil": quantile * 100 if label == "cadinsan" else 75 if label == "dai" and dai_cutoff == "P75" else None})
    # Mesmo com um critério conhecido desfavorável, falta de outro impede a dimensão social.
    valid_social = result[["criterio_ivs", "criterio_idhm"]].notna().all(axis=1)
    result["dim_social"] = (result["criterio_ivs"] & result["criterio_idhm"]).where(valid_social)
    result["dim_alimentar"] = result["criterio_cadinsan"]
    result["dim_nutricional"] = result["criterio_dai"]
    result["social_alta"] = result["dim_social"]
    result["cadinsan_alto"] = result["dim_alimentar"]
    result["nutricional_alta"] = result["dim_nutricional"]
    result["social_status"] = "dados insuficientes"
    for ivs_flag, idhm_flag, label in [(True, True, "ambos desfavoráveis"),
                                     (True, False, "apenas IVS desfavorável"),
                                     (False, True, "apenas IDHM desfavorável"),
                                     (False, False, "nenhum desfavorável")]:
        mask = valid_social & result["criterio_ivs"].eq(ivs_flag) & result["criterio_idhm"].eq(idhm_flag)
        result.loc[mask.fillna(False), "social_status"] = label
    result["elegivel_principal"] = result[DIMENSIONS].notna().all(axis=1)
    result["n_dimensoes_desfavoraveis"] = result[DIMENSIONS].sum(axis=1).where(result["elegivel_principal"]).astype("Int64")
    result["convergencia_total"] = result["n_dimensoes_desfavoraveis"].eq(3).astype("boolean")
    result["prioridade_maxima"] = result["convergencia_total"]
    result["classe_prioridade"] = result["n_dimensoes_desfavoraveis"].map(PRIORITY_LABELS).fillna("dados insuficientes")
    result["dai_categoria_oms"] = pd.cut(result["dai_pct"].where(valid_height),
        [-np.inf, 2.5, 10, 20, 30, np.inf], labels=OMS_LABELS, right=False).astype("string").fillna("dados insuficientes")
    both_valid = valid_height & valid_weight
    result["nutricional_mapa_insan"] = (nullable_flag(result["dai_pct"], valid_height, 6.7)
                                          & result["criterio_dpi"]).where(both_valid)
    result["convergencia_total_dai_dpi"] = (result["dim_social"] & result["dim_alimentar"]
                                             & result["nutricional_mapa_insan"]).where(valid_social & valid_ci & both_valid)
    result["dpi_status"] = result["criterio_dpi"].map({True: "DPI ≥ referência", False: "DPI abaixo da referência"}).fillna("dados insuficientes")
    reasons = []
    for row in result.itertuples():
        missing = []
        if pd.isna(row.ivs): missing.append("IVS ausente")
        if pd.isna(row.idhm): missing.append("IDHM ausente")
        if pd.isna(row.cadinsan_pct) or not row.familias_cadinsan > 0:
            missing.append("CadInsan ausente ou denominador inválido")
        if pd.isna(row.dai_pct): missing.append("DAI ausente ou sem avaliações")
        elif row.avaliados_altura < min_evaluated: missing.append(f"menos de {min_evaluated} avaliações de altura")
        reasons.append("; ".join(missing))
    result["motivo_nao_classificacao"] = reasons
    result["cenario_cadinsan"] = scenario
    result["quantil_cadinsan"] = quantile
    result["minimo_avaliados"] = min_evaluated
    return result, pd.DataFrame(cuts)


def compare_rounding(base, reference, quantile=0.75, min_evaluated=20, scenario="com_PBF", dai_cutoff=6.7):
    rounded = base.copy()
    for option in ("com_PBF", "sem_PBF"):
        rounded[f"cadinsan_pct_{option}"] = rounded[f"cadinsan_pct_{option}_arquivo"]
    previous, cuts = classify(rounded, quantile, min_evaluated, scenario, dai_cutoff)
    comparison = reference[["codigo_ibge_6", "municipio", "uf", "cadinsan_pct", "cadinsan_pct_arquivo"]].copy()
    comparison["selecionado_percentual_csv"] = previous["convergencia_total"]
    comparison["selecionado_sem_arredondamento"] = reference["convergencia_total"]
    comparison["mudou_selecao"] = comparison["selecionado_percentual_csv"].fillna(False).ne(comparison["selecionado_sem_arredondamento"].fillna(False))
    return comparison, cuts


def sensitivity(base, reference, quantiles=(0.70, 0.75, 0.80, 0.90), minima=(20, 50, 100),
                scenarios=("com_PBF", "sem_PBF"), dai_cuts=(6.7, 10.0, "P75")):
    ref = set(reference.loc[reference["convergencia_total"].fillna(False), "codigo_ibge_6"])
    records, selections = [], []
    for scenario, quantile, minimum, dai_cut in product(scenarios, quantiles, minima, dai_cuts):
        result, cuts = classify(base, quantile, minimum, scenario, dai_cut)
        selected = set(result.loc[result["convergencia_total"].fillna(False), "codigo_ibge_6"])
        union = ref | selected
        records.append({"cenario": scenario, "quantil": quantile, "minimo_avaliados": minimum,
                        "referencia_dai": str(dai_cut), "corte_dai_pct": float(cuts.set_index("indicador").loc["dai", "corte"]),
                        "corte_cadinsan_pct": float(cuts.set_index("indicador").loc["cadinsan", "corte"]),
                        "elegiveis": int(result["elegivel_principal"].sum()),
                        "municipios_dim_alimentar": int(result["dim_alimentar"].sum()),
                        "municipios_dim_nutricional": int(result["dim_nutricional"].sum()),
                        "convergencia_total": len(selected), "entram_vs_principal": len(selected - ref),
                        "saem_vs_principal": len(ref - selected), "coincidentes_principal": len(ref & selected),
                        "jaccard_principal": len(ref & selected) / len(union) if union else 1.0})
        selections.append(pd.DataFrame({"codigo_ibge_6": result["codigo_ibge_6"],
                                         "elegivel": result["elegivel_principal"],
                                         "selecionado": result["convergencia_total"].fillna(False).astype(int)}))
    stability = pd.concat(selections).groupby("codigo_ibge_6").agg(
        cenarios_elegiveis=("elegivel", "sum"), cenarios_selecionado=("selecionado", "sum"))
    stability["cenarios_testados"] = len(records)
    stability["fracao_cenarios_selecionado"] = stability["cenarios_selecionado"] / len(records)
    return pd.DataFrame(records), stability.reset_index()


def geographic_summary(result, geography="regiao"):
    records = []
    for area, table in result.groupby(geography, sort=True):
        selected = int(table["convergencia_total"].sum())
        eligible = int(table["elegivel_principal"].sum())
        record = {geography: area, "municipios": len(table), "elegiveis": eligible,
                  "convergencia_total": selected, "pct_convergencia_universo": selected / len(table) * 100,
                  "pct_convergencia_elegiveis": selected / eligible * 100 if eligible else np.nan}
        for label, total in [("dai", "avaliados_altura"), ("dpi", "avaliados_peso")]:
            valid = table[total].gt(0) & table[label + "_n"].notna()
            denominator = table.loc[valid, total].sum()
            record[total] = denominator
            record[label + "_n"] = table.loc[valid, label + "_n"].sum()
            record[label + "_pct_agregado"] = record[label + "_n"] / denominator * 100 if denominator else np.nan
        records.append(record)
    return pd.DataFrame(records)


def nutrition_comparison(result):
    common = result["nutricional_mapa_insan"].notna()
    records = []
    for label, valid in [("Todos os válidos para DAI", result["dim_nutricional"].notna()),
                         ("Denominadores válidos em altura e peso", common)]:
        records.append({"universo": label, "municipios": int(valid.sum()),
                        "dai_isolado": int(result.loc[valid, "dim_nutricional"].sum()),
                        "dai_e_dpi": int(result.loc[valid, "nutricional_mapa_insan"].sum()),
                        "convergencia_dai": int(result.loc[valid, "convergencia_total"].sum()),
                        "convergencia_dai_dpi": int(result.loc[valid, "convergencia_total_dai_dpi"].sum())})
    return pd.DataFrame(records)


def distribution_figure(result, output):
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 3, figsize=(14, 7))
    columns = [("ivs", "IVS — 2010"), ("idhm", "IDHM — 2010"), ("cadinsan_pct", "CadInsan (%)"),
               ("dai_pct", "DAI (%) — com avaliações"), ("dpi_pct", "DPI (%) — com avaliações"),
               ("avaliados_altura", "Avaliações de altura — escala log")]
    for ax, (column, title) in zip(axes.flat, columns):
        values = result[column].dropna()
        if column == "avaliados_altura":
            values = np.log10(values[values > 0])
            ax.set_xlabel("log10(total avaliado)")
        ax.hist(values, bins=35, color="#327c81", edgecolor="white", linewidth=0.4)
        ax.set(title=title, ylabel="Municípios")
    fig.tight_layout()
    save_figure(fig, output, "01_distribuicoes")
    return fig


def association_figure(result, thresholds, output):
    import matplotlib.pyplot as plt
    cuts = thresholds.set_index("indicador")["corte"]
    valid = result[result["elegivel_principal"]]
    chosen = valid["convergencia_total"].fillna(False)
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    for ax, (column, label, criterion) in zip(axes, [("ivs", "IVS (2010)", "ivs"),
        ("idhm", "IDHM (2010)", "idhm"), ("cadinsan_pct", "CadInsan (%)", "cadinsan")]):
        ax.scatter(valid[column], valid["dai_pct"], s=8, alpha=0.25, color="#327c81")
        ax.scatter(valid.loc[chosen, column], valid.loc[chosen, "dai_pct"], s=13, alpha=0.7, color="#9e1b32")
        ax.axhline(cuts["dai"], color="#777777", linestyle="--", linewidth=1)
        ax.axvline(cuts[criterion], color="#777777", linestyle="--", linewidth=1)
        ax.set(xlabel=label, ylabel="DAI (%)", title=f"{label} × DAI")
    fig.suptitle("Municípios elegíveis; vermelho = convergência das três dimensões")
    fig.tight_layout()
    save_figure(fig, output, "02_associacoes")
    return fig


def correlation_figure(result, output, minimum=20):
    import matplotlib.pyplot as plt
    cols = ["ivs", "idhm", "cadinsan_pct", "dai_pct", "dpi_pct"]
    data = result[cols].copy()
    for indicator, total in [("dai_pct", "avaliados_altura"), ("dpi_pct", "avaliados_peso")]:
        data[indicator] = data[indicator].where(result[total].ge(minimum))
    corr = data.corr(method="spearman", min_periods=3)
    pairs = data.notna().astype(int).T @ data.notna().astype(int)
    fig, ax = plt.subplots(figsize=(8, 7))
    im = ax.imshow(corr, vmin=-1, vmax=1, cmap="RdBu_r")
    ax.set_xticks(range(5), ["IVS", "IDHM", "CadInsan", "DAI", "DPI"])
    ax.set_yticks(range(5), ["IVS", "IDHM", "CadInsan", "DAI", "DPI"])
    for i in range(5):
        for j in range(5):
            ax.text(j, i, f"{corr.iloc[i, j]:.2f}\nn={pairs.iloc[i, j]}", ha="center", va="center",
                    fontsize=9, color="white" if abs(corr.iloc[i, j]) > 0.65 else "black")
    ax.set_title("Spearman — pares disponíveis; nutrição com denominador mínimo")
    fig.colorbar(im, ax=ax, shrink=0.8)
    fig.tight_layout()
    save_figure(fig, output, "03_correlacoes")
    return fig, corr, pairs


def sensitivity_figure(table, output, scenario="com_PBF"):
    import matplotlib.pyplot as plt
    subset = table.loc[table["cenario"].eq(scenario)]
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5), sharey=True)
    for ax, reference in zip(axes, ["6.7", "10.0", "P75"]):
        for minimum, group in subset.loc[subset["referencia_dai"].eq(reference)].groupby("minimo_avaliados"):
            group = group.sort_values("quantil")
            ax.plot(group["quantil"] * 100, group["convergencia_total"], marker="o", label=f"n ≥ {minimum}")
        ax.set(title=f"DAI ≥ {reference.replace('.', ',')}{'%' if reference != 'P75' else ''}",
               xlabel="Percentil CadInsan", xticks=[70, 75, 80, 90])
        ax.legend()
    axes[0].set_ylabel("Municípios com convergência total")
    fig.suptitle(f"Sensibilidade — {scenario}; cortes IVS/IDHM fixos")
    fig.tight_layout()
    save_figure(fig, output, "04_sensibilidade")
    return fig


def dictionary():
    rows = [
        ("codigo_ibge", "Código de sete dígitos disponível nas fontes sociais; prefixo de seis se desconhecido", "texto"),
        ("codigo_ibge_6", "Prefixo único usado na integração; não valida limites históricos", "texto"),
        ("codigo_ibge_7", "Código das fontes sociais; sem inventar dígito verificador", "texto"),
        ("municipio / uf / regiao", "Identificação territorial", "texto"),
        ("ivs", "Índice de Vulnerabilidade Social, 2010; corte ≥ 0,401", "0–1"),
        ("idhm", "Desenvolvimento humano municipal, 2010; corte < 0,600", "0–1"),
        ("familias_cadinsan", "Denominador familiar do próprio CSV CadInsan, janeiro/2025", "famílias"),
        ("cadinsan_n", "Famílias em risco estimado no cenário selecionado", "famílias"),
        ("cadinsan_pct", "100 × cadinsan_n / familias_cadinsan; corte P75 exploratório", "%"),
        ("cadinsan_pct_*_arquivo", "Percentuais oficiais arredondados, preservados", "%"),
        ("cadinsan_diferenca_pp_*", "Diferença da razão recalculada para o percentual da fonte", "pontos percentuais"),
        ("avaliados_altura / avaliados_peso", "Totais separados por relatório SISVAN, menores de cinco anos, 2025", "avaliados"),
        ("altura_muito_baixa_n / altura_baixa_n", "Categorias de baixa estatura classificadas pelo SISVAN", "avaliados"),
        ("peso_muito_baixo_n / peso_baixo_n", "Categorias de baixo peso classificadas pelo SISVAN", "avaliados"),
        ("dai_n / dpi_n", "Soma das duas categorias desfavoráveis do respectivo relatório", "avaliados"),
        ("dai_pct / dpi_pct", "100 × numerador / respectivo total; total zero gera ausência", "%"),
        ("dai_categoria_oms", "Faixas <2,5; [2,5,10); [10,20); [20,30); ≥30; insuficiente abaixo do mínimo", "categoria"),
        ("criterio_*", "Critérios individuais anuláveis; DPI não integra seleção principal", "booleano anulável"),
        ("dim_social / social_alta", "IVS ≥ 0,401 E IDHM < 0,600; ausente se falta algum", "booleano anulável"),
        ("social_status", "Combinação dos dois critérios sociais; não representa duas dimensões", "categoria"),
        ("dim_alimentar / cadinsan_alto", "CadInsan ≥ P75 nacional no cenário selecionado", "booleano anulável"),
        ("dim_nutricional / nutricional_alta", "DAI ≥ 6,7%, com total altura ≥20 no cenário principal", "booleano anulável"),
        ("nutricional_mapa_insan", "DAI ≥6,7% E DPI ≥1,8%, ambos com denominadores ≥mínimo; adaptação, não Mapa oficial", "booleano anulável"),
        ("dpi_status", "Situação complementar do DPI, com mínimo próprio de peso", "categoria"),
        ("n_dimensoes_desfavoraveis", "Número de dimensões desfavoráveis, ausente se qualquer dimensão é desconhecida", "0–3"),
        ("classe_prioridade", "Classe descritiva da convergência; não diagnóstico ou ranking", "categoria"),
        ("convergencia_total / prioridade_maxima", "As três dimensões desfavoráveis; ausente se informação insuficiente", "booleano anulável"),
        ("convergencia_total_dai_dpi", "Social E alimentar E critério nutricional combinado DAI+DPI", "booleano anulável"),
        ("motivo_nao_classificacao", "Motivo de insuficiência para a seleção principal; DPI não é requisito", "texto"),
        ("*_valor_fonte / *_percentual_fonte", "Células da fonte antes de qualquer leitura analítica", "texto"),
        ("sisvan_*_escala_alterada / sisvan_*_escalas_compativeis", "Auditoria de leitura das contagens já existente na v1", "booleano / inteiro"),
        ("tem_*", "Presença de registro na respectiva entrada", "booleano"),
        ("fracao_cenarios_selecionado", "Fração de cenários testados que seleciona; não probabilidade de risco", "0–1"),
    ]
    return pd.DataFrame(rows, columns=["variavel", "definicao", "unidade"])
