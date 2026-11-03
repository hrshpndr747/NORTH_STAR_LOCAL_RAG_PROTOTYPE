from pathlib import Path

import numpy as np

from northstar_rag.config import Settings
from northstar_rag.service import REFUSAL, RAGService


class FakeOllamaClient:
    def embed(self, texts, model, batch_size=24):
        values = list(texts)
        return np.tile(np.array([[1.0, 0.0]], dtype=np.float32), (len(values), 1))

    def chat(self, model, messages, temperature=0.1):
        question = messages[-1]["content"].lower()
        if "dental" in question:
            return REFUSAL
        return "Claims must be reported within 48 hours."


def test_service_builds_index_and_guarantees_citation(tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_AUTO_PROCESS_ON_INDEX", "false")
    project = Path(__file__).resolve().parents[1]
    settings = Settings(
        ollama_base_url="http://localhost:11434",
        chat_model="fake-chat",
        embed_model="fake-embed",
        data_dir=project / "data" / "confluence",
        index_dir=tmp_path / "index",
        top_k=6,
        min_relevance=0.1,
    )
    service = RAGService(settings, client=FakeOllamaClient())
    manifest = service.build_index()
    assert manifest.source_count >= 5
    assert manifest.errors == []

    answer = service.answer("What is the claims handling manual procedure?")
    assert answer.text.endswith("[S1]")
    assert len(answer.results) > 0

    refusal = service.answer("What dental insurance plan does Northstar provide?")
    assert refusal.refused
    assert refusal.text == REFUSAL
