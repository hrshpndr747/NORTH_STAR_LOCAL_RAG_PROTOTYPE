from __future__ import annotations

import csv
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from northstar_rag import RAGService, Settings


def source_matches(expected: str, retrieved: list[str]) -> bool:
    expected_lower = expected.lower()
    if "no supporting source" in expected_lower:
        return True
    significant = [
        word
        for word in expected_lower.replace("_", " ").replace("-", " ").split()
        if len(word) > 4 and word not in {"source", "sheet", "document", "database"}
    ]
    joined = " ".join(retrieved).lower().replace("_", " ")
    return any(word in joined for word in significant)


if __name__ == "__main__":
    settings = Settings.from_env()
    service = RAGService(settings)
    if not service.store.exists():
        print("No index found; building it first.")
        service.build_index()
    questions = settings.data_dir / "03_Evaluation" / "rag_evaluation_questions.csv"
    rows = list(csv.DictReader(questions.open("r", encoding="utf-8-sig", newline="")))
    hits = 0
    for row in rows:
        if row["answer_supported"].lower() != "true":
            continue
        results = service.retrieve(row["question"], top_k=6)
        sources = [f"{item.chunk.title} {item.chunk.source_path} {item.chunk.locator}" for item in results]
        matched = source_matches(row["expected_source"], sources)
        hits += int(matched)
        print(f"{row['question_id']}: {'PASS' if matched else 'MISS'} — {sources[0] if sources else 'none'}")
    supported = sum(row["answer_supported"].lower() == "true" for row in rows)
    print(f"Source retrieval: {hits}/{supported} ({hits / supported:.1%})")

