#!/usr/bin/env python3
"""Exporta a tabela municipal bruta do Relatorio Publico do SISVAN.

Nao adiciona colunas, nao calcula indicadores e nao faz juncao com o IBGE.
Os nomes, codigos municipais de seis digitos e percentuais sao preservados
como aparecem no SISVAN. Apenas o cabecalho XLSX de dois niveis e achatado
para uma linha, pois CSV nao suporta celulas mescladas.
"""
from __future__ import annotations

import argparse
import csv
import io
import re
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
COLS = [
    "Região", "Código UF", "UF", "Código IBGE", "Município",
    "Magreza acentuada - Quantidade", "Magreza acentuada - %",
    "Magreza - Quantidade", "Magreza - %",
    "Eutrofia - Quantidade", "Eutrofia - %",
    "Risco de sobrepeso - Quantidade", "Risco de sobrepeso - %",
    "Sobrepeso - Quantidade", "Sobrepeso - %",
    "Obesidade - Quantidade", "Obesidade - %", "Total",
]
COUNT_COLS = [
    "Magreza acentuada - Quantidade", "Magreza - Quantidade",
    "Eutrofia - Quantidade", "Risco de sobrepeso - Quantidade",
    "Sobrepeso - Quantidade", "Obesidade - Quantidade",
]
PERCENT_COLS = [
    "Magreza acentuada - %", "Magreza - %", "Eutrofia - %",
    "Risco de sobrepeso - %", "Sobrepeso - %", "Obesidade - %",
]


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


def resolve_counts(row, uf, code):
    raw_counts = [row[5], row[7], row[9], row[11], row[13], row[15]]
    pct_values = [
        numeric_percent(row[6]), numeric_percent(row[8]),
        numeric_percent(row[10]), numeric_percent(row[12]),
        numeric_percent(row[14]), numeric_percent(row[16]),
    ]
    totals = helper.count_candidates(row[17])
    if totals == [0]:
        values = tuple(helper.parse_count(value) for value in raw_counts)
        if any(values):
            raise RuntimeError("%s/%s: categorias sem denominador" % (uf, code))
        return values, 0
    solutions = []
    for total in totals:
        for values in product(
            *(helper.count_candidates(value) for value in raw_counts)
        ):
            if sum(values) != total:
                continue
            if all(
                abs(value / total * 100 - pct) <= 0.011
                for value, pct in zip(values, pct_values)
            ):
                solutions.append((values, total))
    if not solutions:
        raise RuntimeError("%s/%s: escala das contagens irresolvivel" % (uf, code))
    return min(solutions, key=lambda item: item[1])


def parse_export(binary, expected_uf):
    book = load_workbook(io.BytesIO(binary), read_only=True, data_only=True)
    rows, seen = [], set()
    try:
        for source in book.active.iter_rows(values_only=True):
            values = list(source) + [None] * max(0, 18 - len(source))
            code = helper.municipal_code(values[3])
            uf = str(values[2]).strip() if values[2] is not None else ""
            if code is None or uf != expected_uf:
                continue
            if code in seen:
                raise RuntimeError("Codigo SISVAN duplicado em %s: %s" % (uf, code))
            seen.add(code)
            counts, total = resolve_counts(values, uf, code)
            rows.append({
                "Região": str(values[0]).strip(),
                "Código UF": str(int(values[1])).zfill(2),
                "UF": uf,
                "Código IBGE": code,
                "Município": str(values[4]).strip(),
                "Magreza acentuada - Quantidade": counts[0],
                "Magreza acentuada - %": official_percent(values[6]),
                "Magreza - Quantidade": counts[1],
                "Magreza - %": official_percent(values[8]),
                "Eutrofia - Quantidade": counts[2],
                "Eutrofia - %": official_percent(values[10]),
                "Risco de sobrepeso - Quantidade": counts[3],
                "Risco de sobrepeso - %": official_percent(values[12]),
                "Sobrepeso - Quantidade": counts[4],
                "Sobrepeso - %": official_percent(values[14]),
                "Obesidade - Quantidade": counts[5],
                "Obesidade - %": official_percent(values[16]),
                "Total": total,
            })
    finally:
        book.close()
    if not rows:
        raise RuntimeError("Nenhuma linha municipal encontrada para " + expected_uf)
    return rows


def validate(rows):
    seen, zeros = set(), []
    for row in rows:
        code = row["Código IBGE"]
        if not re.fullmatch(r"\d{6}", code) or code in seen:
            raise RuntimeError("Codigo SISVAN invalido ou duplicado: " + code)
        seen.add(code)
        counts = [int(row[column]) for column in COUNT_COLS]
        total = int(row["Total"])
        if any(value < 0 for value in counts) or total < 0:
            raise RuntimeError("Contagem negativa em " + code)
        if sum(counts) != total:
            raise RuntimeError("Categorias diferentes do Total em " + code)
        percentages = [numeric_percent(row[column]) for column in PERCENT_COLS]
        if total == 0:
            if any(counts) or any(percentages):
                raise RuntimeError("Linha zero inconsistente em " + code)
            zeros.append(row)
            continue
        if abs(sum(percentages) - 100) > 0.10:
            raise RuntimeError("Percentuais nao somam 100 em " + code)
        for quantity, pct in zip(counts, percentages):
            if abs(quantity / total * 100 - pct) > 0.011:
                raise RuntimeError("Percentual nao corresponde a quantidade em " + code)
    return {"total": len(rows), "zeros": zeros}


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLS)
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def load_checkpoint(path, uf):
    if not path.exists():
        return None
    try:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames != COLS:
                return None
            rows = list(reader)
        if any(row["UF"] != uf for row in rows):
            return None
        validate(rows)
        return rows
    except (OSError, ValueError, RuntimeError):
        return None


