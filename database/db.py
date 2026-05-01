"""
database/db.py — Camada de persistência com SQLite.

Aplica o padrão Repository: a lógica de acesso a dados fica isolada aqui,
sem vazar para o restante da aplicação.
"""

import sqlite3
import logging
from contextlib import contextmanager
from datetime import datetime
from typing import Generator

from models.headline import Headline
import config

logger = logging.getLogger(__name__)


# ── Gerenciador de conexão ────────────────────────────────────────────────────

@contextmanager
def get_connection() -> Generator[sqlite3.Connection, None, None]:
    """Context manager que garante fechamento seguro da conexão."""
    conn = sqlite3.connect(config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row          # acesso por nome de coluna
    conn.execute("PRAGMA journal_mode=WAL") # melhor concorrência
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── Inicialização do schema ───────────────────────────────────────────────────

def init_db() -> None:
    """Cria as tabelas caso ainda não existam (idempotente)."""
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS headlines (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT    NOT NULL,
                url         TEXT    NOT NULL UNIQUE,
                source      TEXT    NOT NULL,
                scraped_at  TEXT    NOT NULL
            )
            """
        )
    logger.info("Banco de dados inicializado em '%s'.", config.DATABASE_PATH)


# ── Repositório ───────────────────────────────────────────────────────────────

class HeadlineRepository:
    """Encapsula todas as operações CRUD para a entidade Headline."""

    # ── Escrita ───────────────────────────────────────────────────────────────

    @staticmethod
    def insert(headline: Headline) -> bool:
        """
        Insere uma manchete.
        Retorna True se inserida, False se já existia (url duplicada).
        """
        try:
            with get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO headlines (title, url, source, scraped_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        headline.title,
                        headline.url,
                        headline.source,
                        headline.scraped_at.isoformat(),
                    ),
                )
            return True
        except sqlite3.IntegrityError:
            # Violação de UNIQUE na url — manchete já registrada
            logger.debug("Manchete duplicada ignorada: %s", headline.url)
            return False

    @staticmethod
    def bulk_insert(headlines: list[Headline]) -> tuple[int, int]:
        """
        Insere uma lista de manchetes em lote.
        Retorna (inseridas, duplicadas).
        """
        inserted = duplicated = 0
        for h in headlines:
            if HeadlineRepository.insert(h):
                inserted += 1
            else:
                duplicated += 1
        return inserted, duplicated

    # ── Leitura ───────────────────────────────────────────────────────────────

    @staticmethod
    def find_all(limit: int = 50, offset: int = 0) -> list[Headline]:
        """Retorna manchetes ordenadas pela mais recente."""
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, title, url, source, scraped_at
                FROM   headlines
                ORDER  BY scraped_at DESC
                LIMIT  ? OFFSET ?
                """,
                (limit, offset),
            ).fetchall()
        return [_row_to_headline(r) for r in rows]

    @staticmethod
    def find_by_source(source: str, limit: int = 50) -> list[Headline]:
        """Filtra manchetes por nome de fonte."""
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, title, url, source, scraped_at
                FROM   headlines
                WHERE  source = ?
                ORDER  BY scraped_at DESC
                LIMIT  ?
                """,
                (source, limit),
            ).fetchall()
        return [_row_to_headline(r) for r in rows]

    @staticmethod
    def search(keyword: str, limit: int = 20) -> list[Headline]:
        """Busca manchetes cujo título contenha a palavra-chave (case-insensitive)."""
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, title, url, source, scraped_at
                FROM   headlines
                WHERE  LOWER(title) LIKE LOWER(?)
                ORDER  BY scraped_at DESC
                LIMIT  ?
                """,
                (f"%{keyword}%", limit),
            ).fetchall()
        return [_row_to_headline(r) for r in rows]

    @staticmethod
    def count() -> int:
        """Retorna o total de manchetes armazenadas."""
        with get_connection() as conn:
            return conn.execute("SELECT COUNT(*) FROM headlines").fetchone()[0]

    @staticmethod
    def count_by_source() -> dict[str, int]:
        """Retorna um dicionário {fonte: quantidade}."""
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT source, COUNT(*) AS total FROM headlines GROUP BY source"
            ).fetchall()
        return {r["source"]: r["total"] for r in rows}


# ── Helpers privados ──────────────────────────────────────────────────────────

def _row_to_headline(row: sqlite3.Row) -> Headline:
    return Headline(
        id=row["id"],
        title=row["title"],
        url=row["url"],
        source=row["source"],
        scraped_at=datetime.fromisoformat(row["scraped_at"]),
    )
