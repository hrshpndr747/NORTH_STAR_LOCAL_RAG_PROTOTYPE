from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _path_from_env(name: str, default: str) -> Path:
    value = Path(os.getenv(name, default)).expanduser()
    return value if value.is_absolute() else PROJECT_ROOT / value


@dataclass(frozen=True)
class Settings:
    ollama_base_url: str
    chat_model: str
    embed_model: str
    data_dir: Path
    index_dir: Path
    top_k: int
    min_relevance: float

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv(PROJECT_ROOT / ".env")
        return cls(
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/"),
            chat_model=os.getenv("OLLAMA_CHAT_MODEL", "qwen3.5:4b"),
            embed_model=os.getenv("OLLAMA_EMBED_MODEL", "qwen3-embedding:0.6b"),
            data_dir=_path_from_env("DATA_DIR", "sample_data/northstar_rag_dummy_dataset"),
            index_dir=_path_from_env("INDEX_DIR", ".rag_index"),
            top_k=max(1, int(os.getenv("TOP_K", "6"))),
            min_relevance=float(os.getenv("MIN_RELEVANCE", "0.18")),
        )