def write_readme(args, stats):
    zero_lines = "\n".join(
        "- %s — %s/%s" % (row["Código IBGE"], row["Município"], row["UF"])
        for row in stats["zeros"]
    ) or "- Nenhuma"
    text = f"""# SISVAN municipal — base bruta ({args.year})

## Arquivo principal

sisvan_municipios_{args.year}.csv é uma transcrição da tabela municipal do
Relatório Público do SISVAN. Não contém indicadores calculados, nomes ou códigos
substituídos pelo IBGE, nem municípios acrescentados por outra fonte.

Fonte: {helper.PORTAL}

Endpoint: POST {helper.ENDPOINT}

Filtros oficiais:

- nuAno={args.year} e nuMes[]=99;
- tpFiltro=M e coMunicipioIbge=99;
- nu_ciclo_vida=1;
- nu_idade_inicio=0 e nu_idade_fim=5;
- nu_indice_cri=4 (IMC por idade);
- sexo, raça/cor, origem, povo/comunidade e escolaridade: todos.

O ano não é uma coluna da tabela do SISVAN: ele é metadado do filtro e do nome
do arquivo. O código municipal é mantido com os seis dígitos exibidos pelo
SISVAN. Os nomes municipais também são os textos do SISVAN.

O XLSX possui cabeçalho em dois níveis. Como CSV não admite células mescladas,
os níveis foram combinados sem mudar os rótulos, por exemplo:
Magreza acentuada - Quantidade e Magreza acentuada - %.

As quantidades são serializadas como inteiros no CSV. Assim, o valor brasileiro
1.114 é escrito como 1114; isso muda somente a formatação do separador de
milhar, não o valor. Os percentuais preservam % e o símbolo - usado oficialmente
para categoria com zero casos.

## Resultado

- Linhas municipais do SISVAN: **{stats["total"]}**.
- Linhas com Total=0: **{len(stats["zeros"])}**.
- Códigos duplicados: **0**.
- Categorias cuja soma difere de Total: **0**.

Linhas oficiais com total zero:

{zero_lines}

A versão anteriormente entregue, com código IBGE de sete dígitos e indicador
de desnutrição calculado, foi preservada separadamente como
sisvan_municipios_{args.year}_derivada.csv.

## Reprodução

    python3 scripts/coletar_sisvan.py --year {args.year}

Os checkpoints brutos ficam em
data/sisvan/checkpoints_brutos/{args.year}/UF.csv. O processo é sequencial,
possui rate limiting, sessão, timeout, retries e retomada.
"""
    args.readme.parent.mkdir(parents=True, exist_ok=True)
    args.readme.write_text(text, encoding="utf-8")


def collect(args):
    selected = (
        {item.strip().upper() for item in args.ufs.split(",") if item.strip()}
        if args.ufs else None
    )
    states = [item for item in UF_CODES if not selected or item[0] in selected]
    if selected and {item[0] for item in states} != selected:
        raise RuntimeError("UF invalida em --ufs")
    s = helper.new_session(args.retries)
    limiter = helper.Limiter(args.delay)
    started, all_rows = False, []
    for index, (uf, uf_code) in enumerate(states, 1):
        print("[%02d/%02d] %s" % (index, len(states), uf))
        checkpoint = args.checkpoint_dir / str(args.year) / (uf + ".csv")
        rows = None if args.force else load_checkpoint(checkpoint, uf)
        if rows is not None:
            print("  checkpoint bruto reutilizado")
        else:
            if not started:
                helper.start_portal(
                    s, (args.connect_timeout, args.read_timeout), limiter
                )
                started = True
            print("  baixando XLSX oficial...")
            binary = helper.fetch_xlsx(s, args, limiter, uf, uf_code)
            rows = parse_export(binary, uf)
            validate(rows)
            write_csv(checkpoint, rows)
            print("  checkpoint bruto salvo:", checkpoint)
        stats = validate(rows)
        print("  linhas SISVAN:", stats["total"])
        print("  Total=0:", len(stats["zeros"]))
        all_rows.extend(rows)
    all_rows.sort(key=lambda row: int(row["Código IBGE"]))
    stats = validate(all_rows)
    write_csv(args.output, all_rows)
    write_readme(args, stats)
    print("\nTOTAL")
    print("linhas municipais SISVAN:", stats["total"])
    print("linhas com Total=0:", len(stats["zeros"]))
    print("CSV bruto:", args.output)


def main():
    parser = argparse.ArgumentParser(
        description="Exporta a tabela municipal bruta do SISVAN."
    )
    parser.add_argument("--year", type=int, default=2025)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--checkpoint-dir", type=Path,
        default=Path("data/sisvan/checkpoints_brutos"),
    )
    parser.add_argument("--debug-dir", type=Path, default=Path("debug/sisvan"))
    parser.add_argument("--readme", type=Path, default=Path("data/sisvan/README.md"))
    parser.add_argument("--delay", type=float, default=1.0)
    parser.add_argument("--connect-timeout", type=float, default=20.0)
    parser.add_argument("--read-timeout", type=float, default=180.0)
    parser.add_argument("--retries", type=int, default=4)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--ufs")
    args = parser.parse_args()
    if args.delay < 0 or args.connect_timeout <= 0 or args.read_timeout <= 0:
        parser.error("delay >= 0 e timeouts positivos")
    args.output = args.output or Path(
        "data/sisvan/sisvan_municipios_%s.csv" % args.year
    )
    collect(args)


if __name__ == "__main__":
    main()
