"""
scraper/scraper.py — Lógica de web scraping.

Responsabilidade única: fazer requisições HTTP e extrair manchetes do HTML.
Não conhece banco de dados; devolve objetos Headline para a camada acima.
"""

import logging
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

import config
from models.headline import Headline

logger = logging.getLogger(__name__)


# ── Exceções do domínio ───────────────────────────────────────────────────────

class ScraperError(Exception):
    """Erro base do módulo scraper."""


class FetchError(ScraperError):
    """Falha ao buscar a página."""


class ParseError(ScraperError):
    """Falha ao interpretar o HTML."""


# ── Funções públicas ──────────────────────────────────────────────────────────

def fetch_html(url: str) -> str:
    """
    Faz o download do HTML de *url*.
    Lança FetchError em caso de falha de rede ou HTTP >= 400.
    """
    try:
        response = requests.get(
            url,
            headers=config.REQUEST_HEADERS,
            timeout=config.REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return response.text
    except requests.exceptions.Timeout as exc:
        raise FetchError(f"Timeout ao acessar {url}") from exc
    except requests.exceptions.RequestException as exc:
        raise FetchError(f"Erro de rede ao acessar {url}: {exc}") from exc


def parse_headlines(html: str, source_cfg: dict) -> list[Headline]:
    """
    Extrai manchetes do *html* usando os seletores CSS definidos em *source_cfg*.
    Retorna uma lista (possivelmente vazia) de Headline.
    """
    try:
        soup = BeautifulSoup(html, "html.parser")
        elements = soup.select(source_cfg["title_selector"])
    except Exception as exc:
        raise ParseError(f"Falha ao parsear HTML de {source_cfg['name']}: {exc}") from exc

    headlines: list[Headline] = []
    base_url = source_cfg["url"]

    for el in elements:
        title = el.get_text(strip=True)
        href = el.get("href", "")
        url = href if href.startswith("http") else urljoin(base_url, href)

        if not title or not url:
            continue

        try:
            headlines.append(
                Headline(title=title, url=url, source=source_cfg["name"])
            )
        except ValueError as exc:
            logger.warning("Manchete inválida ignorada: %s", exc)

    logger.info(
        "[%s] %d manchete(s) extraída(s).", source_cfg["name"], len(headlines)
    )
    return headlines


def scrape_source(source_cfg: dict) -> list[Headline]:
    """
    Pipeline completo para uma única fonte:
    fetch → parse → retorna manchetes.
    """
    logger.info("Iniciando scraping de '%s' (%s).", source_cfg["name"], source_cfg["url"])
    html = fetch_html(source_cfg["url"])
    return parse_headlines(html, source_cfg)


def scrape_all(sources: list[dict] | None = None) -> dict[str, list[Headline]]:
    """
    Executa o scraping em todas as fontes configuradas.
    Retorna {nome_fonte: [Headline, ...]}.
    Fontes com erro são registradas no log mas não interrompem as demais.
    """
    sources = sources or config.SOURCES
    results: dict[str, list[Headline]] = {}

    for src in sources:
        try:
            results[src["name"]] = scrape_source(src)
        except ScraperError as exc:
            logger.error("Scraping falhou para '%s': %s", src["name"], exc)
            results[src["name"]] = []

    return results
