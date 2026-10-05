"""Executa a v3 integralmente e valida metodologia, produtos e versões preservadas."""

import argparse
import hashlib
import json
from pathlib import Path

import nbformat
import pandas as pd
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "notebooks/01_sobreposicao_criterios_v3.ipynb"


def execute(directory):
    preserved = [ROOT / "notebooks" / name for name in
                 ["01_sobreposicao_criterios.ipynb", "01_sobreposicao_criterios_v2.ipynb"]]
    before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in preserved}
    notebook = nbformat.read(NOTEBOOK, as_version=4)
    NotebookClient(notebook, timeout=300, kernel_name="python3",
                   resources={"metadata": {"path": str(directory)}}).execute()
    cells = [c for c in notebook.cells if c.cell_type == "code"]
    if [c.execution_count for c in cells] != list(range(1, len(cells) + 1)):
        raise AssertionError("Execução incompleta ou fora de ordem")
    if any(o.output_type == "error" for c in cells for o in c.outputs):
        raise AssertionError("Execução contém traceback")
    destination = sorted(p for p in (directory / "resultados_sobreposicao_v3/resultados").glob("execucao_*")
                         if p.is_dir())[-1]
    csvs = list(destination.glob("*.csv"))
    figures = list((destination / "figuras").glob("*.png"))
    svgs = list((destination / "figuras").glob("*.svg"))
    if len(csvs) != 31 or len(figures) != 12 or len(svgs) != 12 or not destination.with_suffix(".zip").is_file():
        raise AssertionError(f"Produtos incompletos: {len(csvs)} CSVs, {len(figures)} PNGs, {len(svgs)} SVGs")
    frame = pd.read_csv(destination / "base_municipal_final.csv",
                        dtype={"codigo_ibge": "string", "codigo_ibge_6": "string"})
    required = {"codigo_ibge", "municipio", "uf", "regiao", "ivs", "idhm", "cadinsan_pct",
                "avaliados_altura", "dai_pct", "dai_categoria_oms", "avaliados_peso", "dpi_pct",
                "dim_social", "dim_alimentar", "dim_nutricional", "dim_nutricional_dai",
                "n_dimensoes_desfavoraveis", "classe_convergencia", "convergencia_total", "convergencia_total_dai"}
    if not required.issubset(frame.columns) or any("prioridade" in c or "cadunico" in c.lower() for c in frame):
        raise AssertionError("Esquema final incompatível com a v3")
    parameters = json.loads((destination / "manifesto_execucao.json").read_text(),
                            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
    minimum = parameters["minimo_avaliados"]
    valid = frame.dai_pct.notna() & frame.dpi_pct.notna() & frame.avaliados_altura.ge(minimum) & frame.avaliados_peso.ge(minimum)
    expected = frame.dai_pct.ge(parameters["corte_dai_pct"]) & frame.dpi_pct.ge(parameters["corte_dpi_pct"])
    if not frame.loc[valid, "dim_nutricional"].eq(expected[valid]).all() or not frame.loc[~valid, "dim_nutricional"].isna().all():
        raise AssertionError("Dimensão principal não aplica DAI + DPI com insuficiência explícita")
    complete = frame[["dim_social", "dim_alimentar", "dim_nutricional"]].notna().all(axis=1)
    conjunction = frame.loc[complete, ["dim_social", "dim_alimentar", "dim_nutricional"]].all(axis=1)
    if not frame.loc[complete, "convergencia_total"].eq(conjunction).all():
        raise AssertionError("Convergência principal incorreta")
    if not frame.loc[~complete, ["convergencia_total", "n_dimensoes_desfavoraveis"]].isna().all().all():
        raise AssertionError("Dados insuficientes tratados como negativos")
    for path, sha in before.items():
        if hashlib.sha256(path.read_bytes()).hexdigest() != sha:
            raise AssertionError(f"Versão preservada foi alterada: {path}")
    nbformat.validate(notebook)
    nbformat.write(notebook, NOTEBOOK)
    print(f"Execução concluída: {len(cells)} células, {len(csvs)} CSVs, {len(figures)} PNGs/SVGs")
    print(destination)
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("diretorio", type=Path)
    args = parser.parse_args()
    args.diretorio.mkdir(parents=True, exist_ok=True)
    execute(args.diretorio.resolve())
