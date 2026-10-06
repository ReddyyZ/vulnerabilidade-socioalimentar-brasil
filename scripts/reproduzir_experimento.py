"""Verifica as entradas e reproduz o notebook publicado, sem ferramentas locais."""

import argparse
import ast
import base64
import hashlib
import io
import json
import platform
import sys
import zipfile
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from types import ModuleType

import nbformat
import pandas as pd
from jupyter_client import KernelManager
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "experimento.ipynb"
INPUTS = ROOT / "dados/pesquisa"
REFERENCE = ROOT / "resultados/referencia.json"


def tagged_cell(notebook, tag):
    cells = [cell for cell in notebook.cells if tag in cell.metadata.get("tags", [])]
    if len(cells) != 1 or cells[0].cell_type != "code":
        raise ValueError(f"É necessária uma única célula de código com a tag {tag!r}")
    return cells[0]


def analysis_source(notebook=None):
    notebook = notebook if notebook is not None else nbformat.read(NOTEBOOK, as_version=4)
    return tagged_cell(notebook, "funcoes_analise").source.split("\n", 1)[1]


def load_analysis(notebook=None, include_formatting=False):
    """Carrega as funções publicadas para verificações e testes, sem rodar a análise."""
    notebook = notebook if notebook is not None else nbformat.read(NOTEBOOK, as_version=4)
    module = ModuleType("experimento_analise")
    exec(compile(analysis_source(notebook), "<funcoes-do-notebook>", "exec"), module.__dict__)
    if include_formatting:
        names = {"COLUNAS_CONTAGEM", "numero_br", "contagem_br", "percentual_br", "quantil_br", "tabela_br"}
        source = tagged_cell(notebook, "ambiente").source
        nodes = []
        for node in ast.parse(source).body:
            name = node.name if isinstance(node, ast.FunctionDef) else (
                node.targets[0].id if isinstance(node, ast.Assign)
                and isinstance(node.targets[0], ast.Name) else None)
            if name in names or isinstance(node, ast.ImportFrom) and node.module == "pandas.api.types":
                nodes.append(node)
        defined = {node.name for node in nodes if isinstance(node, ast.FunctionDef)}
        if not (names - {"COLUNAS_CONTAGEM"}).issubset(defined):
            raise ValueError("Funções de formatação ausentes no notebook")
        exec(compile(ast.Module(body=nodes, type_ignores=[]), "<formatacao-do-notebook>", "exec"), module.__dict__)
    return module


def embedded_payload(notebook=None):
    notebook = notebook if notebook is not None else nbformat.read(NOTEBOOK, as_version=4)
    for node in ast.parse(tagged_cell(notebook, "entradas").source).body:
        if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == "PACOTE_BASE64" for target in node.targets):
            return base64.b64decode(ast.literal_eval(node.value), validate=True)
    raise ValueError("Pacote de entradas ausente no notebook")


