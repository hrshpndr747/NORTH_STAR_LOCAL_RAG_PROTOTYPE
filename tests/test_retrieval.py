import numpy as np

from northstar_rag.models import Chunk
from northstar_rag.retrieval import HybridRetriever


def test_hybrid_retrieval_uses_exact_terms():
    chunks = [
        Chunk("1", "Unused annual leave carry forward is limited to 6 days.", "Leave Policy", "leave.docx", "word"),
        Chunk("2", "The incident commander runs the technical bridge.", "Incident Handbook", "incident.pdf", "pdf"),
        Chunk("3", "Domestic hotel reimbursement is INR 6,500 per night.", "Expense Guide", "expense.pdf", "pdf"),
    ]
    embeddings = np.eye(3, dtype=np.float32)
    retriever = HybridRetriever(chunks, embeddings, semantic_weight=0.2)
    results = retriever.search("How many annual leave days can be carried forward?", np.array([1, 0, 0], dtype=np.float32))
    assert results[0].chunk.chunk_id == "1"
    assert results[0].lexical_score == 1.0

