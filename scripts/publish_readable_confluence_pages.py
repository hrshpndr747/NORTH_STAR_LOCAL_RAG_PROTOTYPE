import html
import os
import sys
import time
from pathlib import Path
import requests
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")

BASE_URL = os.environ["CONFLUENCE_BASE_URL"].rstrip("/")
EMAIL = os.environ["CONFLUENCE_EMAIL"]
API_TOKEN = os.environ["CONFLUENCE_API_TOKEN"]
SPACE_ID = "163842"
CORPUS_PAGE_ID = "425986"

from northstar_rag.loaders import load_file


def request_with_retry(session, method, url, **kwargs):
    for attempt in range(6):
        resp = session.request(method, url, **kwargs)
        if resp.status_code == 429:
            wait = int(resp.headers.get("Retry-After", 4 + attempt * 2))
            print(f"  Rate limited (429). Waiting {wait}s...")
            time.sleep(wait)
            continue
        resp.raise_for_status()
        return resp
    raise RuntimeError(f"Request failed after retries: {url}")


def update_corpus_parent_page(session):
    print("--- 1. Updating parent page 'Strata Insurance Corpus' with document index ---")
    page_url = f"{BASE_URL}/wiki/api/v2/pages/{CORPUS_PAGE_ID}"
    current = request_with_retry(session, "GET", page_url).json()
    version_num = current["version"]["number"]

    # Get attachments list with their IDs
    att_url = f"{BASE_URL}/wiki/api/v2/pages/{CORPUS_PAGE_ID}/attachments"
    att_resp = request_with_retry(session, "GET", att_url, params={"limit": 100}).json()
    attachments = {a["title"]: a for a in att_resp.get("results", [])}

    def make_link(title, label=None):
        label = label or title
        if title in attachments:
            att_id = attachments[title]["id"]
            preview_url = f"{BASE_URL}/pages/viewpageattachments.action?pageId={CORPUS_PAGE_ID}&preview=%2F{CORPUS_PAGE_ID}%2F{att_id}%2F{title}"
            return f'<a href="{preview_url}"><strong>{html.escape(label)}</strong></a>'
        return f"<strong>{html.escape(label)}</strong>"

    body_html = f"""
<h2>Strata Insurance Knowledge Base &amp; Dataset</h2>
<p>Welcome to the <strong>Strata Insurance Corpus</strong> space. All documents, policy records, claims reports, and registers have been uploaded and indexed into the local RAG engine.</p>

<p><em>Tip: To see all uploaded files in Confluence, click the <strong>&hellip;</strong> (three dots) menu at the top-right and choose <strong>Attachments</strong>, or click any document in the table below to open it directly.</em></p>

<h3>Core Knowledge Base &amp; Policies</h3>
<p>These documents describe standard operating procedures, underwriting rules, and policy contracts:</p>
<table>
<thead>
<tr><th>Document</th><th>Format</th><th>Description</th></tr>
</thead>
<tbody>
<tr><td>{make_link("claims-handling-manual.docx", "Claims Handling Manual")}</td><td>Word (.docx)</td><td>Step-by-step claims lifecycle: FNOL, Assignment, Investigation, Estimate, and Resolution.</td></tr>
<tr><td>{make_link("underwriting-guidelines.md", "Underwriting Guidelines")}</td><td>Markdown (.md)</td><td>Meridian Mutual underwriting limits, eligibility criteria, and endorsements.</td></tr>
<tr><td>{make_link("customer-faq.md", "Customer FAQ")}</td><td>Markdown (.md)</td><td>Frequently asked questions for policyholders on filing claims and coverage.</td></tr>
<tr><td>{make_link("COM-0000003-contract.docx", "Commercial Policy Contract (COM-0000003)")}</td><td>Word (.docx)</td><td>Commercial insurance contract agreement for named insured Plinio Novoa Frutos.</td></tr>
<tr><td>{make_link("COM-0000003-declarations.pdf", "Policy Declarations (COM-0000003)")}</td><td>PDF (.pdf)</td><td>Official coverage declarations, schedule limits, and deductibles.</td></tr>
<tr><td>{make_link("COM-0000003-schedule.pdf", "Policy Schedule (COM-0000003)")}</td><td>PDF (.pdf)</td><td>Itemized endorsements and location coverage details.</td></tr>
</tbody>
</table>

<h3>Claims &amp; Adjuster Reports</h3>
<p>Claim reports, damage appraisals, and settlement correspondence:</p>
<table>
<thead>
<tr><th>Document</th><th>Format</th><th>Description</th></tr>
</thead>
<tbody>
<tr><td>{make_link("C-1000-adjuster-report.pdf", "Adjuster Inspection Report (C-1000)")}</td><td>PDF (.pdf)</td><td>Adjuster on-site inspection findings, damages list, and claim notes.</td></tr>
<tr><td>{make_link("C-1000-fnol.pdf", "First Notice of Loss (C-1000)")}</td><td>PDF (.pdf)</td><td>Digital initial loss report filed by policyholder.</td></tr>
<tr><td>{make_link("C-1000-fnol-scanned.jpg", "Scanned FNOL Claim Form (C-1000)")}</td><td>Scanned Image (.jpg)</td><td>Scanned paper claim form (automatically processed via Local Vision OCR).</td></tr>
<tr><td>{make_link("C-1000-settlement-letter.pdf", "Claim Settlement Letter (C-1000)")}</td><td>PDF (.pdf)</td><td>Final settlement resolution, gross repair amount, deductible, and payout.</td></tr>
</tbody>
</table>

<h3>Financial Registers &amp; Loss Runs</h3>
<p>Tabular data and loss inspection spreadsheets:</p>
<table>
<thead>
<tr><th>Document</th><th>Format</th><th>Description</th></tr>
</thead>
<tbody>
<tr><td>{make_link("commission-summary.csv", "Broker Commission Summary")}</td><td>CSV (.csv)</td><td>Broker commission rates and transaction breakdown.</td></tr>
<tr><td>{make_link("loss-run.xlsx", "Loss Run Register")}</td><td>Excel (.xlsx)</td><td>Historical loss runs, claim statuses, paid amounts, and open reserves.</td></tr>
<tr><td>{make_link("premium-register.xlsx", "Premium Register")}</td><td>Excel (.xlsx)</td><td>Accounting register of premiums invoiced, collected, and unearned.</td></tr>
</tbody>
</table>

<h3>Video &amp; Multimedia Training</h3>
<p>Audio-visual training and explainer materials (sampled at 5-second intervals with Whisper ASR &amp; Vision OCR):</p>
<table>
<thead>
<tr><th>Video File</th><th>Format</th><th>Description</th></tr>
</thead>
<tbody>
<tr><td>{make_link("Employee_Phishing_Training.mp4", "Employee Phishing Training")}</td><td>Video (.mp4)</td><td>Security awareness training video on recognizing and handling phishing emails.</td></tr>
<tr><td>{make_link("The_Insurance_Claims_Process_Explained.mp4", "The Insurance Claims Process Explained")}</td><td>Video (.mp4)</td><td>Video walkthrough and visual explanation of the insurance claims lifecycle.</td></tr>
</tbody>
</table>
"""

    payload = {
        "id": CORPUS_PAGE_ID,
        "status": "current",
        "title": "Strata Insurance Corpus",
        "body": {
            "representation": "storage",
            "value": body_html,
        },
        "version": {
            "number": version_num + 1,
            "message": "Add formatted document table with preview links",
        },
    }

    time.sleep(2)
    request_with_retry(session, "PUT", page_url, json=payload, headers={"Content-Type": "application/json", "Accept": "application/json"})
    print("  [OK] Updated parent page 'Strata Insurance Corpus'.")