def verify_inputs():
    notebook = nbformat.read(NOTEBOOK, as_version=4)
    nbformat.validate(notebook)
    analysis = load_analysis(notebook)
    analysis.verify_hashes(INPUTS)
    manifest = json.loads((INPUTS / "documentacao/manifesto_entradas.json").read_text())
    expected_files = set(analysis.DATA_FILES.values()) | (
        set(analysis.SUPPORT_FILES) - {"documentacao/manifesto_entradas.json"})
    if set(manifest["arquivos"]) != expected_files:
        raise ValueError("Manifesto de procedência contém entradas faltantes ou adicionais")
    for relative, expected in manifest["arquivos"].items():
        if hashlib.sha256((INPUTS / relative).read_bytes()).hexdigest() != expected:
            raise ValueError(f"Procedência divergente: {relative}")
    original = manifest["catalogo_original"]
    original_path = (ROOT / original["arquivo"]).resolve()
    if not original_path.is_relative_to((INPUTS / "documentacao").resolve()):
        raise ValueError("O catálogo original deve estar junto às entradas publicadas")
    if hashlib.sha256(original_path.read_bytes()).hexdigest() != original["sha256"]:
        raise ValueError("Catálogo original foi alterado")
    for relative, expected in manifest["manifestos_coleta_sha256"].items():
        path = (ROOT / relative).resolve()
        if not path.is_relative_to((ROOT / "metadados/manifestos").resolve()):
            raise ValueError("Caminho de manifesto de coleta inválido")
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"Manifesto de coleta alterado: {relative}")
    originals = manifest["xlsx_originais"]
    for index in ("altura_por_idade", "peso_por_idade"):
        group = [item for item in originals if item["indice"] == index]
        if len(group) != 27 or len({Path(item["arquivo_local"]).stem for item in group}) != 27:
            raise ValueError(f"São esperadas 27 UFs originais em {index}")
    paths = [item["arquivo_local"] for item in originals]
    if len(paths) != 54 or len(set(paths)) != 54:
        raise ValueError("São esperados exatamente 54 XLSX originais")
    for item in originals:
        path = (ROOT / item["arquivo_local"]).resolve()
        if not path.is_relative_to((ROOT / "dados/brutos/sisvan").resolve()):
            raise ValueError("Caminho de origem SISVAN inválido")
        if hashlib.sha256(path.read_bytes()).hexdigest() != item["hash_arquivo"]:
            raise ValueError(f"XLSX alterado: {item['arquivo_local']}")
    required = expected_files | {"documentacao/manifesto_entradas.json", "SHA256SUMS", "README.md"}
    with zipfile.ZipFile(io.BytesIO(embedded_payload(notebook))) as archive:
        if set(archive.namelist()) != required or len(archive.namelist()) != len(required):
            raise ValueError("Pacote do notebook contém arquivos faltantes ou adicionais")
        for relative in required:
            if archive.read(relative) != (INPUTS / relative).read_bytes():
                raise ValueError(f"Notebook e seleção oficial divergem: {relative}")
    digest = hashlib.sha256(analysis_source(notebook).encode()).hexdigest()
    if notebook.metadata["experimento"]["codigo_analise_sha256"] != digest:
        raise ValueError("Hash do código de análise divergente")
    environment_cell = ast.parse(tagged_cell(notebook, "ambiente").source)
    code_hashes = [ast.literal_eval(node.value) for node in environment_cell.body
                  if isinstance(node, ast.Assign) and any(
                      isinstance(target, ast.Name) and target.id == "CODIGO_ANALISE_SHA256"
                      for target in node.targets)]
    if code_hashes != [digest]:
        raise ValueError("Hash do código no manifesto de execução divergente")
    input_digest = hashlib.sha256((INPUTS / "SHA256SUMS").read_bytes()).hexdigest()
    if notebook.metadata["experimento"]["entradas_sha256"] != input_digest:
        raise ValueError("Hash das entradas no notebook divergente")
    return {"entradas_verificadas": len(expected_files) + 1, "xlsx_originais": len(originals)}


def verify_environment():
    expected = json.loads((ROOT / "configuracoes/ambiente.json").read_text())
    mismatches = {}
    if platform.python_version() != expected["python"]:
        mismatches["python"] = platform.python_version()
    if platform.system() != expected["sistema"]:
        mismatches["sistema"] = platform.system()
    for line in (ROOT / "requirements.txt").read_text().splitlines():
        if line.strip() and not line.startswith("#"):
            name, required = line.split("==")
            try:
                actual = version(name)
            except PackageNotFoundError:
                actual = "não instalado"
            if actual != required:
                mismatches[name] = actual
    if mismatches:
        raise ValueError(f"Ambiente diferente da referência: {mismatches}")
    return {"python": platform.python_version(), "dependencias": "versões exatas verificadas"}


def verify_results(directory):
    directory = Path(directory)
    reference = json.loads(REFERENCE.read_text())
    actual = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in directory.glob("*.csv")}
    if actual != reference["csv_sha256"]:
        differences = sorted(name for name in set(actual) | set(reference["csv_sha256"])
                             if actual.get(name) != reference["csv_sha256"].get(name))
        raise ValueError(f"Resultados diferem da referência: {differences}")
    for extension in ("png", "svg"):
        if len(list((directory / "figuras").glob(f"*.{extension}"))) != reference["produtos"][extension]:
            raise ValueError(f"Figuras {extension} incompletas")
    parameters = json.loads((directory / "manifesto_execucao.json").read_text())
    if any(parameters[key] != value for key, value in reference["parametros"].items()):
        raise ValueError("Parâmetros diferentes do experimento de referência")
    return {"csv_identicos_referencia": len(actual), "figuras": "12 PNG e 12 SVG"}


