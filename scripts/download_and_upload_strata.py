import os
import sys
import mimetypes
from pathlib import Path
import requests
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")

BASE_URL = os.environ["CONFLUENCE_BASE_URL"].rstrip("/")
EMAIL = os.environ["CONFLUENCE_EMAIL"]
API_TOKEN = os.environ["CONFLUENCE_API_TOKEN"]
SPACE_KEY = os.environ["CONFLUENCE_SPACE_KEY"]
SPACE_ID = "163842"  # Personal space ID
PARENT_PAGE_ID = "163934"  # Overview page ID

FILES_TO_DOWNLOAD = [
    # Knowledge base documents
    "kb/claims-handling-manual.docx",
    "kb/customer-faq.md",
    "kb/underwriting-guidelines.md",
    # Tabular / spreadsheets
    "tabular/commission-summary.csv",
    "tabular/loss-run.xlsx",
    "tabular/premium-register.xlsx",
    # Claim documents & reports
    "claim/C-1000-adjuster-report.pdf",
    "claim/C-1000-fnol.pdf",
    "claim/C-1000-settlement-letter.pdf",
    # Scanned document for OCR
    "claim/C-1000-fnol-scanned.jpg",
    # Policy documents
    "policy/COM-0000003-contract.docx",
    "policy/COM-0000003-declarations.pdf",
    "policy/COM-0000003-schedule.pdf",
]

HF_BASE = "https://huggingface.co/datasets/NikolaiSachok/strata-insurance-corpus/resolve/main/docs"
STAGING_DIR = PROJECT_ROOT / "data" / "staging_strata"


def download_dataset():
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    downloaded = []
    print(f"--- 1. Downloading sample files from Hugging Face ---")
    for relative_path in FILES_TO_DOWNLOAD:
        url = f"{HF_BASE}/{relative_path}"
        filename = Path(relative_path).name
        target = STAGING_DIR / filename
        print(f"Downloading {filename}...")
        resp = requests.get(url, stream=True, timeout=60)
        resp.raise_for_status()
        with open(target, "wb") as f:
            for chunk in resp.iter_content(chunk_size=64 * 1024):
                if chunk:
                    f.write(chunk)
        print(f"  Saved {filename} ({target.stat().st_size} bytes)")
        downloaded.append(target)
    return downloaded


def get_or_create_page(session):
    print("\n--- 2. Checking / Creating Confluence Page ---")
    search_url = f"{BASE_URL}/wiki/api/v2/spaces/{SPACE_ID}/pages"
    resp = session.get(search_url, params={"title": "Strata Insurance Corpus"}, timeout=30)
    resp.raise_for_status()
    results = resp.json().get("results", [])
    if results:
        page_id = str(results[0]["id"])
        print(f"Found existing page 'Strata Insurance Corpus' (ID: {page_id})")
        return page_id

    create_url = f"{BASE_URL}/wiki/api/v2/pages"
    payload = {
        "spaceId": SPACE_ID,
        "parentId": PARENT_PAGE_ID,
        "status": "current",
        "title": "Strata Insurance Corpus",
        "body": {
            "representation": "storage",
            "value": (
                "<p><strong>Strata Insurance Knowledge Base &amp; Dataset</strong></p>"
                "<p>This page holds the sample corpus of insurance contracts, underwriting manuals, "
                "claims reports, settlement letters, and policy schedules for testing local RAG.</p>"
            ),
        },
    }
    resp = session.post(create_url, json=payload, headers={"Content-Type": "application/json", "Accept": "application/json"}, timeout=30)
    resp.raise_for_status()
    new_page = resp.json()
    page_id = str(new_page["id"])
    print(f"Created page 'Strata Insurance Corpus' (ID: {page_id})")
    return page_id


def upload_attachments(session, page_id, files):
    print(f"\n--- 3. Uploading attachments to Confluence Page {page_id} ---")
    # Get existing attachments
    existing = {}
    att_url = f"{BASE_URL}/wiki/api/v2/pages/{page_id}/attachments"
    resp = session.get(att_url, params={"limit": 100}, timeout=30)
    if resp.ok:
        for att in resp.json().get("results", []):
            existing[att.get("title")] = str(att.get("id"))

    headers = {"X-Atlassian-Token": "no-check"}
    for file_path in files:
        filename = file_path.name
        mime_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        if filename in existing:
            att_id = existing[filename]
            url = f"{BASE_URL}/wiki/rest/api/content/{page_id}/child/attachment/{att_id}/data"
            action = "Updating"
        else:
            url = f"{BASE_URL}/wiki/rest/api/content/{page_id}/child/attachment"
            action = "Uploading"

        print(f"{action} {filename}...")
        with open(file_path, "rb") as f:
            files_data = {"file": (filename, f, mime_type)}
            data = {"comment": "Strata Insurance Corpus dataset upload"}
            r = session.post(url, headers=headers, files=files_data, data=data, timeout=60)
            r.raise_for_status()
            print(f"  [OK] {filename}")


if __name__ == "__main__":
    downloaded_files = download_dataset()
    session = requests.Session()
    session.auth = (EMAIL, API_TOKEN)
    page_id = get_or_create_page(session)
    upload_attachments(session, page_id, downloaded_files)
    print("\nDataset successfully uploaded to Confluence!")