def create_child_page(session, title, html_content):
    print(f"Creating / Updating subpage: '{title}'...")
    search_url = f"{BASE_URL}/wiki/api/v2/spaces/{SPACE_ID}/pages"
    time.sleep(2)
    existing = request_with_retry(session, "GET", search_url, params={"title": title}).json().get("results", [])

    if existing:
        page_id = str(existing[0]["id"])
        version_num = existing[0]["version"]["number"]
        update_url = f"{BASE_URL}/wiki/api/v2/pages/{page_id}"
        payload = {
            "id": page_id,
            "status": "current",
            "title": title,
            "body": {
                "representation": "storage",
                "value": html_content,
            },
            "version": {
                "number": version_num + 1,
                "message": "Update page content",
            },
        }
        time.sleep(2)
        request_with_retry(session, "PUT", update_url, json=payload, headers={"Content-Type": "application/json", "Accept": "application/json"})
        print(f"  [OK] Updated existing page '{title}' (ID: {page_id})")
        return page_id

    create_url = f"{BASE_URL}/wiki/api/v2/pages"
    payload = {
        "spaceId": SPACE_ID,
        "parentId": CORPUS_PAGE_ID,
        "status": "current",
        "title": title,
        "body": {
            "representation": "storage",
            "value": html_content,
        },
    }
    time.sleep(2)
    new_page = request_with_retry(session, "POST", create_url, json=payload, headers={"Content-Type": "application/json", "Accept": "application/json"}).json()
    page_id = str(new_page["id"])
    print(f"  [OK] Created new page '{title}' (ID: {page_id})")
    return page_id


