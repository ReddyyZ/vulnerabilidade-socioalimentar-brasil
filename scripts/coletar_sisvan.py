#!/usr/bin/env python3
"""Coleta reproduzivel de relatorios municipais brutos do SISVAN.

Preserva cada XLSX oficial por UF e produz um CSV consolidado por combinacao
de indice antropometrico, faixa etaria e ano. Os arquivos oficiais nunca sao
sobrescritos sem --force.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from itertools import product
from pathlib import Path

from openpyxl import load_workbook

import coletar_sisvan_derivado as helper


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
COLLECTOR_VERSION = "3.0"


@dataclass(frozen=True)
class Indicator:
    key: str
    code: str
    official_title: str
    categories: tuple[str, ...]


@dataclass(frozen=True)
class AgeRange:
    key: str
    start: str
    end: str
    official_label: str


@dataclass(frozen=True)
class Query:
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


INDICATORS = {
    "imc_por_idade": Indicator(
        key="imc_por_idade",
        code="4",
        official_title="IMC X IDADE",
        categories=(
            "Magreza acentuada", "Magreza", "Eutrofia",
            "Risco de sobrepeso", "Sobrepeso", "Obesidade",
        ),
    ),
    "altura_por_idade": Indicator(
        key="altura_por_idade",
        code="3",
        official_title="ALTURA X IDADE",
        categories=(
            "Altura Muito Baixa para a Idade",
            "Altura Baixa para a Idade",
            "Altura Adequada para a Idade",
        ),
    ),
}

AGE_RANGES = {
    "0_a_menor_6_meses": AgeRange(
        "0_a_menor_6_meses", "0", "1", "0 a < 6 meses",
    ),
    "0_a_menor_2_anos": AgeRange(
        "0_a_menor_2_anos", "0", "2", "0 a < 2 anos",
    ),
    "0_a_menor_5_anos": AgeRange(
        "0_a_menor_5_anos", "0", "5", "0 a < 5 anos",
    ),
    "6_meses_a_menor_2_anos": AgeRange(
        "6_meses_a_menor_2_anos", "1", "2", "6 meses a < 2 anos",
    ),
    "6_meses_a_menor_5_anos": AgeRange(
        "6_meses_a_menor_5_anos", "1", "5", "6 meses a < 5 anos",
    ),
    "2_a_menor_5_anos": AgeRange(
        "2_a_menor_5_anos", "2", "5", "2 a < 5 anos",
    ),
    "5_a_menor_7_anos": AgeRange(
        "5_a_menor_7_anos", "5", "7", "5 a < 7 anos",
    ),
    "5_a_menor_10_anos": AgeRange(
        "5_a_menor_10_anos", "5", "10", "5 a < 10 anos",
    ),
    "7_a_menor_10_anos": AgeRange(
        "7_a_menor_10_anos", "7", "10", "7 a < 10 anos",
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


def inspect_schema(binary, indicator):
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


def parse_export(binary, expected_uf, indicator):
    schema = inspect_schema(binary, indicator)
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
            percentages = [numeric_percent(value) for value in official_percentages]
            counts, total = resolve_counts(
                raw_counts, percentages, values[width - 1], uf, code,
            )
            row = {
                "Região": normalize_header(values[0]),
                "Código UF": str(int(values[1])).zfill(2),
                "UF": uf,
                "Código IBGE": code,
                "Município": normalize_header(values[4]),
                "Total": total,
            }
            for category, count, percentage in zip(
                schema.categories, counts, official_percentages,
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
        counts = [int(row[column]) for column in schema.count_columns]
        percentages = [numeric_percent(row[column]) for column in schema.percent_columns]
        total = int(row["Total"])
        if any(value < 0 for value in counts) or total < 0:
            raise RuntimeError("Contagem negativa em " + code)
        if sum(counts) != total:
            raise RuntimeError("Categorias diferentes do Total em " + code)
        if total == 0:
            if any(counts) or any(percentages):
                raise RuntimeError("Linha zero inconsistente em " + code)
            zeros.append(row)
            continue
        if abs(sum(percentages) - 100) > 0.10:
            raise RuntimeError("Percentuais nao somam 100 em " + code)
        for quantity, percentage in zip(counts, percentages):
            if abs(quantity / total * 100 - percentage) > 0.011:
                raise RuntimeError("Percentual nao corresponde a quantidade em " + code)
    return {"total": len(rows), "zeros": zeros}


def atomic_write_bytes(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(content)
    temporary.replace(path)


def write_csv(path, rows, columns):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
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
        write_csv(self.path, ordered, MANIFEST_COLUMNS)


def parse_list(value):
    return [item.strip() for item in (value or "").split(",") if item.strip()]


def canonical_age(value):
    key = AGE_ALIASES.get(value, value)
    if key not in AGE_RANGES:
        raise ValueError("faixa etaria invalida: %s" % value)
    return key


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
    configured = []
    for item in config["consultas"]:
        indicator_key = item.get("indice")
        if indicator_key not in INDICATORS:
            raise RuntimeError("indice invalido na configuracao: %r" % indicator_key)
        ages = item.get("faixas_etarias")
        if not isinstance(ages, list) or not ages:
            raise RuntimeError("consulta sem faixas_etarias: %s" % indicator_key)
        for age in ages:
            configured.append((indicator_key, canonical_age(str(age))))
    cli_indicators = parse_list(args.indices)
    cli_ages = parse_list(args.faixas_etarias)
    if cli_indicators or cli_ages:
        indicators = cli_indicators or list(dict.fromkeys(item[0] for item in configured))
        ages = (
            [canonical_age(item) for item in cli_ages]
            if cli_ages else list(dict.fromkeys(item[1] for item in configured))
        )
        invalid = [item for item in indicators if item not in INDICATORS]
        if invalid:
            raise RuntimeError("indices invalidos: %s" % ", ".join(invalid))
        configured = list(product(indicators, ages))
    unique = []
    for item in configured:
        if item not in unique:
            unique.append(item)
    return [Query(INDICATORS[index], AGE_RANGES[age], year) for index, age in unique]


def selected_states(value):
    selected = {item.upper() for item in parse_list(value)} if value else None
    states = [item for item in UF_CODES if not selected or item[0] in selected]
    if selected and {item[0] for item in states} != selected:
        invalid = sorted(selected - {item[0] for item in states})
        raise RuntimeError("UF invalida: " + ", ".join(invalid))
    return states


def raw_path(args, query, uf):
    return (
        args.raw_dir / query.indicator.key / query.age_range.key
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
    name = "sisvan_municipios_%s_%s_%s%s.csv" % (
        query.indicator.key, query.age_range.key, query.year, suffix,
    )
    return args.output_dir / query.indicator.key / name


def metadata_path(output):
    return output.with_suffix(".metadados.json")


def write_metadata(path, query, output, stats, states, schema):
    data = {
        "fonte": helper.PORTAL,
        "endpoint": helper.ENDPOINT,
        "arquivo": portable_path(output),
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
        "gerado_em": datetime.now().astimezone().isoformat(timespec="seconds"),
        "observacao": (
            "CSV consolidado e validado a partir dos XLSX oficiais por UF; "
            "os XLSX preservados constituem a camada bruta imutavel."
        ),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    temporary.replace(path)


def manifest_row(query, uf, raw, payload, content, row_count, timestamp):
    return {
        "id_coleta": "sisvan-%s-%s-%s-%s" % (
            query.year, query.indicator.key, query.age_range.key, uf,
        ),
        "fonte": helper.PORTAL,
        "arquivo_local": portable_path(raw),
        "nome_original": "",
        "indice_antropometrico": query.indicator.official_title,
        "faixa_etaria": query.age_range.official_label,
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
    label = "%s | %s | %s" % (
        query.indicator.official_title, query.age_range.official_label, query.year,
    )
    print("\nCONSULTA:", label)
    all_rows, expected_schema = [], None
    for position, (uf, uf_code) in enumerate(states, 1):
        print("[%02d/%02d] %s" % (position, len(states), uf))
        raw = raw_path(args, query, uf)
        payload = helper.report_payload(
            query.year, uf_code, query.indicator.code,
            query.age_range.start, query.age_range.end,
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
                debug_name="%s_%s_%s" % (
                    query.indicator.key, query.age_range.key, uf,
                ),
            )
            atomic_write_bytes(raw, content)
            print("  XLSX oficial salvo:", raw)
        rows, schema = parse_export(content, uf, query.indicator)
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
        manifest.write()
        print("  municipios:", len(rows))
    all_rows.sort(key=lambda row: int(row["Código IBGE"]))
    stats = validate(all_rows, expected_schema)
    output = output_path(args, query, states, query_count)
    write_csv(output, all_rows, expected_schema.columns)
    write_metadata(
        metadata_path(output), query, output, stats, states, expected_schema,
    )
    print("  CSV consolidado:", output)
    print("  linhas:", stats["total"], "| Total=0:", len(stats["zeros"]))
    return output


def print_options():
    print("Indices disponíveis:")
    for item in INDICATORS.values():
        print("  %-20s codigo=%s  %s" % (item.key, item.code, item.official_title))
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
        "--indices",
        help="Lista separada por virgulas: imc_por_idade,altura_por_idade",
    )
    parser.add_argument(
        "--faixas-etarias",
        help="Lista separada por virgulas; use --listar-opcoes para consultar",
    )
    parser.add_argument("--raw-dir", type=Path, default=Path("dados/brutos/sisvan"))
    parser.add_argument(
        "--output-dir", type=Path, default=Path("dados/tratados/sisvan"),
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--manifest", type=Path,
        default=Path("metadados/manifestos/sisvan_coletas.csv"),
    )
    parser.add_argument("--debug-dir", type=Path, default=Path("debug/sisvan"))
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
    try:
        queries = resolve_queries(args)
        states = selected_states(args.ufs)
    except (RuntimeError, ValueError) as exc:
        parser.error(str(exc))
    print("Consultas planejadas:")
    for query in queries:
        print(
            "- %s | %s | %s"
            % (
                query.indicator.official_title,
                query.age_range.official_label,
                query.year,
            )
        )
    print("UFs:", ", ".join(item[0] for item in states))
    if args.dry_run:
        return
    session = helper.new_session(args.retries)
    limiter = helper.Limiter(args.delay)
    manifest = Manifest(args.manifest)
    portal_started = [False]
    outputs = []
    for query in queries:
        outputs.append(
            collect_query(
                args, query, states, session, limiter, portal_started,
                manifest, len(queries),
            )
        )
    print("\nCOLETA CONCLUIDA")
    print("Manifesto:", args.manifest)
    for output in outputs:
        print("CSV:", output)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nColeta interrompida; arquivos ja validados foram preservados.", file=sys.stderr)
        raise SystemExit(130)
