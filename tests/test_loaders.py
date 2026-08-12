from pathlib import Path

from northstar_rag.loaders import load_docx, load_pdf, load_sqlite, load_vtt, load_xlsx


ROOT = Path(__file__).resolve().parents[1] / "sample_data" / "northstar_rag_dummy_dataset"


def test_all_major_source_types_load():
    pages = ROOT / "01_Confluence_Pages"
    attachments = ROOT / "02_Attachments"
    assert "18 working days" in load_docx(pages / "03_Leave_and_Holiday_Policy.docx", ROOT)[0].text
    assert any("30 minutes" in item.text for item in load_pdf(attachments / "IT_Incident_Response_Handbook.pdf", ROOT))
    assert any("phishing" in item.text.lower() for item in load_vtt(attachments / "Security_Awareness_Training.vtt", ROOT))
    assert any("Total data rows: 100" in item.text for item in load_xlsx(attachments / "Service_Desk_Tickets_Q2_2026.xlsx", ROOT))
    assert any("Total rows: 60" in item.text for item in load_sqlite(attachments / "support_operations.db", ROOT))

