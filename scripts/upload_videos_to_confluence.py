import html
import mimetypes
import os
import shutil
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
PAGE_ID = "425986"

RAW_VIDEO_DIR = PROJECT_ROOT / "data" / "confluence"
STAGING_DIR = PROJECT_ROOT / "data" / "staging_videos"

VIDEOS = {
    "vidssave.com Employee Phishing Training 720P.mp4": "Employee_Phishing_Training.mp4",
    "vidssave.com The Insurance Claims Process Explained 720P.mp4": "The_Insurance_Claims_Process_Explained.mp4",
}


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


def prepare_videos():
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    prepared = []
    for src_name, clean_name in VIDEOS.items():
        src_path = RAW_VIDEO_DIR / src_name
        dest_path = STAGING_DIR / clean_name
        if src_path.exists():
            print(f"Staging {src_name} -> {clean_name} ({src_path.stat().st_size} bytes)")
            shutil.copy2(src_path, dest_path)
            prepared.append(dest_path)
        elif dest_path.exists():
            print(f"Already staged: {clean_name}")
            prepared.append(dest_path)
        else:
            print(f"Warning: {src_path} not found!")
    return prepared


def upload_to_confluence(session, files):
    print(f"\n--- Uploading videos to Confluence Page {PAGE_ID} ---")
    att_url = f"{BASE_URL}/wiki/api/v2/pages/{PAGE_ID}/attachments"
    att_resp = request_with_retry(session, "GET", att_url, params={"limit": 100}).json()
    existing = {a["title"]: str(a["id"]) for a in att_resp.get("results", [])}

    headers = {"X-Atlassian-Token": "no-check"}
    for file_path in files:
        filename = file_path.name
        mime_type = mimetypes.guess_type(filename)[0] or "video/mp4"
        if filename in existing:
            att_id = existing[filename]
            url = f"{BASE_URL}/wiki/rest/api/content/{PAGE_ID}/child/attachment/{att_id}/data"
            action = "Updating existing"
        else:
            url = f"{BASE_URL}/wiki/rest/api/content/{PAGE_ID}/child/attachment"
            action = "Uploading new"

        print(f"{action} {filename} ({file_path.stat().st_size} bytes)...")
        with file_path.open("rb") as f:
            files_data = {"file": (filename, f, mime_type)}
            data = {"comment": "Uploaded video training material"}
            r = request_with_retry(session, "POST", url, headers=headers, files=files_data, data=data, timeout=120)
            print(f"  [OK] {filename}")
        time.sleep(2)


def cleanup_stray_raw_videos():
    print("\n--- Cleaning up raw loose videos in data/confluence root ---")
    for src_name in VIDEOS.keys():
        stray = RAW_VIDEO_DIR / src_name
        if stray.exists():
            stray.unlink()
            print(f"  Removed loose file: {src_name}")
    if STAGING_DIR.exists():
        shutil.rmtree(STAGING_DIR, ignore_errors=True)
        print("  Cleaned up staging folder.")


if __name__ == "__main__":
    session = requests.Session()
    session.auth = (EMAIL, API_TOKEN)
    files = prepare_videos()
    if not files:
        sys.exit("No video files found to upload.")
    upload_to_confluence(session, files)
    cleanup_stray_raw_videos()
    print("\nVideos uploaded to Confluence successfully!")
