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
        return "A maximum of 6 days."


def test_service_builds_index_and_guarantees_citation(tmp_path, monkeypatch):
    monkeypatch.setenv("MEDIA_AUTO_PROCESS_ON_INDEX", "false")
    project = Path(__file__).resolve().parents[1]
    settings = Settings(
        ollama_base_url="http://localhost:11434",
        chat_model="fake-chat",
        embed_model="fake-embed",
        data_dir=project / "sample_data" / "northstar_rag_dummy_dataset",
        index_dir=tmp_path / "index",
        top_k=6,
        min_relevance=0.1,
    )
    service = RAGService(settings, client=FakeOllamaClient())
    manifest = service.build_index()
    assert manifest.source_count >= 16
    assert manifest.errors == []

    answer = service.answer("How many unused annual-leave days may be carried forward?")
    assert answer.text.endswith("[S1]")
    assert any("Leave" in result.chunk.title for result in answer.results)

    refusal = service.answer("What dental insurance plan does Northstar provide?")
    assert refusal.refused
    assert refusal.text == REFUSAL