def publish_subpages(session):
    print("\n--- 2. Publishing readable subpages in the sidebar ---")
    att_dir = PROJECT_ROOT / "data" / "confluence" / "attachments" / CORPUS_PAGE_ID

    # 1. Customer FAQ
    faq_path = att_dir / "customer-faq.md"
    if faq_path.exists():
        text = faq_path.read_text(encoding="utf-8")
        paragraphs = ["<p>" + html.escape(line).replace("\n", "<br/>") + "</p>" for line in text.split("\n\n") if line.strip()]
        body = "".join(paragraphs)
        create_child_page(session, "Customer FAQ (Claims & Policies)", body)

    # 2. Underwriting Guidelines
    ug_path = att_dir / "underwriting-guidelines.md"
    if ug_path.exists():
        text = ug_path.read_text(encoding="utf-8")
        paragraphs = ["<p>" + html.escape(line).replace("\n", "<br/>") + "</p>" for line in text.split("\n\n") if line.strip()]
        body = "".join(paragraphs)
        create_child_page(session, "Underwriting Guidelines", body)

    # 3. Claims Handling Manual
    chm_path = att_dir / "claims-handling-manual.docx"
    if chm_path.exists():
        docs = load_file(chm_path, chm_path.parent)
        full_text = "\n\n".join(d.text for d in docs)
        paragraphs = ["<p>" + html.escape(line).replace("\n", "<br/>") + "</p>" for line in full_text.split("\n\n") if line.strip()]
        body = "".join(paragraphs)
        create_child_page(session, "Claims Handling Manual", body)

    # 4. Policy COM-0000003 Contract
    pol_path = att_dir / "COM-0000003-contract.docx"
    if pol_path.exists():
        docs = load_file(pol_path, pol_path.parent)
        full_text = "\n\n".join(d.text for d in docs)
        paragraphs = ["<p>" + html.escape(line).replace("\n", "<br/>") + "</p>" for line in full_text.split("\n\n") if line.strip()]
        body = "".join(paragraphs)
        create_child_page(session, "Commercial Policy COM-0000003 Contract", body)


if __name__ == "__main__":
    session = requests.Session()
    session.auth = (EMAIL, API_TOKEN)
    update_corpus_parent_page(session)
    publish_subpages(session)
    print("\nAll Confluence pages updated and readable!")
