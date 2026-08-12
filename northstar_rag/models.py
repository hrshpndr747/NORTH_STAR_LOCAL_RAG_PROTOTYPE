from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class SourceDocument:
    text: str
    title: str
    source_path: str
    source_type: str
    locator: str = ""
    source_url: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Chunk:
    chunk_id: str
    text: str
    title: str
    source_path: str
    source_type: str
    locator: str = ""
    source_url: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Chunk":
        return cls(**value)


@dataclass
class SearchResult:
    chunk: Chunk
    score: float
    semantic_score: float
    lexical_score: float


@dataclass
class Answer:
    text: str
    results: list[SearchResult]
    refused: bool = False
    sql_used: str = ""