def execute(directory=ROOT):
    """Grava o notebook executado somente depois de validar a reprodução inteira."""
    directory = Path(directory).resolve()
    for protected in (INPUTS, ROOT / "dados/brutos", ROOT / "metadados"):
        if directory.is_relative_to(protected.resolve()):
            raise ValueError("Não executar dentro das entradas ou origens preservadas")
    verify_inputs()
    verify_environment()
    directory.mkdir(parents=True, exist_ok=True)
    output_root = directory / "resultados_experimento/resultados"
    previous = set(output_root.glob("execucao_*"))
    notebook = nbformat.read(NOTEBOOK, as_version=4)
    manager = KernelManager(kernel_name="python3")
    manager.kernel_spec.argv = [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"]
    NotebookClient(notebook, timeout=300, kernel_name="python3", km=manager,
                   resources={"metadata": {"path": str(directory)}}).execute(cleanup_kc=True)
    cells = [cell for cell in notebook.cells if cell.cell_type == "code"]
    if [cell.execution_count for cell in cells] != list(range(1, len(cells) + 1)):
        raise AssertionError("Execução incompleta ou fora de ordem")
    if any(output.output_type == "error" for cell in cells for output in cell.outputs):
        raise AssertionError("Execução contém traceback")
    created = [path for path in output_root.glob("execucao_*") if path.is_dir() and path not in previous]
    if len(created) != 1:
        raise AssertionError("Não foi identificada uma única nova execução")
    destination = created[0]
    if not destination.with_suffix(".zip").is_file():
        raise AssertionError("ZIP de resultados ausente")
    frame = pd.read_csv(destination / "base_municipal_final.csv",
                        dtype={"codigo_ibge": "string", "codigo_ibge_6": "string"})
    parameters = json.loads((destination / "manifesto_execucao.json").read_text())
    minimum = parameters["minimo_avaliados"]
    valid = frame.dai_pct.notna() & frame.dpi_pct.notna() & frame.avaliados_altura.ge(minimum) & frame.avaliados_peso.ge(minimum)
    expected = frame.dai_pct.ge(parameters["corte_dai_pct"]) & frame.dpi_pct.ge(parameters["corte_dpi_pct"])
    if not frame.loc[valid, "dim_nutricional"].eq(expected[valid]).all() or not frame.loc[~valid, "dim_nutricional"].isna().all():
        raise AssertionError("Dimensão nutricional não aplica DAI + DPI com insuficiência explícita")
    complete = frame[["dim_social", "dim_alimentar", "dim_nutricional"]].notna().all(axis=1)
    conjunction = frame.loc[complete, ["dim_social", "dim_alimentar", "dim_nutricional"]].all(axis=1)
    if not frame.loc[complete, "convergencia_total"].eq(conjunction).all():
        raise AssertionError("Convergência principal incorreta")
    if not frame.loc[~complete, ["convergencia_total", "n_dimensoes_desfavoraveis"]].isna().all().all():
        raise AssertionError("Dados insuficientes tratados como negativos")
    verify_inputs()
    print(verify_results(destination))
    nbformat.validate(notebook)
    nbformat.write(notebook, NOTEBOOK)
    print(f"Execução concluída: {len(cells)} células; notebook salvo com resultados.")
    print(destination.relative_to(directory))
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verificar", action="store_true", help="Confere integridade sem executar ou modificar o notebook")
    parser.add_argument("--ambiente", action="store_true", help="Exige o ambiente fixado também na verificação")
    parser.add_argument("--resultados", type=Path, help="Confere uma pasta de resultados já existente")
    parser.add_argument("--diretorio", type=Path, default=ROOT, help="Diretório de execução; padrão: raiz do projeto")
    args = parser.parse_args()
    if args.verificar or args.resultados is not None:
        print(verify_inputs())
        if args.ambiente:
            print(verify_environment())
        if args.resultados is not None:
            print(verify_results(args.resultados))
    else:
        execute(args.diretorio)
