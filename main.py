"""
main.py — Ponto de entrada da aplicação News Scraper.

Uso:
    python main.py scrape          # raspa todas as fontes e salva no banco
    python main.py list            # exibe as 20 manchetes mais recentes
    python main.py search <termo>  # busca manchetes por palavra-chave
    python main.py stats           # exibe estatísticas do banco
"""

import argparse
import logging
import sys

from datetime import datetime, timedelta

from database import init_db, HeadlineRepository
from models import Headline
from scraper import scrape_all

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("main")


# ── Comandos ──────────────────────────────────────────────────────────────────

def cmd_scrape(_args: argparse.Namespace) -> None:
    """Raspa todas as fontes configuradas e persiste no banco."""
    init_db()
    all_results = scrape_all()

    total_inserted = total_duplicated = 0

    for source_name, headlines in all_results.items():
        if not headlines:
            logger.warning("Nenhuma manchete obtida de '%s'.", source_name)
            continue

        inserted, duplicated = HeadlineRepository.bulk_insert(headlines)
        total_inserted += inserted
        total_duplicated += duplicated

        print(
            f"  ✔  {source_name:30s} "
            f"→ {inserted:3d} nova(s) | {duplicated:3d} duplicada(s)"
        )

    print(
        f"\n📦  Total: {total_inserted} manchete(s) inserida(s), "
        f"{total_duplicated} já existiam no banco."
    )


def cmd_list(args: argparse.Namespace) -> None:
    """Lista as manchetes mais recentes."""
    init_db()
    limit = getattr(args, "limit", 20)
    headlines = HeadlineRepository.find_all(limit=limit)

    if not headlines:
        print("Banco vazio. Execute: python main.py scrape")
        return

    print(f"\n{'#':>4}  {'Fonte':<22}  {'Título'}")
    print("─" * 80)
    for i, h in enumerate(headlines, 1):
        print(f"{i:>4}  {h.source:<22}  {h.title[:52]}")
    print(f"\n{len(headlines)} manchete(s) exibida(s).")


def cmd_search(args: argparse.Namespace) -> None:
    """Busca manchetes pelo título."""
    init_db()
    keyword = args.keyword
    results = HeadlineRepository.search(keyword)

    if not results:
        print(f'Nenhuma manchete encontrada para "{keyword}".')
        return

    print(f'\n🔍  Resultados para "{keyword}":\n')
    for h in results:
        print(f"  [{h.source}]  {h.title}")
        print(f"   └─ {h.url}\n")


def cmd_seed(_args: argparse.Namespace) -> None:
    """Popula o banco com manchetes de exemplo (útil para testes)."""
    init_db()
    now = datetime.utcnow()
    mock_data = [
        ("Hacker News", "Show HN: I built a Rust-based SQLite replacement",
         "https://news.ycombinator.com/item?id=40001001", now - timedelta(minutes=5)),
        ("Hacker News", "Why Python 3.13 is faster than C++ in some benchmarks",
         "https://news.ycombinator.com/item?id=40001002", now - timedelta(minutes=12)),
        ("Hacker News", "Ask HN: Best resources for learning distributed systems in 2025?",
         "https://news.ycombinator.com/item?id=40001003", now - timedelta(minutes=30)),
        ("Hacker News", "OpenAI releases o4-mini with 1M context window",
         "https://news.ycombinator.com/item?id=40001004", now - timedelta(hours=1)),
        ("Hacker News", "The Death of the Junior Developer Position",
         "https://news.ycombinator.com/item?id=40001005", now - timedelta(hours=2)),
        ("G1 - Últimas Notícias", "Banco Central eleva taxa Selic para 14,75% ao ano",
         "https://g1.globo.com/economia/noticia/selic-1.html", now - timedelta(minutes=8)),
        ("G1 - Últimas Notícias", "Copa do Mundo 2026: seleção brasileira convocada com 6 novos nomes",
         "https://g1.globo.com/esportes/copa-2026.html", now - timedelta(minutes=20)),
        ("G1 - Últimas Notícias", "Incêndios no Pantanal: área queimada é 40% maior que 2024",
         "https://g1.globo.com/natureza/pantanal.html", now - timedelta(hours=3)),
        ("G1 - Últimas Notícias", "STF decide sobre descriminalização do porte de maconha",
         "https://g1.globo.com/politica/stf-maconha.html", now - timedelta(hours=4)),
        ("G1 - Últimas Notícias", "Receita Federal libera consulta ao lote de restituição do IR 2025",
         "https://g1.globo.com/economia/ir-restituicao.html", now - timedelta(hours=5)),
    ]

    headlines = [
        Headline(title=title, url=url, source=src, scraped_at=ts)
        for src, title, url, ts in mock_data
    ]

    inserted, duplicated = HeadlineRepository.bulk_insert(headlines)
    print(f"\n🌱  Seed concluído: {inserted} inserida(s), {duplicated} duplicada(s).")


def cmd_stats(_args: argparse.Namespace) -> None:
    """Exibe estatísticas do banco."""
    init_db()
    total = HeadlineRepository.count()
    by_source = HeadlineRepository.count_by_source()

    print(f"\n📊  Estatísticas — {total} manchete(s) no banco\n")
    print(f"  {'Fonte':<30}  {'Total':>6}")
    print("  " + "─" * 40)
    for source, count in sorted(by_source.items(), key=lambda x: -x[1]):
        print(f"  {source:<30}  {count:>6}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="news_scraper",
        description="Raspador de manchetes de notícias com persistência em SQLite.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # seed
    sub.add_parser("seed", help="Popula o banco com manchetes de exemplo.")

    # scrape
    sub.add_parser("scrape", help="Raspa as fontes e salva manchetes no banco.")

    # list
    p_list = sub.add_parser("list", help="Lista as manchetes mais recentes.")
    p_list.add_argument(
        "--limit", type=int, default=20, help="Quantidade de manchetes (padrão: 20)."
    )

    # search
    p_search = sub.add_parser("search", help="Busca manchetes por palavra-chave.")
    p_search.add_argument("keyword", help="Termo a pesquisar.")

    # stats
    sub.add_parser("stats", help="Estatísticas do banco.")

    return parser


COMMANDS = {
    "scrape": cmd_scrape,
    "seed":   cmd_seed,
    "list":   cmd_list,
    "search": cmd_search,
    "stats":  cmd_stats,
}


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    handler = COMMANDS.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
