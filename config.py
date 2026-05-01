"""
config.py — Configurações globais da aplicação.
Centralize aqui todas as constantes e configurações de ambiente.
"""

import os

# ── Banco de dados ────────────────────────────────────────────────────────────
DATABASE_PATH: str = os.getenv("DB_PATH", "news.db")

# ── Scraper ───────────────────────────────────────────────────────────────────
REQUEST_TIMEOUT: int = 10          # segundos
REQUEST_HEADERS: dict = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; NewsScraper/1.0; +https://github.com/lussfp)"
    )
}

# ── Fontes configuradas ───────────────────────────────────────────────────────
# Cada entrada define: nome, url, seletor CSS do título e seletor do link
SOURCES: list[dict] = [
    {
        "name": "Hacker News",
        "url": "https://news.ycombinator.com",
        "title_selector": "span.titleline > a",
        "link_selector":  "span.titleline > a",
    },
    {
        "name": "G1 - Últimas Notícias",
        "url": "https://g1.globo.com/",
        "title_selector": "a.feed-post-link",
        "link_selector":  "a.feed-post-link",
    },
]
