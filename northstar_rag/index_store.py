from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from .models import Chunk


@dataclass
class IndexManifest:
    created_at: str
    embedding_model: str
    chunk_count: int
    source_count: int
    errors: list[str]


class IndexStore:
    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.chunks_path = directory / "chunks.json"
        self.embeddings_path = directory / "embeddings.npy"
        self.manifest_path = directory / "manifest.json"

    def exists(self) -> bool:
        return self.chunks_path.exists() and self.embeddings_path.exists() and self.manifest_path.exists()

    def save(self, chunks: list[Chunk], embeddings: np.ndarray, embedding_model: str, errors: list[str]) -> IndexManifest:
        if len(chunks) != len(embeddings):
            raise ValueError("Chunk and embedding counts do not match.")
        self.directory.mkdir(parents=True, exist_ok=True)
        manifest = IndexManifest(
            created_at=datetime.now(timezone.utc).isoformat(),
            embedding_model=embedding_model,
            chunk_count=len(chunks),
            source_count=len({chunk.source_path for chunk in chunks}),
            errors=errors,
        )
        self.chunks_path.write_text(
            json.dumps([chunk.to_dict() for chunk in chunks], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        np.save(self.embeddings_path, embeddings.astype(np.float32))
        self.manifest_path.write_text(json.dumps(asdict(manifest), indent=2), encoding="utf-8")
        return manifest

    def load(self) -> tuple[list[Chunk], np.ndarray, IndexManifest]:
        if not self.exists():
            raise FileNotFoundError("The RAG index has not been built yet.")
        chunks = [Chunk.from_dict(item) for item in json.loads(self.chunks_path.read_text(encoding="utf-8"))]
        embeddings = np.load(self.embeddings_path, allow_pickle=False)
        manifest = IndexManifest(**json.loads(self.manifest_path.read_text(encoding="utf-8")))
        if len(chunks) != len(embeddings):
            raise ValueError("The saved index is inconsistent. Rebuild it.")
        return chunks, embeddings, manifest

