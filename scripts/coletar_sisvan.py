#!/usr/bin/env python3
"""Coleta e harmoniza relatorios municipais do estado nutricional no SISVAN.

Cada XLSX oficial e preservado sem alteracao. Somente produtos derivados
somam faixas etarias ou harmonizam classificacoes entre fases da vida.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from itertools import product
from pathlib import Path

from openpyxl import load_workbook

if __package__:
    from . import sisvan_cliente as helper
else:
    import sisvan_cliente as helper


UF_CODES = [
    ("RO", "11"), ("AC", "12"), ("AM", "13"), ("RR", "14"),
    ("PA", "15"), ("AP", "16"), ("TO", "17"), ("MA", "21"),
    ("PI", "22"), ("CE", "23"), ("RN", "24"), ("PB", "25"),
    ("PE", "26"), ("AL", "27"), ("SE", "28"), ("BA", "29"),
    ("MG", "31"), ("ES", "32"), ("RJ", "33"), ("SP", "35"),
    ("PR", "41"), ("SC", "42"), ("RS", "43"), ("MS", "50"),
    ("MT", "51"), ("GO", "52"), ("DF", "53"),
]
BASE_COLUMNS = ("Região", "Código UF", "UF", "Código IBGE", "Município")
MANIFEST_COLUMNS = (
    "id_coleta", "fonte", "arquivo_local", "nome_original",
    "indice_antropometrico", "faixa_etaria", "ano_inicio", "ano_fim",
    "abrangencia", "filtros", "data_hora_coleta", "quantidade_registros",
    "hash_arquivo", "status", "versao_coletor", "observacoes",
)
COMBINED_COLUMNS = (
    "Fase da vida", "Código da fase SISVAN",
    "Índice antropométrico", "Código do índice SISVAN", "Faixa etária",
    "Código da faixa etária", "Idade inicial SISVAN", "Idade final SISVAN",
    "Ano", *BASE_COLUMNS, "Classificação nutricional", "Quantidade",
    "Percentual", "Total",
)
SUMMED_COLUMNS = (
    "Fase da vida", "Código da fase SISVAN", "Índice antropométrico",
    "Código do índice SISVAN", "Faixas etárias participantes",
    "Códigos das faixas etárias", "Ano", *BASE_COLUMNS,
    "Classificação nutricional oficial", "Quantidade",
    "Percentual recalculado", "Total",
)
HARMONIZED_COLUMNS = (
    "Fase da vida", "Faixas etárias participantes", "Ano", *BASE_COLUMNS,
    "Magreza acentuada - Quantidade",
    "Magreza acentuada - % (crianças e adolescentes)",
    "Magreza - Quantidade",
    "Magreza - % (crianças e adolescentes)",
    "Baixo peso - Quantidade",
    "Baixo peso - % (adultos e idosos)",
    "Déficit nutricional total - Quantidade",
    "Déficit nutricional total - %",
    "Estado nutricional adequado - Quantidade",
    "Estado nutricional adequado - %",
    "Risco para excesso de peso - Quantidade",
    "Risco para excesso de peso - % (faixas aplicáveis)",
    "Excesso de peso - Quantidade", "Excesso de peso - %",
    "Total crianças e adolescentes (denominador)",
    "Total adultos e idosos (denominador)",
    "Total com risco de sobrepeso aplicável (denominador)", "Total",
)
PREGNANT_COLUMNS = (
    "Fase da vida", "Ano", *BASE_COLUMNS,
    "Baixo peso - Quantidade", "Baixo peso - %",
    "Adequado ou Eutrófico - Quantidade", "Adequado ou Eutrófico - %",
    "Sobrepeso - Quantidade", "Sobrepeso - %",
    "Obesidade - Quantidade", "Obesidade - %",
    "Excesso de peso - Quantidade", "Excesso de peso - %", "Total",
)
COLLECTOR_VERSION = "5.0"


@dataclass(frozen=True)
class Phase:
    key: str
    code: str
    official_label: str


@dataclass(frozen=True)
class Indicator:
    key: str
    code: str
    code_field: str | None
    official_title: str
    categories: tuple[str, ...]


@dataclass(frozen=True)
class AgeRange:
    key: str
    start: str
    end: str
    official_label: str
    start_month: int | None
    end_month: int | None


@dataclass(frozen=True)
class Query:
    phase: Phase
    indicator: Indicator
    age_range: AgeRange
    year: int


@dataclass(frozen=True)
class Schema:
    categories: tuple[str, ...]
    columns: tuple[str, ...]

    @property
    def count_columns(self):
        return tuple("%s - Quantidade" % item for item in self.categories)

    @property
    def percent_columns(self):
        return tuple("%s - %%" % item for item in self.categories)


PHASES = {
    "crianca": Phase("crianca", "1", "CRIANÇA"),
    "adolescente": Phase("adolescente", "2", "ADOLESCENTE"),
    "adulto": Phase("adulto", "3", "ADULTO"),
    "idoso": Phase("idoso", "4", "IDOSO"),
    "gestante": Phase("gestante", "5", "GESTANTE"),
}

INDICATORS = {
    "imc_por_idade": Indicator(
        key="imc_por_idade",
        code="4",
        code_field="nu_indice_cri",
        official_title="IMC X IDADE",
        categories=(
            "Magreza acentuada", "Magreza", "Eutrofia",
            "Risco de sobrepeso", "Sobrepeso", "Obesidade",
        ),
    ),
    "altura_por_idade": Indicator(
        key="altura_por_idade",
        code="3",
        code_field="nu_indice_cri",
        official_title="ALTURA X IDADE",
        categories=(
            "Altura Muito Baixa para a Idade",
            "Altura Baixa para a Idade",
            "Altura Adequada para a Idade",
        ),
    ),
    "peso_por_idade": Indicator(
        key="peso_por_idade",
        code="1",
        code_field="nu_indice_cri",
        official_title="PESO X IDADE",
        categories=(
            "Peso Muito Baixo para a Idade",
            "Peso Baixo para a Idade",
            "Peso Adequado ou Eutrófico",
            "Peso Elevado para a Idade",
        ),
    ),
}

INDICATOR_VARIANTS = {
    ("crianca", "imc_por_idade", "menor_5"): INDICATORS["imc_por_idade"],
    ("crianca", "imc_por_idade", "5_a_10"): Indicator(
        "imc_por_idade", "4", "nu_indice_cri", "IMC X IDADE",
        (
            "Magreza acentuada", "Magreza", "Eutrofia",
            "Sobrepeso (5-10 anos)", "Obesidade (5-10 anos)",
            "Obesidade grave (5-10 anos)",
        ),
    ),
    ("crianca", "altura_por_idade", "todos"): INDICATORS["altura_por_idade"],
    ("crianca", "peso_por_idade", "todos"): INDICATORS["peso_por_idade"],
    ("adolescente", "imc_por_idade", "todos"): Indicator(
        "imc_por_idade", "2", "nu_indice_ado", "IMC X IDADE",
        (
            "Magreza acentuada", "Magreza", "Eutrofia", "Sobrepeso",
            "Obesidade", "Obesidade Grave",
        ),
    ),
    ("adolescente", "altura_por_idade", "todos"): Indicator(
        "altura_por_idade", "1", "nu_indice_ado", "ALTURA X IDADE",
        (
            "Altura Muito Baixa para a Idade",
            "Altura Baixa para a Idade",
            "Altura Adequado para a Idade",
        ),
    ),
    ("adulto", "imc", "todos"): Indicator(
        "imc", "", None, "IMC",
        (
            "Baixo peso", "Adequado ou Eutrófico", "Sobrepeso",
            "Obesidade Grau I", "Obesidade Grau II", "Obesidade Grau III",
        ),
    ),
    ("idoso", "imc", "todos"): Indicator(
        "imc", "", None, "IMC",
        ("Baixo peso", "Adequado ou Eutrófico", "Sobrepeso"),
    ),
    ("gestante", "imc_por_semana_gestacional", "todos"): Indicator(
        "imc_por_semana_gestacional", "", None,
        "IMC por semana gestacional",
        ("Baixo peso", "Adequado ou Eutrófico", "Sobrepeso", "Obesidade"),
    ),
}

PHASE_INDICES = {
    "crianca": ("altura_por_idade", "peso_por_idade", "imc_por_idade"),
    "adolescente": ("imc_por_idade", "altura_por_idade"),
    "adulto": ("imc",),
    "idoso": ("imc",),
    "gestante": ("imc_por_semana_gestacional",),
}

AGE_RANGES = {
    "0_a_menor_6_meses": AgeRange(
        "0_a_menor_6_meses", "0", "1", "0 a < 6 meses", 0, 6,
    ),
    "0_a_menor_2_anos": AgeRange(
        "0_a_menor_2_anos", "0", "2", "0 a < 2 anos", 0, 24,
    ),
    "0_a_menor_5_anos": AgeRange(
        "0_a_menor_5_anos", "0", "5", "0 a < 5 anos", 0, 60,
    ),
    "6_meses_a_menor_2_anos": AgeRange(
        "6_meses_a_menor_2_anos", "1", "2", "6 meses a < 2 anos", 6, 24,
    ),
    "6_meses_a_menor_5_anos": AgeRange(
        "6_meses_a_menor_5_anos", "1", "5", "6 meses a < 5 anos", 6, 60,
    ),
    "2_a_menor_5_anos": AgeRange(
        "2_a_menor_5_anos", "2", "5", "2 a < 5 anos", 24, 60,
    ),
    "5_a_menor_7_anos": AgeRange(
        "5_a_menor_7_anos", "5", "7", "5 a < 7 anos", 60, 84,
    ),
    "5_a_menor_10_anos": AgeRange(
        "5_a_menor_10_anos", "5", "10", "5 a < 10 anos", 60, 120,
    ),
    "7_a_menor_10_anos": AgeRange(
        "7_a_menor_10_anos", "7", "10", "7 a < 10 anos", 84, 120,
    ),
}

PHASE_AGE_RANGES = {
    "adolescente": AgeRange(
        "10_a_menor_20_anos", "", "", "10 a < 20 anos", 120, 240,
    ),
    "adulto": AgeRange(
        "20_a_menor_60_anos", "", "", "20 a < 60 anos", 240, 720,
    ),
    "idoso": AgeRange(
        "60_anos_ou_mais", "", "", "60 anos ou mais", 720, None,
    ),
    "gestante": AgeRange(
        "todas_as_idades_gestacionais", "", "", "TODAS", None, None,
    ),
}

AGE_ALIASES = {
    "0-6m": "0_a_menor_6_meses",
    "0-2": "0_a_menor_2_anos",
    "0-5": "0_a_menor_5_anos",
    "6m-2": "6_meses_a_menor_2_anos",
    "6m-5": "6_meses_a_menor_5_anos",
    "2-5": "2_a_menor_5_anos",
    "5-7": "5_a_menor_7_anos",
    "5-10": "5_a_menor_10_anos",
    "7-10": "7_a_menor_10_anos",
}


def normalize_header(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def official_percent(value):
    """Preserva inclusive '-' usado pelo SISVAN para percentual zero."""
    if value is None:
        raise ValueError("percentual vazio em linha municipal")
    text = str(value).strip()
    if text in {"-", "–", "—"} or text.endswith("%"):
        return text
    raise ValueError("percentual SISVAN inesperado: %r" % value)


def numeric_percent(value):
    return helper.parse_percent(value)


def inspect_schema(binary, indicator, phase=None):
    book = load_workbook(io.BytesIO(binary), read_only=True, data_only=True)
    try:
        rows = list(book.active.iter_rows(min_row=1, max_row=15, values_only=True))
    finally:
        book.close()
    titles = {
        normalize_header(value)
        for row in rows for value in row if value is not None
    }
    if indicator.official_title not in titles:
        raise RuntimeError(
            "Resposta nao corresponde a %s" % indicator.official_title
        )
    if phase is not None and phase.key != "crianca":
        phase_title = "Fase da Vida: " + phase.official_label
        if phase_title not in titles:
            raise RuntimeError(
                "Resposta nao corresponde a fase %s" % phase.official_label
            )
    header = None
    for row in rows:
        normalized = [normalize_header(value) for value in row]
        if all(item in normalized for item in BASE_COLUMNS + ("Total",)):
            header = normalized
            break
    if header is None:
        raise RuntimeError("Cabecalho oficial do SISVAN nao reconhecido")
    base_positions = [header.index(item) for item in BASE_COLUMNS]
    if base_positions != list(range(base_positions[0], base_positions[0] + 5)):
        raise RuntimeError("Colunas territoriais mudaram no XLSX do SISVAN")
    total_position = header.index("Total", base_positions[-1] + 1)
    categories = tuple(
        value for value in header[base_positions[-1] + 1:total_position] if value
    )
    if categories != indicator.categories:
        raise RuntimeError(
            "Categorias oficiais inesperadas para %s: %r"
            % (indicator.key, categories)
        )
    columns = list(BASE_COLUMNS)
    for category in categories:
        columns.extend((category + " - Quantidade", category + " - %"))
    columns.append("Total")
    return Schema(categories=categories, columns=tuple(columns))


def resolve_counts(values, percentages, total_value, uf, code):
    totals = helper.count_candidates(total_value)
    if totals == [0]:
        counts = tuple(helper.parse_count(value) for value in values)
        if any(counts):
            raise RuntimeError("%s/%s: categorias sem denominador" % (uf, code))
        return counts, 0
    solutions = []
    for total in totals:
        for counts in product(*(helper.count_candidates(value) for value in values)):
            if sum(counts) != total:
                continue
            if all(
                abs(value / total * 100 - pct) <= 0.011
                for value, pct in zip(counts, percentages)
            ):
                solutions.append((counts, total))
    if not solutions:
        raise RuntimeError("%s/%s: escala das contagens irresolvivel" % (uf, code))
    return min(solutions, key=lambda item: item[1])


def parse_export(binary, expected_uf, indicator, phase=None):
    schema = inspect_schema(binary, indicator, phase)
    width = 5 + 2 * len(schema.categories) + 1
    book = load_workbook(io.BytesIO(binary), read_only=True, data_only=True)
    rows, seen = [], set()
    try:
        for source in book.active.iter_rows(values_only=True):
            values = list(source) + [None] * max(0, width - len(source))
            code = helper.municipal_code(values[3])
            uf = normalize_header(values[2])
            if code is None or uf != expected_uf:
                continue
            if code in seen:
                raise RuntimeError("Codigo SISVAN duplicado em %s: %s" % (uf, code))
            seen.add(code)
            raw_counts = [values[5 + 2 * index] for index in range(len(schema.categories))]
            official_percentages = [
                official_percent(values[6 + 2 * index])
                for index in range(len(schema.categories))
            ]
            row = {
                "Região": normalize_header(values[0]),
                "Código UF": str(int(values[1])).zfill(2),
                "UF": uf,
                "Código IBGE": code,
                "Município": normalize_header(values[4]),
                "Total": values[width - 1],
            }
            for category, count, percentage in zip(
                schema.categories, raw_counts, official_percentages,
            ):
                row[category + " - Quantidade"] = count
                row[category + " - %"] = percentage
            rows.append(row)
    finally:
        book.close()
    if not rows:
        raise RuntimeError("Nenhuma linha municipal encontrada para " + expected_uf)
    return rows, schema


def validate(rows, schema):
    seen, zeros = set(), []
    for row in rows:
        code = str(row["Código IBGE"])
        if not re.fullmatch(r"\d{6}", code) or code in seen:
            raise RuntimeError("Codigo SISVAN invalido ou duplicado: " + code)
        seen.add(code)
        counts = [float(row[column]) for column in schema.count_columns]
        percentages = [numeric_percent(row[column]) for column in schema.percent_columns]
        total = float(row["Total"])
        if any(not math.isfinite(value) or value < 0 for value in counts + [total]):
            raise RuntimeError("Contagem negativa ou nao finita em " + code)
        if total == 0:
            if any(counts) or any(percentages):
                raise RuntimeError("Linha zero inconsistente em " + code)
            zeros.append(row)
            continue
        if abs(sum(percentages) - 100) > 0.10:
            raise RuntimeError("Percentuais nao somam 100 em " + code)
        # Escalas numéricas do exportador são interpretadas somente na análise.
        # A coleta preserva os valores das células, inclusive números decimais.
    return {"total": len(rows), "zeros": zeros}


def atomic_write_bytes(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(content)
    temporary.replace(path)


def write_csv(path, rows, columns, lineterminator="\r\n"):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator=lineterminator)
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def sha256(content):
    return hashlib.sha256(content).hexdigest()


def portable_path(path):
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(path.resolve())


class Manifest:
    def __init__(self, path):
        self.path = path
        self.rows = {}
        if not path.exists():
            return
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            if tuple(reader.fieldnames or ()) != MANIFEST_COLUMNS:
                raise RuntimeError("Esquema inesperado no manifesto: %s" % path)
            for row in reader:
                self.rows[row["id_coleta"]] = row

    def record(self, row, preserve_timestamp=False):
        previous = self.rows.get(row["id_coleta"])
        if preserve_timestamp and previous:
            row["data_hora_coleta"] = previous["data_hora_coleta"]
        self.rows[row["id_coleta"]] = row

    def write(self):
        ordered = sorted(
            self.rows.values(),
            key=lambda item: (
                item["ano_inicio"], item["indice_antropometrico"],
                item["faixa_etaria"], item["arquivo_local"],
            ),
        )
        write_csv(self.path, ordered, MANIFEST_COLUMNS, lineterminator="\n")


def parse_list(value):
    return [item.strip() for item in (value or "").split(",") if item.strip()]


def canonical_age(value):
    key = AGE_ALIASES.get(value, value)
    if key not in AGE_RANGES:
        raise ValueError("faixa etaria invalida: %s" % value)
    return key


def indicator_for(phase_key, indicator_key, age_range=None):
    if phase_key not in PHASES:
        raise ValueError("fase da vida invalida: %s" % phase_key)
    if indicator_key not in PHASE_INDICES[phase_key]:
        raise ValueError(
            "indice %s nao esta disponivel para %s"
            % (indicator_key, phase_key)
        )
    variant = "todos"
    if phase_key == "crianca" and indicator_key == "imc_por_idade":
        if age_range is None:
            raise ValueError("IMC infantil exige faixa etaria")
        variant = "menor_5" if age_range.end_month <= 60 else "5_a_10"
    return INDICATOR_VARIANTS[(phase_key, indicator_key, variant)]


def make_query(phase_key, indicator_key, age_key, year):
    phase = PHASES[phase_key]
    if phase_key == "crianca":
        if not age_key:
            raise ValueError("consulta infantil exige faixa etaria")
        age_range = AGE_RANGES[canonical_age(age_key)]
    else:
        age_range = PHASE_AGE_RANGES[phase_key]
    indicator = indicator_for(phase_key, indicator_key, age_range)
    return Query(phase, indicator, age_range, year)


def population_queries(year, include_pregnant=False):
    plan = [
        ("crianca", "imc_por_idade", "0_a_menor_5_anos"),
        ("crianca", "imc_por_idade", "5_a_menor_10_anos"),
        ("adolescente", "imc_por_idade", None),
        ("adulto", "imc", None),
        ("idoso", "imc", None),
    ]
    if include_pregnant:
        plan.append(("gestante", "imc_por_semana_gestacional", None))
    return [make_query(phase, index, age, year) for phase, index, age in plan]


def validate_nonoverlapping_ranges(queries):
    grouped = {}
    for query in queries:
        grouped.setdefault(
            (query.phase.key, query.indicator.key), [],
        ).append(query.age_range)
    for (phase, index), ranges in grouped.items():
        comparable = [
            item for item in ranges
            if item.start_month is not None and item.end_month is not None
        ]
        for position, current in enumerate(comparable):
            for other in comparable[position + 1:]:
                if (
                    current.start_month < other.end_month
                    and other.start_month < current.end_month
                ):
                    raise RuntimeError(
                        "faixas sobrepostas nao podem ser somadas em %s/%s: "
                        "%s e %s"
                        % (
                            phase, index, current.official_label,
                            other.official_label,
                        )
                    )


def validate_population_queries(queries):
    expected = {"crianca", "adolescente", "adulto", "idoso"}
    nutritional = [
        item for item in queries
        if item.phase.key != "gestante"
        and item.indicator.key in {"imc_por_idade", "imc"}
    ]
    phases = {item.phase.key for item in nutritional}
    if phases != expected:
        raise RuntimeError(
            "populacao geral exige crianca, adolescente, adulto e idoso; "
            "fases encontradas: %s" % ", ".join(sorted(phases))
        )
    children = [item for item in nutritional if item.phase.key == "crianca"]
    validate_nonoverlapping_ranges(children)
    coverage = sorted(
        (item.age_range.start_month, item.age_range.end_month)
        for item in children
    )
    if coverage != [(0, 60), (60, 120)]:
        raise RuntimeError(
            "populacao geral exige as faixas infantis 0 a < 5 e 5 a < 10"
        )


def load_config(path):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("Nao foi possivel carregar %s: %s" % (path, exc)) from exc
    if not isinstance(data.get("consultas"), list) or not data["consultas"]:
        raise RuntimeError("A configuracao deve possuir uma lista 'consultas'")
    return data


def resolve_queries(args):
    config = load_config(args.config)
    year = args.year if args.year is not None else int(config.get("ano", 2025))
    if getattr(args, "populacao_geral", False):
        return population_queries(
            year, include_pregnant=getattr(args, "incluir_gestantes", False),
        )
    configured = []
    for item in config["consultas"]:
        phase_key = item.get("fase", "crianca")
        if phase_key not in PHASES:
            raise RuntimeError("fase invalida na configuracao: %r" % phase_key)
        indicator_key = item.get("indice")
        if indicator_key not in PHASE_INDICES[phase_key]:
            raise RuntimeError(
                "indice invalido para %s na configuracao: %r"
                % (phase_key, indicator_key)
            )
        if phase_key == "crianca":
            ages = item.get("faixas_etarias")
            if not isinstance(ages, list) or not ages:
                raise RuntimeError("consulta infantil sem faixas_etarias")
            for age in ages:
                configured.append(
                    (phase_key, indicator_key, canonical_age(str(age)))
                )
        else:
            configured.append((phase_key, indicator_key, None))
    cli_phases = parse_list(getattr(args, "fases", None))
    cli_indicators = parse_list(args.indices)
    if getattr(args, "todas_idades_infantis", False):
        cli_ages = ["0_a_menor_5_anos", "5_a_menor_10_anos"]
    elif getattr(args, "todas_faixas", False):
        cli_ages = list(AGE_RANGES)
    else:
        cli_ages = [
            canonical_age(item) for item in parse_list(args.faixas_etarias)
        ]
    if cli_phases or cli_indicators or cli_ages:
        phases = cli_phases or list(dict.fromkeys(item[0] for item in configured))
        invalid_phases = [item for item in phases if item not in PHASES]
        if invalid_phases:
            raise RuntimeError("fases invalidas: %s" % ", ".join(invalid_phases))
        replacement = []
        for phase_key in phases:
            available = PHASE_INDICES[phase_key]
            if cli_indicators:
                invalid = [item for item in cli_indicators if item not in available]
                if invalid:
                    raise RuntimeError(
                        "indices indisponiveis para %s: %s"
                        % (phase_key, ", ".join(invalid))
                    )
                indices = cli_indicators
            else:
                indices = list(dict.fromkeys(
                    item[1] for item in configured if item[0] == phase_key
                )) or list(available)
            if phase_key == "crianca":
                ages = cli_ages or list(dict.fromkeys(
                    item[2] for item in configured if item[0] == "crianca"
                ))
                if not ages:
                    ages = ["0_a_menor_5_anos"]
                replacement.extend(
                    (phase_key, index, age)
                    for index, age in product(indices, ages)
                )
            else:
                replacement.extend((phase_key, index, None) for index in indices)
        configured = replacement
    if getattr(args, "incluir_gestantes", False):
        configured.append(("gestante", "imc_por_semana_gestacional", None))
    unique = []
    for item in configured:
        if item not in unique:
            unique.append(item)
    return [make_query(phase, index, age, year) for phase, index, age in unique]


def selected_states(value):
    selected = {item.upper() for item in parse_list(value)} if value else None
    states = [item for item in UF_CODES if not selected or item[0] in selected]
    if selected and {item[0] for item in states} != selected:
        invalid = sorted(selected - {item[0] for item in states})
        raise RuntimeError("UF invalida: " + ", ".join(invalid))
    return states


def raw_path(args, query, uf):
    if query.phase.key == "crianca":
        root = args.raw_dir / query.indicator.key
    else:
        root = args.raw_dir / query.phase.key / query.indicator.key
    return (
        root / query.age_range.key
        / str(query.year) / "ufs" / (uf + ".xlsx")
    )


def output_path(args, query, states, query_count):
    if args.output:
        if query_count != 1:
            raise RuntimeError("--output so pode ser usado com uma unica consulta")
        return args.output
    suffix = ""
    if len(states) != len(UF_CODES):
        suffix = "_ufs_" + "-".join(item[0] for item in states)
    name = "sisvan_municipios_%s_%s_%s_%s%s.csv" % (
        query.phase.key, query.indicator.key, query.age_range.key,
        query.year, suffix,
    )
    if query.phase.key == "crianca":
        name = "sisvan_municipios_%s_%s_%s%s.csv" % (
            query.indicator.key, query.age_range.key, query.year, suffix,
        )
        return args.output_dir / query.indicator.key / name
    return args.output_dir / "consultas" / query.phase.key / query.indicator.key / name


def metadata_path(output):
    return output.with_suffix(".metadados.json")


def combined_output_path(args, queries, states):
    if args.arquivo_unico_output:
        return args.arquivo_unico_output
    years = {query.year for query in queries}
    if len(years) != 1:
        raise RuntimeError("O arquivo unico exige consultas do mesmo ano")
    suffix = ""
    if len(states) != len(UF_CODES):
        suffix = "_ufs_" + "-".join(item[0] for item in states)
    name = "sisvan_municipios_consultas_combinadas_%s%s.csv" % (
        years.pop(), suffix,
    )
    return args.output_dir / name


def write_combined(path, products, states):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    written = 0
    with temporary.open("w", newline="", encoding="utf-8-sig") as target:
        writer = csv.DictWriter(target, fieldnames=COMBINED_COLUMNS)
        writer.writeheader()
        for product_item in products:
            query = product_item["query"]
            schema = product_item["schema"]
            with product_item["output"].open(
                newline="", encoding="utf-8-sig",
            ) as source:
                reader = csv.DictReader(source)
                if tuple(reader.fieldnames or ()) != schema.columns:
                    raise RuntimeError(
                        "Esquema inesperado no consolidado: %s"
                        % product_item["output"]
                    )
                for source_row in reader:
                    common = {
                        "Fase da vida": query.phase.official_label,
                        "Código da fase SISVAN": query.phase.code,
                        "Índice antropométrico": query.indicator.official_title,
                        "Código do índice SISVAN": query.indicator.code,
                        "Faixa etária": query.age_range.official_label,
                        "Código da faixa etária": query.age_range.key,
                        "Idade inicial SISVAN": query.age_range.start,
                        "Idade final SISVAN": query.age_range.end,
                        "Ano": query.year,
                        **{column: source_row[column] for column in BASE_COLUMNS},
                        "Total": source_row["Total"],
                    }
                    for category in schema.categories:
                        writer.writerow({
                            **common,
                            "Classificação nutricional": category,
                            "Quantidade": source_row[category + " - Quantidade"],
                            "Percentual": source_row[category + " - %"],
                        })
                        written += 1
    temporary.replace(path)
    metadata = {
        "fonte": helper.PORTAL,
        "arquivo": portable_path(path),
        "formato": "longo",
        "linhas": written,
        "ufs": [item[0] for item in states],
        "consultas": [
            {
                "fase": item["query"].phase.key,
                "fase_oficial": item["query"].phase.official_label,
                "indice": item["query"].indicator.key,
                "indice_oficial": item["query"].indicator.official_title,
                "faixa_etaria": item["query"].age_range.key,
                "faixa_etaria_descricao": item["query"].age_range.official_label,
                "ano": item["query"].year,
                "arquivo_origem": portable_path(item["output"]),
            }
            for item in products
        ],
        "gerado_em": datetime.now().astimezone().isoformat(timespec="seconds"),
        "observacao": (
            "As consultas foram concatenadas, nao somadas. Faixas etarias "
            "sobrepostas podem conter as mesmas pessoas. Este e um produto "
            "tratado; os XLSX oficiais permanecem na camada bruta."
        ),
    }
    meta_path = metadata_path(path)
    meta_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return written


def write_metadata(path, query, output, stats, states, schema, originals=None):
    data = {
        "fonte": helper.PORTAL,
        "endpoint": helper.ENDPOINT,
        "arquivo": portable_path(output),
        "fase": query.phase.key,
        "fase_oficial": query.phase.official_label,
        "codigo_fase_sisvan": query.phase.code,
        "indice": query.indicator.key,
        "indice_oficial": query.indicator.official_title,
        "codigo_indice_sisvan": query.indicator.code,
        "faixa_etaria": query.age_range.key,
        "faixa_etaria_descricao": query.age_range.official_label,
        "nu_idade_inicio": query.age_range.start,
        "nu_idade_fim": query.age_range.end,
        "ano": query.year,
        "ufs": [item[0] for item in states],
        "colunas": list(schema.columns),
        "linhas": stats["total"],
        "linhas_total_zero": len(stats["zeros"]),
        "versao_coletor": COLLECTOR_VERSION,
        "sha256_csv": sha256(output.read_bytes()),
        "xlsx_originais": originals or [],
        "contagens": "valores das celulas preservados; sem normalizacao de escala",
        "indicadores_derivados": [],
        "gerado_em": datetime.now().astimezone().isoformat(timespec="seconds"),
        "observacao": (
            "CSV convertido dos XLSX oficiais por UF. Cabecalhos multinivel "
            "sao achatados em categoria - Quantidade e categoria - %. "
            "Valores das celulas nao sao corrigidos ou recalculados. "
            "Os XLSX preservados sao os arquivos originais exatos."
        ),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    temporary.replace(path)


def manifest_row(query, uf, raw, payload, content, row_count, timestamp):
    if query.phase.key == "crianca":
        identifier = "sisvan-%s-%s-%s-%s" % (
            query.year, query.indicator.key, query.age_range.key, uf,
        )
        age_label = query.age_range.official_label
    else:
        identifier = "sisvan-%s-%s-%s-%s-%s" % (
            query.year, query.phase.key, query.indicator.key,
            query.age_range.key, uf,
        )
        age_label = "%s | %s" % (
            query.phase.official_label, query.age_range.official_label,
        )
    return {
        "id_coleta": identifier,
        "fonte": helper.PORTAL,
        "arquivo_local": portable_path(raw),
        "nome_original": "",
        "indice_antropometrico": query.indicator.official_title,
        "faixa_etaria": age_label,
        "ano_inicio": str(query.year),
        "ano_fim": str(query.year),
        "abrangencia": "Municipios de " + uf,
        "filtros": json.dumps(payload, ensure_ascii=False, sort_keys=True),
        "data_hora_coleta": timestamp,
        "quantidade_registros": str(row_count),
        "hash_arquivo": sha256(content),
        "status": "validado",
        "versao_coletor": COLLECTOR_VERSION,
        "observacoes": "XLSX oficial preservado sem alteracao",
    }


def collect_query(args, query, states, session, limiter, portal_started, manifest, query_count):
    label = "%s | %s | %s | %s" % (
        query.phase.official_label, query.indicator.official_title,
        query.age_range.official_label, query.year,
    )
    print("\nCONSULTA:", label)
    all_rows, expected_schema, originals = [], None, []
    for position, (uf, uf_code) in enumerate(states, 1):
        print("[%02d/%02d] %s" % (position, len(states), uf))
        raw = raw_path(args, query, uf)
        payload_options = {
            "life_cycle": query.phase.code,
            "pregnancy_age": "99",
        }
        if query.indicator.code_field == "nu_indice_ado":
            payload_options["adolescent_index_code"] = query.indicator.code
        payload = helper.report_payload(
            query.year, uf_code,
            query.indicator.code if query.indicator.code_field == "nu_indice_cri" else "4",
            query.age_range.start or "0", query.age_range.end or "5",
            **payload_options,
        )
        reused = raw.exists() and not args.force
        if reused:
            content = raw.read_bytes()
            print("  XLSX oficial reutilizado:", raw)
        else:
            if not portal_started[0]:
                helper.start_portal(
                    session, (args.connect_timeout, args.read_timeout), limiter,
                )
                portal_started[0] = True
            content = helper.fetch_xlsx(
                session, args, limiter, uf, uf_code, payload=payload,
                debug_name="%s_%s_%s_%s" % (
                    query.phase.key, query.indicator.key,
                    query.age_range.key, uf,
                ),
            )
            atomic_write_bytes(raw, content)
            print("  XLSX oficial salvo:", raw)
        rows, schema = parse_export(content, uf, query.indicator, query.phase)
        validate(rows, schema)
        if expected_schema is None:
            expected_schema = schema
        elif schema != expected_schema:
            raise RuntimeError("Esquema divergente entre UFs na consulta " + label)
        all_rows.extend(rows)
        entry = manifest_row(
            query, uf, raw, payload, content, len(rows),
            datetime.now().astimezone().isoformat(timespec="seconds"),
        )
        previous = manifest.rows.get(entry["id_coleta"])
        if (
            reused and previous
            and previous["hash_arquivo"] != entry["hash_arquivo"]
        ):
            raise RuntimeError(
                "Arquivo bruto diverge do manifesto: %s" % raw
            )
        manifest.record(entry, preserve_timestamp=reused)
        originals.append({key: entry[key] for key in (
            "arquivo_local", "hash_arquivo", "data_hora_coleta", "filtros",
            "quantidade_registros",
        )})
        manifest.write()
        print("  municipios:", len(rows))
    all_rows.sort(key=lambda row: int(row["Código IBGE"]))
    stats = validate(all_rows, expected_schema)
    output = output_path(args, query, states, query_count)
    write_csv(output, all_rows, expected_schema.columns)
    write_metadata(
        metadata_path(output), query, output, stats, states, expected_schema, originals,
    )
    print("  CSV consolidado:", output)
    print("  linhas:", stats["total"], "| Total=0:", len(stats["zeros"]))
    return {
        "query": query, "output": output, "schema": expected_schema,
        "stats": stats,
    }


def read_product_rows(product_item):
    with product_item["output"].open(
        newline="", encoding="utf-8-sig",
    ) as source:
        reader = csv.DictReader(source)
        if tuple(reader.fieldnames or ()) != product_item["schema"].columns:
            raise RuntimeError(
                "Esquema inesperado no consolidado: %s"
                % product_item["output"]
            )
        rows = list(reader)
    # Apenas produtos derivados explicitamente solicitados usam contagens
    # interpretadas. O CSV por consulta nunca é reescrito por esta operação.
    schema = product_item["schema"]
    for row in rows:
        counts, total = resolve_counts(
            [float(row[c]) for c in schema.count_columns],
            [numeric_percent(row[c]) for c in schema.percent_columns],
            float(row["Total"]), row["UF"], row["Código IBGE"],
        )
        row.update(zip(schema.count_columns, counts))
        row["Total"] = total
    return rows


def derived_percent(quantity, total):
    return round(quantity / total * 100, 2) if total else 0.0


def partial_suffix(states):
    if len(states) == len(UF_CODES):
        return ""
    return "_ufs_" + "-".join(item[0] for item in states)


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def product_sources(products):
    return [
        {
            "fase": item["query"].phase.key,
            "indice": item["query"].indicator.key,
            "faixa_etaria": item["query"].age_range.key,
            "arquivo": portable_path(item["output"]),
        }
        for item in products
    ]


def compatible_product_rows(products):
    """Le produtos e garante a mesma malha municipal e identificacao."""
    loaded = [(item, read_product_rows(item)) for item in products]
    expected_codes = None
    identities = {}
    for item, rows in loaded:
        codes = {row["Código IBGE"] for row in rows}
        if expected_codes is None:
            expected_codes = codes
        elif codes != expected_codes:
            raise RuntimeError(
                "Cobertura municipal divergente entre %s e as demais fontes"
                % item["output"]
            )
        for row in rows:
            code = row["Código IBGE"]
            identity = tuple(row[column] for column in BASE_COLUMNS)
            previous = identities.setdefault(code, identity)
            if previous != identity:
                raise RuntimeError(
                    "Identificacao territorial divergente para %s" % code
                )
    return loaded, identities


def summed_output_path(args, products, states, population_phase=False):
    query = products[0]["query"]
    if population_phase:
        name = "%s_categorias_oficiais_%s%s.csv" % (
            query.phase.key, query.year, partial_suffix(states),
        )
        return args.output_dir / "por_fase" / name
    name = "sisvan_municipios_%s_%s_faixas_somadas_%s%s.csv" % (
        query.phase.key, query.indicator.key, query.year,
        partial_suffix(states),
    )
    return (
        args.output_dir / "faixas_somadas" / query.phase.key
        / query.indicator.key / name
    )


def write_summed_product(args, products, states, population_phase=False):
    queries = [item["query"] for item in products]
    validate_nonoverlapping_ranges(queries)
    keys = {
        (item.phase.key, item.indicator.key, item.year) for item in queries
    }
    if len(keys) != 1:
        raise RuntimeError("a soma exige mesma fase, indice e ano")
    loaded, identities = compatible_product_rows(products)
    categories = []
    for item in products:
        for category in item["schema"].categories:
            if category not in categories:
                categories.append(category)
    values = {
        code: {"Total": 0, **{category: 0 for category in categories}}
        for code in identities
    }
    for item, rows in loaded:
        for row in rows:
            target = values[row["Código IBGE"]]
            target["Total"] += int(row["Total"])
            for category in item["schema"].categories:
                target[category] += int(row[category + " - Quantidade"])
    query = queries[0]
    age_labels = " + ".join(item.age_range.official_label for item in queries)
    age_keys = "+".join(item.age_range.key for item in queries)
    output_rows = []
    for code in sorted(values, key=int):
        total = values[code]["Total"]
        common = {
            "Fase da vida": query.phase.official_label,
            "Código da fase SISVAN": query.phase.code,
            "Índice antropométrico": query.indicator.official_title,
            "Código do índice SISVAN": query.indicator.code,
            "Faixas etárias participantes": age_labels,
            "Códigos das faixas etárias": age_keys,
            "Ano": query.year,
            **dict(zip(BASE_COLUMNS, identities[code])),
            "Total": total,
        }
        for category in categories:
            quantity = values[code][category]
            output_rows.append({
                **common,
                "Classificação nutricional oficial": category,
                "Quantidade": quantity,
                "Percentual recalculado": derived_percent(quantity, total),
            })
    output = summed_output_path(args, products, states, population_phase)
    write_csv(output, output_rows, SUMMED_COLUMNS)
    write_json(metadata_path(output), {
        "fonte": helper.PORTAL,
        "arquivo": portable_path(output),
        "tipo": "produto derivado com faixas etarias somadas",
        "fase": query.phase.key,
        "indice": query.indicator.key,
        "ano": query.year,
        "faixas_etarias": [item.age_range.key for item in queries],
        "sobreposicao_validada": True,
        "percentuais": "recalculados como quantidade / total combinado * 100",
        "fontes": product_sources(products),
        "linhas": len(output_rows),
        "gerado_em": datetime.now().astimezone().isoformat(timespec="seconds"),
        "observacao": (
            "As classificacoes mantem exatamente a grafia oficial, mas este "
            "CSV e derivado; os XLSX oficiais permanecem inalterados."
        ),
    })
    return output


def load_harmonization(path):
    if path is None:
        raise RuntimeError(
            "--harmonizar e --populacao-geral exigem "
            "--harmonization-config CAMINHO_JSON; "
            "o coletor nao inclui um dicionario de harmonizacao padrao"
        )
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            "Nao foi possivel carregar o dicionario %s: %s" % (path, exc)
        ) from exc
    if not data.get("versao") or not isinstance(data.get("mapeamentos"), list):
        raise RuntimeError("dicionario de harmonizacao invalido: %s" % path)
    lookup = {}
    allowed_groups = {"deficit", "adequado", "risco_excesso", "excesso"}
    allowed_components = {
        "magreza_acentuada", "magreza", "baixo_peso",
        "baixo_peso_gestacional",
    }
    for item in data["mapeamentos"]:
        try:
            key = (item["fase"], item["indice"], item["categoria_oficial"])
            group = item["grupo_harmonizado"]
        except KeyError as exc:
            raise RuntimeError(
                "campo ausente no dicionario de harmonizacao: %s" % exc
            ) from exc
        if item["fase"] not in PHASES or group not in allowed_groups:
            raise RuntimeError("mapeamento de harmonizacao invalido: %r" % (item,))
        component = item.get("componente_deficit")
        if component and component not in allowed_components:
            raise RuntimeError("componente de deficit invalido: %r" % component)
        if (group == "deficit") != bool(component):
            raise RuntimeError(
                "grupo deficit exige componente, e componente exige grupo deficit: %r"
                % (item,)
            )
        if key in lookup:
            raise RuntimeError("mapeamento duplicado: %r" % (key,))
        lookup[key] = item
    return data, lookup


def nutritional_products(products):
    return [
        item for item in products
        if item["query"].indicator.key in {
            "imc_por_idade", "imc", "imc_por_semana_gestacional",
        }
    ]


def build_phase_facts(products, mapping):
    if not products:
        raise RuntimeError("nenhum produto para harmonizar")
    phase_keys = {item["query"].phase.key for item in products}
    years = {item["query"].year for item in products}
    if len(phase_keys) != 1 or len(years) != 1:
        raise RuntimeError("harmonizacao por fase exige uma fase e um ano")
    phase_key = next(iter(phase_keys))
    if phase_key == "gestante":
        raise RuntimeError("gestantes usam produto separado")
    validate_nonoverlapping_ranges([item["query"] for item in products])
    loaded, identities = compatible_product_rows(products)
    facts = {}
    for code, identity in identities.items():
        facts[code] = {
            "identity": identity,
            "total": 0,
            "magreza_acentuada": 0,
            "magreza": 0,
            "baixo_peso": 0,
            "adequado": 0,
            "risco_excesso": 0,
            "excesso": 0,
            "deficit": 0,
            "denom_crianca_adolescente": 0,
            "denom_adulto_idoso": 0,
            "denom_risco": 0,
            "aplica_magreza_acentuada": False,
            "aplica_magreza": False,
            "aplica_baixo_peso": False,
            "aplica_risco": False,
        }
    for item, rows in loaded:
        query = item["query"]
        category_maps = {}
        for category in item["schema"].categories:
            key = (phase_key, query.indicator.key, category)
            if key not in mapping:
                raise RuntimeError(
                    "categoria oficial sem harmonizacao aprovada: %r" % (key,)
                )
            category_maps[category] = mapping[key]
        components = {
            value.get("componente_deficit")
            for value in category_maps.values()
            if value.get("componente_deficit")
        }
        has_risk = any(
            value["grupo_harmonizado"] == "risco_excesso"
            for value in category_maps.values()
        )
        for row in rows:
            fact = facts[row["Código IBGE"]]
            total = int(row["Total"])
            fact["total"] += total
            if phase_key in {"crianca", "adolescente"}:
                fact["denom_crianca_adolescente"] += total
            if phase_key in {"adulto", "idoso"}:
                fact["denom_adulto_idoso"] += total
            if has_risk:
                fact["denom_risco"] += total
                fact["aplica_risco"] = True
            for component in components:
                fact["aplica_" + component] = True
            for category, item_map in category_maps.items():
                quantity = int(row[category + " - Quantidade"])
                group = item_map["grupo_harmonizado"]
                fact[group] += quantity
                component = item_map.get("componente_deficit")
                if component:
                    fact[component] += quantity

    for code, fact in facts.items():
        deficit_components = (
            fact["magreza_acentuada"] + fact["magreza"] + fact["baixo_peso"]
        )
        if fact["deficit"] != deficit_components:
            raise RuntimeError(
                "componentes do deficit divergem do grupo em %s/%s"
                % (phase_key, code)
            )
        fact["deficit"] = deficit_components
        if (
            deficit_components + fact["adequado"] + fact["risco_excesso"]
            + fact["excesso"] != fact["total"]
        ):
            raise RuntimeError(
                "grupos harmonizados nao formam particao em %s/%s"
                % (phase_key, code)
            )
    return phase_key, next(iter(years)), facts


def harmonized_row(label, age_labels, year, fact):
    ca_total = fact["denom_crianca_adolescente"]
    ai_total = fact["denom_adulto_idoso"]
    risk_total = fact["denom_risco"]
    total = fact["total"]

    def applicable(name, denominator):
        if not fact["aplica_" + name]:
            return "", ""
        return fact[name], derived_percent(fact[name], denominator)

    severe_q, severe_p = applicable("magreza_acentuada", ca_total)
    thin_q, thin_p = applicable("magreza", ca_total)
    low_q, low_p = applicable("baixo_peso", ai_total)
    if fact["aplica_risco"]:
        risk_q = fact["risco_excesso"]
        risk_p = derived_percent(risk_q, risk_total)
    else:
        risk_q, risk_p = "", ""
    return {
        "Fase da vida": label,
        "Faixas etárias participantes": age_labels,
        "Ano": year,
        **dict(zip(BASE_COLUMNS, fact["identity"])),
        "Magreza acentuada - Quantidade": severe_q,
        "Magreza acentuada - % (crianças e adolescentes)": severe_p,
        "Magreza - Quantidade": thin_q,
        "Magreza - % (crianças e adolescentes)": thin_p,
        "Baixo peso - Quantidade": low_q,
        "Baixo peso - % (adultos e idosos)": low_p,
        "Déficit nutricional total - Quantidade": fact["deficit"],
        "Déficit nutricional total - %": derived_percent(fact["deficit"], total),
        "Estado nutricional adequado - Quantidade": fact["adequado"],
        "Estado nutricional adequado - %": derived_percent(fact["adequado"], total),
        "Risco para excesso de peso - Quantidade": risk_q,
        "Risco para excesso de peso - % (faixas aplicáveis)": risk_p,
        "Excesso de peso - Quantidade": fact["excesso"],
        "Excesso de peso - %": derived_percent(fact["excesso"], total),
        "Total crianças e adolescentes (denominador)": (
            ca_total if (
                fact["aplica_magreza_acentuada"] or fact["aplica_magreza"]
            ) else ""
        ),
        "Total adultos e idosos (denominador)": (
            ai_total if fact["aplica_baixo_peso"] else ""
        ),
        "Total com risco de sobrepeso aplicável (denominador)": (
            risk_total if fact["aplica_risco"] else ""
        ),
        "Total": total,
    }


def write_phase_harmonized(args, products, states, mapping_data, mapping):
    phase_key, year, facts = build_phase_facts(products, mapping)
    phase = PHASES[phase_key]
    age_labels = " + ".join(
        item["query"].age_range.official_label for item in products
    )
    rows = [
        harmonized_row(phase.official_label, age_labels, year, facts[code])
        for code in sorted(facts, key=int)
    ]
    name = "%s_harmonizado_%s%s.csv" % (
        phase_key, year, partial_suffix(states),
    )
    output = args.output_dir / "harmonizados" / name
    write_csv(output, rows, HARMONIZED_COLUMNS)
    write_json(metadata_path(output), {
        "fonte": helper.PORTAL,
        "arquivo": portable_path(output),
        "tipo": "produto derivado harmonizado por fase",
        "fase": phase_key,
        "ano": year,
        "dicionario_harmonizacao": portable_path(args.harmonization_config),
        "dicionario_harmonizacao_sha256": sha256(
            args.harmonization_config.read_bytes()
        ),
        "versao_harmonizacao": mapping_data["versao"],
        "denominadores": {
            "magreza_acentuada_e_magreza": "total da fase aplicavel",
            "baixo_peso": "total da fase aplicavel",
            "risco_excesso": "somente faixas com a categoria oficial",
            "demais_grupos": "total combinado da fase",
        },
        "fontes": product_sources(products),
        "linhas": len(rows),
        "gerado_em": datetime.now().astimezone().isoformat(timespec="seconds"),
    })
    return {"phase": phase_key, "year": year, "facts": facts, "output": output}


def combine_general_facts(phase_results):
    by_phase = {item["phase"]: item for item in phase_results}
    expected = {"crianca", "adolescente", "adulto", "idoso"}
    if set(by_phase) != expected:
        raise RuntimeError(
            "base geral exige harmonizados de: %s" % ", ".join(sorted(expected))
        )
    years = {item["year"] for item in phase_results}
    if len(years) != 1:
        raise RuntimeError("base geral exige o mesmo ano em todas as fases")
    code_sets = {tuple(sorted(item["facts"])) for item in phase_results}
    if len(code_sets) != 1:
        raise RuntimeError("cobertura municipal divergente entre fases")
    facts = {}
    for code in next(iter(code_sets)):
        sources = [by_phase[phase]["facts"][code] for phase in sorted(expected)]
        identities = {item["identity"] for item in sources}
        if len(identities) != 1:
            raise RuntimeError("identificacao territorial divergente em " + code)
        fact = {
            "identity": next(iter(identities)),
            "total": sum(item["total"] for item in sources),
            "magreza_acentuada": sum(item["magreza_acentuada"] for item in sources),
            "magreza": sum(item["magreza"] for item in sources),
            "baixo_peso": sum(item["baixo_peso"] for item in sources),
            "adequado": sum(item["adequado"] for item in sources),
            "risco_excesso": sum(item["risco_excesso"] for item in sources),
            "excesso": sum(item["excesso"] for item in sources),
            "denom_crianca_adolescente": sum(
                item["denom_crianca_adolescente"] for item in sources
            ),
            "denom_adulto_idoso": sum(
                item["denom_adulto_idoso"] for item in sources
            ),
            "denom_risco": sum(item["denom_risco"] for item in sources),
            "aplica_magreza_acentuada": True,
            "aplica_magreza": True,
            "aplica_baixo_peso": True,
            "aplica_risco": True,
        }
        fact["deficit"] = (
            fact["magreza_acentuada"] + fact["magreza"] + fact["baixo_peso"]
        )
        if (
            fact["deficit"] + fact["adequado"] + fact["risco_excesso"]
            + fact["excesso"] != fact["total"]
        ):
            raise RuntimeError("particao geral inconsistente em " + code)
        facts[code] = fact
    return next(iter(years)), facts


def write_general_population(args, phase_results, states, mapping_data):
    year, facts = combine_general_facts(phase_results)
    rows = [
        harmonized_row(
            "POPULAÇÃO GERAL (SEM GESTANTES)",
            "0 a < 10 + 10 a < 20 + 20 a < 60 + 60 anos ou mais",
            year, facts[code],
        )
        for code in sorted(facts, key=int)
    ]
    name = "estado_nutricional_populacao_geral_%s%s.csv" % (
        year, partial_suffix(states),
    )
    output = args.output_dir / "populacao_geral" / name
    write_csv(output, rows, HARMONIZED_COLUMNS)
    write_json(metadata_path(output), {
        "fonte": helper.PORTAL,
        "arquivo": portable_path(output),
        "tipo": "produto derivado harmonizado da populacao geral",
        "fases_incluidas": ["crianca", "adolescente", "adulto", "idoso"],
        "gestantes_incluidas": False,
        "ano": year,
        "dicionario_harmonizacao": portable_path(args.harmonization_config),
        "dicionario_harmonizacao_sha256": sha256(
            args.harmonization_config.read_bytes()
        ),
        "versao_harmonizacao": mapping_data["versao"],
        "fontes_harmonizadas": [portable_path(item["output"]) for item in phase_results],
        "linhas": len(rows),
        "gerado_em": datetime.now().astimezone().isoformat(timespec="seconds"),
        "limitacoes": [
            "Representa pessoas contabilizadas nas consultas do SISVAN, nao toda a populacao residente.",
            "Uma pessoa que muda de fase durante o periodo anual pode aparecer em mais de uma consulta; unicidade individual nao foi comprovada.",
            "Gestantes sao excluidas para evitar dupla contagem e por classificacao especifica.",
        ],
    })
    return output


def write_pregnant_product(args, product_item, states):
    query = product_item["query"]
    rows = read_product_rows(product_item)
    output_rows = []
    for row in rows:
        total = int(row["Total"])
        quantities = {
            category: int(row[category + " - Quantidade"])
            for category in query.indicator.categories
        }
        excess = quantities["Sobrepeso"] + quantities["Obesidade"]
        output_rows.append({
            "Fase da vida": query.phase.official_label,
            "Ano": query.year,
            **{column: row[column] for column in BASE_COLUMNS},
            "Baixo peso - Quantidade": quantities["Baixo peso"],
            "Baixo peso - %": derived_percent(quantities["Baixo peso"], total),
            "Adequado ou Eutrófico - Quantidade": quantities["Adequado ou Eutrófico"],
            "Adequado ou Eutrófico - %": derived_percent(quantities["Adequado ou Eutrófico"], total),
            "Sobrepeso - Quantidade": quantities["Sobrepeso"],
            "Sobrepeso - %": derived_percent(quantities["Sobrepeso"], total),
            "Obesidade - Quantidade": quantities["Obesidade"],
            "Obesidade - %": derived_percent(quantities["Obesidade"], total),
            "Excesso de peso - Quantidade": excess,
            "Excesso de peso - %": derived_percent(excess, total),
            "Total": total,
        })
    name = "estado_nutricional_gestantes_%s%s.csv" % (
        query.year, partial_suffix(states),
    )
    output = args.output_dir / "gestantes" / name
    write_csv(output, output_rows, PREGNANT_COLUMNS)
    write_json(metadata_path(output), {
        "fonte": helper.PORTAL,
        "arquivo": portable_path(output),
        "tipo": "produto derivado exclusivo de gestantes",
        "incluido_na_populacao_geral": False,
        "fontes": product_sources([product_item]),
        "linhas": len(output_rows),
        "gerado_em": datetime.now().astimezone().isoformat(timespec="seconds"),
    })
    return output




def print_options():
    print("Fases e indices disponíveis:")
    for phase_key, phase in PHASES.items():
        print("  %s (codigo=%s): %s" % (
            phase_key, phase.code, ", ".join(PHASE_INDICES[phase_key]),
        ))
    print("\nFaixas etárias oficiais aceitas pelo formulário infantil:")
    reverse_aliases = {value: key for key, value in AGE_ALIASES.items()}
    for item in AGE_RANGES.values():
        print(
            "  %-27s alias=%-5s parametros=%s:%s  %s"
            % (
                item.key, reverse_aliases[item.key], item.start, item.end,
                item.official_label,
            )
        )


def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Preserva XLSX oficiais e consolida relatorios municipais do SISVAN "
            "para multiplos indices e faixas etarias."
        )
    )
    parser.add_argument(
        "--config", type=Path,
        default=Path("configuracoes/sisvan/coletas.json"),
    )
    parser.add_argument("--year", type=int)
    parser.add_argument(
        "--fases",
        help="Lista: crianca,adolescente,adulto,idoso,gestante",
    )
    parser.add_argument(
        "--indices",
        help=(
            "Lista separada por virgulas: altura_por_idade,peso_por_idade,"
            "imc_por_idade"
        ),
    )
    parser.add_argument(
        "--faixas-etarias",
        help="Lista separada por virgulas; use --listar-opcoes para consultar",
    )
    parser.add_argument(
        "--todas-faixas", action="store_true",
        help="Coleta as nove consultas infantis; nao implica soma",
    )
    parser.add_argument(
        "--todas-idades-infantis", action="store_true",
        help="Seleciona 0 a < 5 e 5 a < 10, sem sobreposicao",
    )
    parser.add_argument(
        "--somar-faixas", action="store_true",
        help="Soma somente faixas selecionadas e mutuamente exclusivas por base",
    )
    parser.add_argument(
        "--harmonizar", action="store_true",
        help="Cria bases harmonizadas de IMC; exige --harmonization-config",
    )
    parser.add_argument(
        "--populacao-geral", action="store_true",
        help="Gera a base geral de criancas, adolescentes, adultos e idosos; exige --harmonization-config",
    )
    parser.add_argument(
        "--incluir-gestantes", action="store_true",
        help="Coleta gestantes em produto separado; nunca entra na base geral",
    )
    parser.add_argument(
        "--arquivo-unico", action="store_true",
        help="Cria tambem um CSV longo reunindo as consultas selecionadas",
    )
    parser.add_argument(
        "--arquivo-unico-output", type=Path,
        help="Caminho opcional do CSV unico; ativa --arquivo-unico",
    )
    parser.add_argument("--raw-dir", type=Path, default=Path("dados/coletas/sisvan/brutos"))
    parser.add_argument(
        "--output-dir", type=Path, default=Path("dados/coletas/sisvan/convertidos"),
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--manifest", type=Path,
        default=Path("dados/coletas/sisvan/manifesto_coletas.csv"),
    )
    parser.add_argument(
        "--harmonization-config", type=Path,
        help="Dicionario JSON fornecido pelo usuario para --harmonizar ou --populacao-geral; sem padrao",
    )
    parser.add_argument("--debug-dir", type=Path, default=Path("dados/coletas/sisvan/debug"))
    parser.add_argument("--delay", type=float, default=1.0)
    parser.add_argument("--connect-timeout", type=float, default=20.0)
    parser.add_argument("--read-timeout", type=float, default=180.0)
    parser.add_argument("--retries", type=int, default=4)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--ufs", help="Lista de UFs separada por virgulas")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--listar-opcoes", action="store_true")
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    if args.listar_opcoes:
        print_options()
        return
    if args.delay < 0 or args.connect_timeout <= 0 or args.read_timeout <= 0:
        parser.error("delay >= 0 e timeouts positivos")
    age_modes = sum(bool(item) for item in (
        args.todas_faixas, args.todas_idades_infantis, args.faixas_etarias,
    ))
    if age_modes > 1:
        parser.error(
            "use apenas uma opcao entre --todas-faixas, "
            "--todas-idades-infantis e --faixas-etarias"
        )
    if args.populacao_geral and any((
        args.fases, args.indices, args.faixas_etarias,
        args.todas_faixas, args.todas_idades_infantis,
    )):
        parser.error(
            "--populacao-geral ja define fases e faixas; nao combine com seletores"
        )
    if args.arquivo_unico_output:
        args.arquivo_unico = True
    try:
        queries = resolve_queries(args)
        states = selected_states(args.ufs)
        if args.somar_faixas or args.harmonizar or args.populacao_geral:
            validate_nonoverlapping_ranges(queries)
        if args.populacao_geral:
            validate_population_queries(queries)
        mapping_bundle = None
        if args.harmonizar or args.populacao_geral:
            mapping_bundle = load_harmonization(args.harmonization_config)
    except (RuntimeError, ValueError) as exc:
        parser.error(str(exc))
    print("Consultas planejadas:")
    for query in queries:
        print(
            "- %s | %s | %s | %s"
            % (
                query.phase.official_label,
                query.indicator.official_title,
                query.age_range.official_label,
                query.year,
            )
        )
    print("UFs:", ", ".join(item[0] for item in states))
    if args.output and len(queries) != 1:
        parser.error("--output so pode ser usado com uma unica consulta")
    if args.arquivo_unico:
        print("Arquivo unico: formato longo, sem somar faixas sobrepostas")
    if args.somar_faixas or args.populacao_geral:
        print("Soma: apenas grupos de faixas validados como nao sobrepostos")
    if args.populacao_geral:
        print("Populacao geral: criancas + adolescentes + adultos + idosos")
        print("Gestantes: excluidas da soma geral")
    if args.dry_run:
        return
    session = helper.new_session(args.retries)
    limiter = helper.Limiter(args.delay)
    manifest = Manifest(args.manifest)
    portal_started = [False]
    products = []
    for query in queries:
        products.append(
            collect_query(
                args, query, states, session, limiter, portal_started,
                manifest, len(queries),
            )
        )
    combined = None
    if args.arquivo_unico:
        combined = combined_output_path(args, queries, states)
        combined_rows = write_combined(combined, products, states)
        print("\nCSV unico:", combined)
        print("Linhas no formato longo:", combined_rows)
    derived = []
    if args.somar_faixas or args.populacao_geral:
        grouped = {}
        for item in products:
            query = item["query"]
            grouped.setdefault(
                (query.phase.key, query.indicator.key, query.year), [],
            ).append(item)
        for group in grouped.values():
            if (
                args.populacao_geral
                and group[0]["query"].phase.key == "gestante"
                and not args.somar_faixas
            ):
                continue
            output = write_summed_product(
                args, group, states,
                population_phase=(
                    args.populacao_geral
                    and group[0]["query"].phase.key != "gestante"
                ),
            )
            derived.append(output)
            print("Base com faixas somadas:", output)
    if args.harmonizar or args.populacao_geral:
        mapping_data, mapping = mapping_bundle
        by_phase = {}
        pregnant = []
        for item in nutritional_products(products):
            if item["query"].phase.key == "gestante":
                pregnant.append(item)
            else:
                by_phase.setdefault(item["query"].phase.key, []).append(item)
        phase_results = []
        for group in by_phase.values():
            result = write_phase_harmonized(
                args, group, states, mapping_data, mapping,
            )
            phase_results.append(result)
            derived.append(result["output"])
            print("Base harmonizada por fase:", result["output"])
        if args.populacao_geral:
            output = write_general_population(
                args, phase_results, states, mapping_data,
            )
            derived.append(output)
            print("Base harmonizada da populacao geral:", output)
        for item in pregnant:
            output = write_pregnant_product(args, item, states)
            derived.append(output)
            print("Base separada de gestantes:", output)
    print("\nCOLETA CONCLUIDA")
    print("Manifesto:", args.manifest)
    for item in products:
        print("CSV:", item["output"])
    if combined:
        print("CSV combinado:", combined)
    for output in derived:
        print("CSV derivado:", output)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nColeta interrompida; arquivos ja validados foram preservados.", file=sys.stderr)
        raise SystemExit(130)
