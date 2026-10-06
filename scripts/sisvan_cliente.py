"""Cliente HTTP e leitura auxiliar do SISVAN; não executa análises derivadas."""

import math
import re
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

PORTAL = "https://sisaps.saude.gov.br/sisvan/relatoriopublico/"


ENDPOINT = PORTAL + "estadonutricional"


def new_session(retries):
    policy = Retry(
        total=retries, connect=retries, read=retries, status=retries,
        backoff_factor=1, status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(("GET", "POST")),
        respect_retry_after_header=True, raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=policy, pool_connections=2, pool_maxsize=2)
    result = requests.Session()
    result.mount("https://", adapter)
    result.mount("http://", adapter)
    result.headers.update({
        "User-Agent": "pesquisa-academica-sisvan/2.0 (+%s)" % PORTAL,
        "Accept-Language": "pt-BR,pt;q=0.9",
    })
    return result


def http(s, method, url, timeout, **kwargs):
    response = s.request(method, url, timeout=timeout, **kwargs)
    if response.status_code == 429:
        raise RuntimeError(
            "HTTP 429; Retry-After=%s" % response.headers.get("Retry-After", "?")
        )
    response.raise_for_status()
    return response


def report_payload(
    year, uf, index_code="4", age_start="0", age_end="5",
    life_cycle="1", adolescent_index_code="1", pregnancy_age="99",
):
    # coMunicipioIbge=99 e essencial; vazio devolve somente totais.
    return {
        "excel": "1", "tpRelatorio": "2", "coVisualizacao": "3",
        "nuAno": str(year), "nuMes[]": "99", "tpFiltro": "M",
        "coRegiao": "99", "coUfIbge": uf, "coMunicipioIbge": "99",
        "noRegional": "", "st_cobertura": "99",
        "nu_ciclo_vida": str(life_cycle),
        "nu_idade_inicio": str(age_start), "nu_idade_fim": str(age_end),
        "nu_indice_cri": str(index_code),
        "nu_indice_ado": str(adolescent_index_code),
        "nu_idade_ges": str(pregnancy_age), "ds_sexo2": "1",
        "ds_raca_cor2": "99", "co_sistema_origem": "0",
        "CO_POVO_COMUNIDADE": "TODOS", "CO_ESCOLARIDADE": "TODOS",
        "tpAbrangencia": "M", "tpAbrangenciaEas": "",
    }


class Limiter:
    def __init__(self, interval):
        self.interval, self.last = max(0, interval), 0

    def wait(self):
        remaining = self.interval - (time.monotonic() - self.last)
        if remaining > 0:
            time.sleep(remaining)
        self.last = time.monotonic()


def start_portal(s, timeout, limiter):
    limiter.wait()
    page = http(s, "GET", PORTAL, timeout).text
    expected = [
        'action="/sisvan/relatoriopublico/estadonutricional"',
        'name="coMunicipioIbge"', 'name="nu_ciclo_vida"',
        'value="1">CRIANÇA', 'value="2">ADOLESCENTE',
        'value="3">ADULTO', 'value="4">IDOSO', 'value="5">GESTANTE',
        'name="nu_indice_cri"', 'name="nu_indice_ado"',
        'name="nu_idade_ges"',
        'value="1">Peso X Idade', 'value="3">Altura X Idade',
        'value="4">IMC X Idade',
    ]
    missing = [x for x in expected if x not in page]
    if missing:
        raise RuntimeError("Formulario SISVAN mudou; ausentes: " + repr(missing))


def fetch_xlsx(
    s, args, limiter, uf, uf_code, payload=None, debug_name=None,
):
    for attempt in range(args.retries + 1):
        limiter.wait()
        response = http(
            s, "POST", ENDPOINT,
            (args.connect_timeout, args.read_timeout),
            data=payload or report_payload(args.year, uf_code),
            headers={
                "Referer": PORTAL,
                "Accept": "application/vnd.openxmlformats-officedocument."
                          "spreadsheetml.sheet,*/*;q=0.5",
            },
        )
        if response.content.startswith(b"PK\x03\x04"):
            return response.content
        args.debug_dir.mkdir(parents=True, exist_ok=True)
        kind = response.headers.get("Content-Type", "").lower()
        prefix = debug_name or uf
        debug = args.debug_dir / (
            prefix + "_resposta_invalida"
            + (".html" if "html" in kind else ".bin")
        )
        debug.write_bytes(response.content)
        if attempt == args.retries:
            raise RuntimeError("Resposta SISVAN invalida; debug: %s" % debug)
        delay = min(60, 2 ** attempt)
        print("  resposta invalida; retry em %ss; debug: %s" % (delay, debug))
        time.sleep(delay)
    raise AssertionError("tentativas esgotadas")


def parse_count(value):
    """Corrige o XLSX que grava 1.234 pessoas como numero decimal 1.234."""
    if value is None or value == "" or isinstance(value, bool):
        raise ValueError("contagem invalida: %r" % value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value) or value < 0:
            raise ValueError("contagem invalida: %r" % value)
        return int(value) if value.is_integer() else round(value * 1000)
    text = str(value).strip()
    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", text):
        text = text.replace(".", "")
    if not text.isdigit():
        raise ValueError("contagem invalida: %r" % value)
    return int(text)


def count_candidates(value):
    """Possiveis inteiros quando 2.000 foi gravado no XLSX como numero 2."""
    base = parse_count(value)
    integral_source = (
        isinstance(value, int)
        or (isinstance(value, float) and value.is_integer())
        or bool(re.fullmatch(r"\d+", str(value).strip()))
    )
    return [base, base * 1000] if integral_source and base > 0 else [base]


def parse_percent(value):
    text = str(value).strip()
    # O exportador usa "-" quando a categoria tem zero casos.
    if text in {"-", "–", "—"}:
        return 0.0
    number = float(text.replace("%", "").replace(",", "."))
    if not 0 <= number <= 100:
        raise ValueError("percentual invalido: %r" % value)
    return number


def municipal_code(value):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    text = str(number)
    return text if re.fullmatch(r"\d{6}", text) else None
