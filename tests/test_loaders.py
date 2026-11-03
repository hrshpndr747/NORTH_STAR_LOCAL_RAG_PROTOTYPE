import sqlite3
from pathlib import Path

from northstar_rag.loaders import load_docx, load_pdf, load_sqlite, load_vtt, load_xlsx


ROOT = Path(__file__).resolve().parents[1] / "data" / "confluence"


def test_all_major_source_types_load(tmp_path):
    attachments = ROOT / "attachments" / "425986"
    assert len(load_docx(attachments / "claims-handling-manual.docx", ROOT)) >= 1
    assert any("Notice of Loss" in item.text or "FNOL" in item.text for item in load_pdf(attachments / "C-1000-fnol.pdf", ROOT))
    assert any("Total data rows:" in item.text for item in load_xlsx(attachments / "loss-run.xlsx", ROOT))

    # Test SQLite loader with self-contained fixture
    db_file = tmp_path / "test.db"
    conn = sqlite3.connect(db_file)
    conn.execute("CREATE TABLE tickets (id INTEGER, subject TEXT)")
    conn.execute("INSERT INTO tickets VALUES (1, 'Login failure')")
    conn.commit()
    conn.close()
    assert any("Total rows: 1" in item.text for item in load_sqlite(db_file, tmp_path))

    # Test VTT loader with self-contained fixture
    vtt_file = tmp_path / "test.vtt"
    vtt_file.write_text("WEBVTT\n\n00:00:01.000 --> 00:00:04.000\nPhishing awareness and security training.\n", encoding="utf-8")
    assert any("phishing" in item.text.lower() for item in load_vtt(vtt_file, tmp_path))

