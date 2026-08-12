from __future__ import annotations

import hashlib
import re

from .models import Chunk, SourceDocument


def _stable_id(document: SourceDocument, part: int, text: str) -> str:
    value = f"{document.source_path}|{document.locator}|{part}|{text[:80]}"
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:16]


def split_document(
    document: SourceDocument,
    max_words: int = 260,
    overlap_words: int = 45,
) -> list[Chunk]:
    cleaned = re.sub(r"[ \t]+", " ", document.text).strip()
    if not cleaned:
        return []
    words = cleaned.split()
    if len(words) <= max_words:
        return [
            Chunk(
                chunk_id=_stable_id(document, 0, cleaned),
                text=cleaned,
                title=document.title,
                source_path=document.source_path,
                source_type=document.source_type,
                locator=document.locator,
                source_url=document.source_url,
                metadata=document.metadata,
            )
        ]

    chunks: list[Chunk] = []
    start = 0
    part = 1
    while start < len(words):
        end = min(start + max_words, len(words))
        text = " ".join(words[start:end])
        locator = f"{document.locator}; part {part}" if document.locator else f"part {part}"
        chunks.append(
            Chunk(
                chunk_id=_stable_id(document, part, text),
                text=text,
                title=document.title,
                source_path=document.source_path,
                source_type=document.source_type,
                locator=locator,
                source_url=document.source_url,
                metadata=document.metadata,
            )
        )
        if end == len(words):
            break
        start = end - overlap_words
        part += 1
    return chunks


def chunk_documents(documents: list[SourceDocument]) -> list[Chunk]:
    chunks: list[Chunk] = []
    for document in documents:
        chunks.extend(split_document(document))
    return chunks
