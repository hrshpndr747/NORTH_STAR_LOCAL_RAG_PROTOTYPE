from __future__ import annotations

import math
import re
from collections import Counter

import numpy as np

from .models import Chunk, SearchResult


TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]*")


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_PATTERN.findall(text)]


class BM25Index:
    def __init__(self, chunks: list[Chunk], k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self.term_frequencies = [Counter(tokenize(f"{chunk.title} {chunk.text}")) for chunk in chunks]
        self.lengths = [sum(values.values()) for values in self.term_frequencies]
        self.average_length = sum(self.lengths) / max(len(self.lengths), 1)
        document_frequency: Counter[str] = Counter()
        for values in self.term_frequencies:
            document_frequency.update(values.keys())
        total = len(chunks)
        self.idf = {
            term: math.log(1 + (total - frequency + 0.5) / (frequency + 0.5))
            for term, frequency in document_frequency.items()
        }

    def scores(self, query: str) -> np.ndarray:
        query_terms = tokenize(query)
        output = np.zeros(len(self.term_frequencies), dtype=np.float32)
        for index, frequencies in enumerate(self.term_frequencies):
            length = self.lengths[index]
            score = 0.0
            for term in query_terms:
                frequency = frequencies.get(term, 0)
                if not frequency:
                    continue
                numerator = frequency * (self.k1 + 1)
                denominator = frequency + self.k1 * (1 - self.b + self.b * length / max(self.average_length, 1))
                score += self.idf.get(term, 0.0) * numerator / denominator
            output[index] = score
        return output


class HybridRetriever:
    def __init__(self, chunks: list[Chunk], embeddings: np.ndarray, semantic_weight: float = 0.68) -> None:
        if len(chunks) != len(embeddings):
            raise ValueError("Chunk and embedding counts do not match.")
        self.chunks = chunks
        self.embeddings = embeddings
        self.semantic_weight = semantic_weight
        self.bm25 = BM25Index(chunks)

    def search(self, query: str, query_vector: np.ndarray, top_k: int = 6) -> list[SearchResult]:
        vector = np.asarray(query_vector, dtype=np.float32).reshape(-1)
        if self.embeddings.ndim != 2 or vector.shape[0] != self.embeddings.shape[1]:
            raise ValueError("Query embedding dimension does not match the index.")
        semantic = np.maximum(self.embeddings @ vector, 0.0)
        lexical_raw = self.bm25.scores(query)
        lexical = lexical_raw / lexical_raw.max() if lexical_raw.size and lexical_raw.max() > 0 else lexical_raw
        combined = self.semantic_weight * semantic + (1 - self.semantic_weight) * lexical

        ranked = np.argsort(-combined)[: min(top_k, len(self.chunks))]
        return [
            SearchResult(
                chunk=self.chunks[index],
                score=float(combined[index]),
                semantic_score=float(semantic[index]),
                lexical_score=float(lexical[index]),
            )
            for index in ranked
        ]

