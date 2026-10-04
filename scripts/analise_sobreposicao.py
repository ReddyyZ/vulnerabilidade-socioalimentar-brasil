"""Análise municipal exploratória usada pelo notebook autocontido do Colab."""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal, InvalidOperation
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd


DATA_FILES = {
    "ivs_idhm": "ivs_idhm/atlasivs_municipios_2010.csv",
    "cadunico": "cadunico/municipios-cadunico.json",
    "cadinsan": "cadinsan/CADINSAN_2025_dados_municipais.csv",
    "sisvan": "sisvan/sisvan_municipios_altura_por_idade_0_a_menor_5_anos_2025.csv",
}
CATALOGUE_DATASETS = {
    "ivs_idhm": "municipios_ivs",
    "cadunico": "municipios_cadunico",
    "cadinsan": "municipios_cadinsan",
}
FIXED_CUTS = {"ivs": (0.401, ">="), "idhm": (0.600, "<")}
GROUP_COLORS = {
    "Convergência dos quatro critérios": "#9e1b32",
    "IVS e CadInsan elevados, IDHM baixo, DAI abaixo do corte": "#e89c38",
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


def validate_catalogue(catalogue_path, directory):
    """Confere que os metadados sociais descrevem exatamente os arquivos usados."""
    catalogue_path, directory = Path(catalogue_path), Path(directory)
    raw = catalogue_path.read_bytes()
    catalogue = json.loads(raw.decode("utf-8-sig"))
    records = []
    for source, dataset_id in CATALOGUE_DATASETS.items():
        dataset = catalogue["datasets"][dataset_id]
        relative = DATA_FILES[source]
        actual = hashlib.sha256((directory / relative).read_bytes()).hexdigest()
        expected = dataset["stats"]["checkSum"].removeprefix("sha256:")
        if actual != expected:
            raise ValueError(f"Catálogo não corresponde ao arquivo {relative}.")
        temporal = dataset["temporal"]["extent"][0]
        fields = dataset["schema"]["fields"]
        units = sorted({f["unit"] for f in fields if "unit" in f})
        records.append({"dataset_id": dataset_id, "arquivo": relative,
                        "titulo": dataset["title"], "inicio_referencia_catalogo": temporal[0],
                        "fim_referencia_catalogo": temporal[1], "unidades_catalogo": "; ".join(units),
                        "fonte_original": dataset["source"]["url"],
                        "sha256": actual, "corresponde_ao_catalogo": True})
    provenance = {"catalogo_id": catalogue["catalog"]["id"],
                  "catalogo_status": catalogue["catalog"]["status"],
                  "catalogo_atualizado_em": catalogue["catalog"]["updated_at"],
                  "catalogo_sha256": hashlib.sha256(raw).hexdigest(),
                  "schema_version": catalogue["schema_version"],
                  "fontes": records,
                  "cadunico": {"unidade": "pessoas", "periodo": "2026-06",
                               "campo_fonte": "cadun_qtd_pessoas_cadastradas_i",
                               "evidencia": "datasets.municipios_cadunico.source.notes e schema.fields"},
                  "cadinsan": {"unidade": "famílias", "referencia_catalogo": "2025",
                               "referencia_relatorio_oficial": "2025-01",
                               "populacao": "Famílias do universo analisado pelo CadInsan; não todas as pessoas cadastradas",
                               "cenarios": {"com_PBF": "Risco estimado considerando o efeito do PBF na renda",
                                            "sem_PBF": "Cenário contrafactual desconsiderando o efeito do PBF"},
                               "relatorio_oficial": "https://www.gov.br/mds/pt-br/Sisan/vigilancia-do-sisan/CADINSAN2025.pdf",
                               "evidencia": "Relatório: metodologia, p. 7; cenários, p. 16–19; tabela municipal, p. 22. "
                                            "Valores municipais conferidos por amostragem com o CSV."}}
    return pd.DataFrame(records), provenance


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


def sisvan_metadata(directory):
    path = Path(directory) / DATA_FILES["sisvan"]
    metadata = json.loads(path.with_suffix(".metadados.json").read_text(encoding="utf-8"))
    expected = {"ano": 2025, "fase": "crianca", "indice": "altura_por_idade",
                "faixa_etaria": "0_a_menor_5_anos", "nu_idade_inicio": "0", "nu_idade_fim": "5"}
    if any(metadata.get(key) != value for key, value in expected.items()):
        raise ValueError("SISVAN fora do recorte previsto: altura, 2025, menores de 5 anos.")
    if metadata.get("indicadores_derivados") != []:
        raise ValueError("A entrada SISVAN deve conter somente valores da fonte.")
    if metadata.get("sha256_csv") != hashlib.sha256(path.read_bytes()).hexdigest():
        raise ValueError("Metadados SISVAN não correspondem ao CSV.")
    if set(metadata.get("ufs", [])) != {uf for uf, _ in UF_REGIONS.values()}:
        raise ValueError("SISVAN: coleta nacional incompleta.")
    return metadata


def interpret_sisvan_counts(values, percentages, code):
    """Interpreta artefatos numéricos sem modificar as células de entrada.

    Mantém inteiros coerentes sem criar uma alternativa uniforme ×1000.
    Decimais do XLSX são interpretados como milhares. Apenas quando a soma
    ou os percentuais não conferem, tenta conciliar células truncadas pelo
    exportador. Exige uma solução única, soma exata e percentuais a 0,011 pp.
    """
    original_values, initial, integral = [], [], []
    for raw in values:
        text = str(raw).strip()
        try:
            value = Decimal(text)
        except InvalidOperation as exc:
            raise ValueError(f"{code}: contagem SISVAN não numérica: {raw!r}") from exc
        if not value.is_finite() or value < 0:
            raise ValueError(f"{code}: contagem SISVAN inválida: {raw!r}")
        original_values.append(value)
        if value == value.to_integral_value():
            initial.append(int(value))
            integral.append(True)
        else:
            scaled = value * 1000
            if scaled != scaled.to_integral_value():
                raise ValueError(f"{code}: escala decimal SISVAN irresolvível: {raw!r}")
            initial.append(int(scaled))
            integral.append(False)
    pcts = []
    for raw in percentages:
        text = str(raw).strip()
        pct = 0.0 if text in {"-", "–", "—"} else float(text.rstrip("%").replace(",", "."))
        if not np.isfinite(pct) or not 0 <= pct <= 100:
            raise ValueError(f"{code}: percentual SISVAN inválido: {raw!r}")
        pcts.append(pct)

    def consistent(counts, total):
        if sum(counts) != total:
            return False
        if total == 0:
            return not any(pcts)
        return all(abs(n / total * 100 - pct) <= 0.011 for n, pct in zip(counts, pcts))

    # Regra aprovada: não extrapolar inteiros cuja soma e percentuais conferem.
    if consistent(initial[:-1], initial[-1]):
        changed = any(value != n for value, n in zip(original_values, initial))
        return tuple(initial), changed, 1

    # Exportações podem perder zeros finais (ex.: 1.000 vira 1). Essa leitura
    # só é tentada para linhas inconsistentes, não para criar outra população.
    candidates = [[n, n * 1000] if is_int and n else [n]
                  for n, is_int in zip(initial, integral)]
    solutions = []
    for counts in product(*candidates[:-1]):
        total = sum(counts)
        if total not in candidates[-1]:
            continue
        if not consistent(counts, total):
            continue
        solutions.append((*counts, total))
    if not solutions:
        raise ValueError(f"{code}: contagens não conciliam soma e percentuais oficiais.")
    if len(solutions) != 1:
        raise ValueError(f"{code}: contagens inconsistentes admitem mais de uma interpretação; conferir na fonte.")
    chosen = solutions[0]
    changed = any(value != n for value, n in zip(original_values, chosen))
    return chosen, changed, 1


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
    for scenario in ("com_PBF", "sem_PBF"):
        tables["cadinsan"].rename(
            columns={f"cadinsan_pct_{scenario}": f"cadinsan_pct_{scenario}_arquivo"}, inplace=True)
    sv = sources["sisvan"]
    metadata = sisvan_metadata(directory)
    if list(sv.columns) != metadata["colunas"] or len(sv) != metadata["linhas"]:
        raise ValueError("SISVAN: esquema ou número de linhas difere dos metadados.")
    tables["sisvan"] = pd.DataFrame({
        "codigo_sisvan_original": codes(sv["Código IBGE"], 6, "SISVAN"),
        "municipio_sisvan": sv["Município"], "uf_sisvan": sv["UF"],
        "ano_sisvan": metadata["ano"],
    })
    counts = {
        "Altura Muito Baixa para a Idade - Quantidade": "altura_muito_baixa_n",
        "Altura Baixa para a Idade - Quantidade": "altura_baixa_n",
        "Altura Adequada para a Idade - Quantidade": "altura_adequada_n",
        "Total": "avaliados_altura",
    }
    percentages = [original.replace(" - Quantidade", " - %") for original in list(counts)[:3]]
    interpreted = [interpret_sisvan_counts(
        [row[c] for c in counts], [row[c] for c in percentages], row["Código IBGE"])
        for _, row in sv.iterrows()]
    for original, new in counts.items():
        tables["sisvan"][new + "_valor_fonte"] = sv[original]
    for index, new in enumerate(counts.values()):
        tables["sisvan"][new] = [item[0][index] for item in interpreted]
    for original, new in zip(percentages, list(counts.values())[:3]):
        tables["sisvan"][new + "_percentual_fonte"] = sv[original]
    tables["sisvan"]["sisvan_escala_alterada"] = [item[1] for item in interpreted]
    tables["sisvan"]["sisvan_escalas_compativeis"] = [item[2] for item in interpreted]
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
    base["cadunico_pessoas_2026_06"] = base["cadunico_valor_original"]
    base["cadunico_referencia"] = "2026-06"
    base["cadinsan_referencia"] = "2025-01"
    base["uf"] = base["codigo_ibge_6"].str[:2].map(lambda c: UF_REGIONS[c][0])
    base["regiao"] = base["codigo_ibge_6"].str[:2].map(lambda c: UF_REGIONS[c][1])
    sv_rows = base["tem_sisvan"]
    if base.loc[sv_rows, "uf"].ne(base.loc[sv_rows, "uf_sisvan"]).any():
        raise ValueError("UF SISVAN incompatível com o prefixo municipal.")

    nonnegative = [c for c in base if c.endswith("_n") or c == "avaliados_altura"]
    nonnegative += ["cadunico_valor_original", "cadastros_cadunico_cadinsan",
                    "cadinsan_n_com_PBF", "cadinsan_n_sem_PBF"]
    for column in nonnegative:
        values = base[column].dropna()
        if (values < 0).any() or not np.isclose(values % 1, 0).all():
            raise ValueError(f"{column}: contagem negativa ou não inteira.")
    for prefix, parts, total in (
        ("dai", ["altura_muito_baixa_n", "altura_baixa_n", "altura_adequada_n"], "avaliados_altura"),
    ):
        component_total = base[parts].sum(axis=1, min_count=len(parts))
        if not np.allclose(component_total[sv_rows], base.loc[sv_rows, total], equal_nan=False):
            raise ValueError(f"Soma das categorias incompatível com {total}.")
        base[f"{prefix}_n"] = base[parts[:2]].sum(axis=1, min_count=2)
        base[f"{prefix}_pct"] = base[f"{prefix}_n"].div(base[total].where(base[total] > 0)) * 100
        check_range(base[f"{prefix}_pct"], 0, 100, prefix)
    for scenario in ("com_PBF", "sem_PBF"):
        check_range(base[f"cadinsan_pct_{scenario}_arquivo"], 0, 100, "CadInsan no arquivo")
        denominator = base["cadastros_cadunico_cadinsan"]
        absolute = base[f"cadinsan_n_{scenario}"]
        if (absolute > denominator).fillna(False).any():
            raise ValueError("CadInsan absoluto excede o total de cadastros informado.")
        calculated = absolute.div(denominator.where(denominator > 0)) * 100
        reported = base[f"cadinsan_pct_{scenario}_arquivo"]
        complete = calculated.notna() & reported.notna()
        if not np.allclose(calculated[complete], reported[complete], atol=0.11):
            raise ValueError("Percentual CadInsan diverge da razão no arquivo.")
        base[f"cadinsan_pct_{scenario}"] = calculated
        base[f"cadinsan_diferenca_pp_{scenario}"] = calculated - reported
        check_range(calculated, 0, 100, "CadInsan recalculado")
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
    """IVS/IDHM fixos; quantis nacionais nos demais; DAI exige denominador mínimo."""
    if not 0 < quantile < 1 or not isinstance(min_evaluated, int) or min_evaluated < 1:
        raise ValueError("Quantil deve estar entre 0 e 1 e o mínimo deve ser inteiro positivo.")
    if scenario not in ("com_PBF", "sem_PBF"):
        raise ValueError("Cenário deve ser com_PBF ou sem_PBF.")
    result = base.copy()
    result["cadinsan_pct"] = result[f"cadinsan_pct_{scenario}"]
    if f"cadinsan_pct_{scenario}_arquivo" in result:
        result["cadinsan_pct_arquivo"] = result[f"cadinsan_pct_{scenario}_arquivo"]
    result["cadinsan_n"] = result[f"cadinsan_n_{scenario}"]
    specs = [
        ("ivs", "ivs", pd.Series(True, index=result.index)),
        ("cadinsan", "cadinsan_pct", result["cadastros_cadunico_cadinsan"] > 0),
        ("dai", "dai_pct", result["avaliados_altura"] >= min_evaluated),
        ("idhm", "idhm", pd.Series(True, index=result.index)),
    ]
    thresholds = []
    for label, column, eligible in specs:
        valid = eligible & result[column].notna()
        if not valid.any():
            raise ValueError(f"Nenhum município elegível para {label}.")
        if label in FIXED_CUTS:
            cutoff, operator = FIXED_CUTS[label]
            method, percentile = "fixo", None
        else:
            cutoff = result.loc[valid, column].quantile(quantile)
            operator, method, percentile = ">=", "quantil", quantile * 100
        flag = pd.Series(pd.NA, index=result.index, dtype="boolean")
        flag.loc[valid] = (result.loc[valid, column] >= cutoff if operator == ">="
                           else result.loc[valid, column] < cutoff)
        result[f"criterio_{label}"] = flag
        thresholds.append({"indicador": label, "corte": float(cutoff),
                           "operador": operator, "metodo": method,
                           "municipios_referencia": int(valid.sum()),
                           "municipios_no_criterio": int(flag.fillna(False).sum()),
                           "percentil": percentile})
    primary = ["criterio_ivs", "criterio_idhm", "criterio_cadinsan", "criterio_dai"]
    result["elegivel_principal"] = result[primary].notna().all(axis=1)
    result["prioritario"] = result[primary].all(axis=1).where(result["elegivel_principal"]).astype("boolean")
    result["numero_criterios_primarios"] = result[primary].sum(axis=1).where(result["elegivel_principal"]).astype("Int64")
    social = (result["criterio_ivs"] & result["criterio_idhm"] & result["criterio_cadinsan"]).fillna(False)
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
        if pd.isna(row.idhm): missing.append("IDHM ausente")
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
    cuts = pd.DataFrame(thresholds)
    cuts["percentil"] = cuts["percentil"].astype(object).where(cuts["percentil"].notna(), None)
    return result, cuts


def compare_rounding(base, reference, quantile=0.75, min_evaluated=100, scenario="com_PBF"):
    """Audita a diferença entre usar percentuais do CSV e razões sem arredondar."""
    rounded = base.copy()
    for option in ("com_PBF", "sem_PBF"):
        rounded[f"cadinsan_pct_{option}"] = rounded[f"cadinsan_pct_{option}_arquivo"]
    previous, thresholds = classify(rounded, quantile, min_evaluated, scenario)
    columns = ["codigo_ibge_6", "municipio", "uf", "cadinsan_pct", "cadinsan_pct_arquivo"]
    comparison = reference[columns].copy()
    old = previous.set_index("codigo_ibge_6")
    comparison["selecionado_percentual_csv"] = comparison["codigo_ibge_6"].map(old["prioritario"])
    comparison["selecionado_sem_arredondamento"] = reference["prioritario"].to_numpy()
    comparison["mudou_selecao"] = (comparison["selecionado_percentual_csv"].fillna(False).astype(bool)
                                   != comparison["selecionado_sem_arredondamento"].fillna(False).astype(bool))
    return comparison, thresholds


def sensitivity(base, reference, quantiles=(0.75, 0.80), minima=(30, 50, 100),
                scenarios=("com_PBF", "sem_PBF")):
    reference_set = set(reference.loc[reference["prioritario"].fillna(False), "codigo_ibge_6"])
    records, selections = [], []
    for scenario, quantile, minimum in product(scenarios, quantiles, minima):
        result, _ = classify(base, quantile, minimum, scenario)
        selected = set(result.loc[result["prioritario"].fillna(False), "codigo_ibge_6"])
        union = reference_set | selected
        records.append({"cenario": scenario, "quantil": quantile,
                        "corte_ivs": FIXED_CUTS["ivs"][0], "operador_ivs": FIXED_CUTS["ivs"][1],
                        "corte_idhm": FIXED_CUTS["idhm"][0], "operador_idhm": FIXED_CUTS["idhm"][1],
                        "minimo_avaliados": minimum,
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
        for label, total in (("dai", "avaliados_altura"),):
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
        ("ivs", "Índice de Vulnerabilidade Social", "0–1", "IVS, 2010", "Critério obrigatório: IVS ≥ 0,401, alta ou muito alta vulnerabilidade"),
        ("idhm", "Índice de Desenvolvimento Humano Municipal", "0–1", "IDHM, 2010", "Critério obrigatório: IDHM < 0,600, baixo ou muito baixo"),
        ("cadunico_valor_original", "Pessoas cadastradas, valor preservado do JSON", "pessoas", "CadÚnico, junho/2026", "Unidade e período descritos no catálogo com hash correspondente"),
        ("cadunico_pessoas_2026_06", "Alias explícito para pessoas cadastradas", "pessoas", "CadÚnico, junho/2026", "Contexto de demanda; não integra a regra principal"),
        ("cadunico_referencia", "Referência mensal do JSON", "ano-mês", "Catálogo Cozinhas Solidárias", "2026-06"),
        ("cadinsan_referencia", "Referência da base do CadInsan", "ano-mês", "Relatório oficial do MDS", "2025-01; não é uma média anual"),
        ("cadastros_cadunico_cadinsan", "Famílias consideradas no denominador do CSV", "famílias", "CadInsan, janeiro/2025", "Universo analisado; não equivale às pessoas do JSON"),
        ("cadinsan_pct", "100 × quantidade do cenário / famílias no denominador", "%", "CadInsan, janeiro/2025", "Sem arredondamento; cenários com/sem efeito do PBF"),
        ("cadinsan_pct_*_arquivo", "Percentuais do CSV preservados", "%", "CadInsan, janeiro/2025", "Arredondados; usados para comparação, não para seleção"),
        ("cadinsan_diferenca_pp_*", "Recalculado menos percentual do arquivo", "pontos percentuais", "Análise derivada", "Não confundir com variação percentual relativa"),
        ("cadinsan_n", "Famílias em risco estimado no cenário selecionado", "famílias", "CadInsan, janeiro/2025", "Não é contagem de pessoas nem medida direta de fome"),
        ("dai_n", "Altura muito baixa + altura baixa", "registros avaliados", "SISVAN, 2025", "Numerador recalculado"),
        ("dai_pct", "100 × dai_n / avaliados_altura", "%", "SISVAN, 2025", "Sem arredondamento; denominador zero gera NaN"),
        ("avaliados_altura", "Total avaliado em Altura X Idade", "registros avaliados", "SISVAN, 2025", "Não é medida de cobertura populacional"),
        ("*_valor_fonte", "Valores das células de contagem do XLSX", "texto", "SISVAN, 2025", "Preservados antes da interpretação da escala"),
        ("sisvan_escala_alterada", "Alguma contagem foi interpretada em escala diferente", "booleano", "Análise derivada", "A entrada não é reescrita"),
        ("sisvan_escalas_compativeis", "Uma interpretação validada por soma e percentuais", "inteiro", "Análise derivada", "Inteiros coerentes são mantidos; linhas inconsistentes exigem solução única"),
        ("criterio_*", "Flag para corte fixo (IVS/IDHM) ou quantil nacional (demais)", "booleano anulável", "Análise derivada", "Ausente quando indicador não é elegível; IVS ≥ 0,401 e IDHM < 0,600"),
        ("prioritario", "Coincidência de IVS, CadInsan e DAI elevados e IDHM baixo", "booleano anulável", "Análise derivada", "Quatro critérios obrigatórios; ausente para informação insuficiente"),
        ("numero_criterios_primarios", "Quantidade de critérios primários atendidos", "0–4", "Análise derivada", "Ausente quando falta informação para qualquer critério primário; não é ranking"),
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
               ("avaliados_altura", "Avaliações de altura — escala log")]
    for ax, (column, title) in zip(axes.flat, columns):
        values = result[column].dropna()
        if column == "avaliados_altura":
            values = np.log10(values[values > 0])
            ax.set_xlabel("log10(total avaliado)")
        ax.hist(values, bins=35, color="#327c81", edgecolor="white", linewidth=0.4)
        ax.set_title(title)
        ax.set_ylabel("Municípios")
    axes.flat[-1].set_visible(False)
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
    fig.suptitle("Municípios elegíveis; vermelho = convergência dos quatro critérios")
    fig.tight_layout()
    save_figure(fig, output, "02_associacoes")
    return fig


def correlation_figure(result, output, minimum=100):
    import matplotlib.pyplot as plt
    cols = ["ivs", "idhm", "cadinsan_pct", "dai_pct"]
    data = result[cols].copy()
    data.loc[result["avaliados_altura"] < minimum, "dai_pct"] = np.nan
    corr = data.corr(method="spearman", min_periods=3)
    pair_counts = data.notna().astype(int).T @ data.notna().astype(int)
    fig, ax = plt.subplots(figsize=(7, 6))
    im = ax.imshow(corr, vmin=-1, vmax=1, cmap="RdBu_r")
    ax.set_xticks(range(len(cols)), ["IVS", "IDHM", "CadInsan", "DAI"])
    ax.set_yticks(range(len(cols)), ["IVS", "IDHM", "CadInsan", "DAI"])
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
    labels = [f"{r.cenario}\nCadInsan/DAI P{r.quantil * 100:.0f}\nn≥{r.minimo_avaliados}"
              for r in table.itertuples()]
    ax.bar(range(len(table)), table["prioritarios"], color="#327c81")
    ax.set_xticks(range(len(table)), labels, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("Municípios selecionados")
    ax.set_title("Sensibilidade: quantis, denominadores e cenários; IVS/IDHM com cortes fixos")
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
    from textwrap import fill
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
        ax.legend(handles=[Patch(facecolor=color, label=fill(label, width=42)) for label, color in categories.items()],
                  loc="lower left", fontsize=8, frameon=False)
    else:
        arr = np.ma.masked_invalid(values)
        collection.set_array(arr)
        cmap = plt.get_cmap("YlOrRd_r" if column == "idhm" else "YlOrRd").copy()
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
