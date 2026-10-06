"""Reconstrói os dois CSVs históricos a partir dos XLSX locais, sem acessar a rede."""

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path

from scripts import coletar_sisvan as collector

ROOT = Path(__file__).resolve().parents[1]
INPUTS = ROOT / "dados/pesquisa"


def reconstruct(destination):
    destination = Path(destination).resolve()
    # Não sobrescreve entradas, origens ou registros de procedência.
    for protected in (INPUTS, ROOT / "dados/brutos", ROOT / "metadados"):
        if destination.is_relative_to(protected.resolve()):
            raise ValueError("Escolha uma saída fora das entradas e origens preservadas")
    manifest = json.loads((INPUTS / "documentacao/manifesto_entradas.json").read_text())
    sources = {index: manifest["procedencia"][f"sisvan_{kind}"]["csv_atual"]
               for index, kind in (("altura_por_idade", "altura"), ("peso_por_idade", "peso"))}
    products = []
    for index in ("altura_por_idade", "peso_por_idade"):
        indicator = collector.INDICATORS[index]
        rows = []
        for item in manifest["xlsx_originais"]:
            if item["indice"] != index:
                continue
            path = ROOT / item["arquivo_local"]
            binary = path.read_bytes()
            if hashlib.sha256(binary).hexdigest() != item["hash_arquivo"]:
                raise ValueError(f"XLSX alterado: {path}")
            parsed, schema = collector.parse_export(binary, path.stem, indicator)
            if index == "peso_por_idade":
                # Replica SOMENTE a conversão histórica deste CSV de peso.
                # Coletas novas continuam preservando células, sem essa normalização.
                for row in parsed:
                    counts, total = collector.resolve_counts(
                        [row[c] for c in schema.count_columns],
                        [collector.numeric_percent(row[c]) for c in schema.percent_columns],
                        row["Total"], row["UF"], row["Código IBGE"])
                    for column, count in zip(schema.count_columns, counts):
                        row[column] = count
                    row["Total"] = total
            rows.extend(parsed)
        collector.validate(rows, schema)
        rows.sort(key=lambda row: row["Código IBGE"])
        stream = io.StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=schema.columns, lineterminator="\r\n")
        writer.writeheader()
        writer.writerows(rows)
        binary = stream.getvalue().encode("utf-8-sig")
        relative = sources[index]
        if binary != (INPUTS / relative).read_bytes():
            raise ValueError(f"Reconstrução difere da entrada histórica: {relative}")
        output = destination / Path(relative).name
        if output.exists():
            raise FileExistsError(f"Saída já existe: {output}")
        products.append((output, binary))
    destination.mkdir(parents=True, exist_ok=True)
    for output, binary in products:
        output.write_bytes(binary)
        print(f"Reconstrução idêntica: {output.name}")
    return [p for p, _ in products]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destino", type=Path, required=True)
    reconstruct(parser.parse_args().destino)
