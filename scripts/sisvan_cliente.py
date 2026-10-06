"""Acesso aos relatórios SISVAN de altura e peso de menores de cinco anos."""

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
    session = requests.Session()
    session.mount("https://", adapter)
    session.headers.update({
        "User-Agent": "pesquisa-academica-sisvan/6.0 (+%s)" % PORTAL,
        "Accept-Language": "pt-BR,pt;q=0.9",
    })
    return session


def http(session, method, url, timeout, **kwargs):
    response = session.request(method, url, timeout=timeout, **kwargs)
    if response.status_code == 429:
        raise RuntimeError("HTTP 429; Retry-After=" + response.headers.get("Retry-After", "?"))
    response.raise_for_status()
    return response


def report_payload(year, uf, index_code):
    # Campos não utilizados no recorte conservam os valores do formulário.
    # coMunicipioIbge=99 é necessário para obter linhas por município.
    return {
        "excel": "1", "tpRelatorio": "2", "coVisualizacao": "3",
        "nuAno": str(year), "nuMes[]": "99", "tpFiltro": "M",
        "coRegiao": "99", "coUfIbge": uf, "coMunicipioIbge": "99",
        "noRegional": "", "st_cobertura": "99", "nu_ciclo_vida": "1",
        "nu_idade_inicio": "0", "nu_idade_fim": "5",
        "nu_indice_cri": str(index_code), "nu_indice_ado": "1",
        "nu_idade_ges": "99", "ds_sexo2": "1", "ds_raca_cor2": "99",
        "co_sistema_origem": "0", "CO_POVO_COMUNIDADE": "TODOS",
        "CO_ESCOLARIDADE": "TODOS", "tpAbrangencia": "M", "tpAbrangenciaEas": "",
    }


class Limiter:
    def __init__(self, interval):
        self.interval, self.last = interval, 0

    def wait(self):
        remaining = self.interval - (time.monotonic() - self.last)
        if remaining > 0:
            time.sleep(remaining)
        self.last = time.monotonic()


def start_portal(session, timeout, limiter):
    limiter.wait()
    page = http(session, "GET", PORTAL, timeout).text
    expected = (
        'action="/sisvan/relatoriopublico/estadonutricional"',
        'name="coMunicipioIbge"', 'name="nu_ciclo_vida"',
        'value="1">CRIANÇA', 'name="nu_indice_cri"',
        'name="nu_idade_inicio"', 'name="nu_idade_fim"',
        'value="1">Peso X Idade', 'value="3">Altura X Idade',
    )
    missing = [field for field in expected if field not in page]
    if missing:
        raise RuntimeError("Formulário SISVAN mudou; ausentes: " + repr(missing))


def fetch_xlsx(session, args, limiter, payload, debug_name):
    for attempt in range(args.retries + 1):
        limiter.wait()
        response = http(
            session, "POST", ENDPOINT,
            (args.connect_timeout, args.read_timeout), data=payload,
            headers={"Referer": PORTAL, "Accept": (
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,*/*;q=0.5")},
        )
        if response.content.startswith(b"PK\x03\x04"):
            return response.content
        kind = response.headers.get("Content-Type", "").lower()
        debug = args.debug_dir / (debug_name + "_resposta_invalida" + (
            ".html" if "html" in kind else ".bin"))
        debug.parent.mkdir(parents=True, exist_ok=True)
        debug.write_bytes(response.content)
        if attempt == args.retries:
            raise RuntimeError("Resposta SISVAN inválida; debug: " + str(debug))
        delay = min(60, 2 ** attempt)
        print(f"  resposta inválida; retry em {delay}s; debug: {debug}")
        time.sleep(delay)
    raise AssertionError("Tentativas esgotadas")


def parse_percent(value):
    text = str(value).strip()
    if text in {"-", "–", "—"}:
        return 0.0
    number = float(text.replace("%", "").replace(",", "."))
    if not 0 <= number <= 100:
        raise ValueError("Percentual inválido: " + text)
    return number


def municipal_code(value):
    try:
        number = int(value)
    except (TypeError, ValueError, OverflowError):
        return None
    text = str(number)
    return text if re.fullmatch(r"\d{6}", text) else None
