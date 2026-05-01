"""
models/headline.py — Modelo de domínio para uma manchete.
Representa a entidade central da aplicação usando dataclass.
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Headline:
    """Representa uma manchete extraída de uma fonte de notícias."""

    title: str
    url: str
    source: str
    scraped_at: datetime = field(default_factory=datetime.utcnow)
    id: int | None = None

    def __post_init__(self) -> None:
        self.title = self.title.strip()
        self.url = self.url.strip()
        if not self.title:
            raise ValueError("O título não pode ser vazio.")
        if not self.url:
            raise ValueError("A URL não pode ser vazia.")

    def __repr__(self) -> str:
        return f"Headline(source={self.source!r}, title={self.title[:60]!r})"
