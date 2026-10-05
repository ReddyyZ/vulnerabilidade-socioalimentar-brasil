"""Executa e verifica o notebook v2 em uma sessão local isolada."""

import argparse
import hashlib
from pathlib import Path

import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks/01_sobreposicao_criterios_v2.ipynb"


def execute(directory):
    original = ROOT / "notebooks/01_sobreposicao_criterios.ipynb"
    before = hashlib.sha256(original.read_bytes()).hexdigest()
    notebook = nbformat.read(NOTEBOOK, as_version=4)
    client = NotebookClient(notebook, timeout=300, kernel_name="python3",
                            resources={"metadata": {"path": str(directory)}})
    client.execute()
    code_cells = [c for c in notebook.cells if c.cell_type == "code"]
    if [c.execution_count for c in code_cells] != list(range(1, len(code_cells) + 1)):
        raise AssertionError("Células fora de ordem")
    if any(o.output_type == "error" for c in code_cells for o in c.outputs):
        raise AssertionError("Execução contém traceback")
    destination = sorted(p for p in (directory / "resultados_sobreposicao_v2/resultados").glob("execucao_*")
                         if p.is_dir())[-1]
    csvs = list(destination.glob("*.csv"))
    figures = list((destination / "figuras").glob("*.png"))
    if len(csvs) != 30 or len(figures) != 12 or not destination.with_suffix(".zip").is_file():
        raise AssertionError(f"Produtos incompletos: {len(csvs)} CSVs, {len(figures)} PNGs")
    if hashlib.sha256(original.read_bytes()).hexdigest() != before:
        raise AssertionError("Notebook original alterado")
    nbformat.write(notebook, NOTEBOOK)
    print(f"Execução concluída: {len(code_cells)} células, {len(csvs)} CSVs, {len(figures)} PNGs/SVGs")
    print(destination)
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("diretorio", type=Path)
    args = parser.parse_args()
    args.diretorio.mkdir(parents=True, exist_ok=True)
    execute(args.diretorio.resolve())
