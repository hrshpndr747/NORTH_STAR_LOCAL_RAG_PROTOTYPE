from __future__ import annotations

import argparse
import mimetypes
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


class ConfluenceUploader:
    def __init__(self, base_url: str, email: str, api_token: str, timeout: int = 60) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.auth = (email, api_token)

    def get_page(self, page_id: str) -> dict:
        url = f"{self.base_url}/wiki/api/v2/pages/{page_id}"
        resp = self.session.get(url, headers={"Accept": "application/json"}, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def get_existing_attachments(self, page_id: str) -> dict[str, str]:
        """Returns {filename: attachment_id} for all attachments on page."""
        existing = {}
        url = f"{self.base_url}/wiki/api/v2/pages/{page_id}/attachments"
        params = {"limit": 100}
        while url:
            resp = self.session.get(url, headers={"Accept": "application/json"}, params=params, timeout=self.timeout)
            resp.raise_for_status()
            payload = resp.json()
            for att in payload.get("results", []):
                title = att.get("title")
                att_id = att.get("id")
                if title and att_id:
                    existing[title] = str(att_id)
            params = None
            next_link = payload.get("_links", {}).get("next")
            url = f"{self.base_url}{next_link}" if next_link else None
        return existing

    def upload_attachment(self, page_id: str, file_path: Path, comment: str = "Uploaded via script") -> dict:
        file_path = Path(file_path)
        if not file_path.is_file():
            raise FileNotFoundError(f"File not found: {file_path}")

        existing = self.get_existing_attachments(page_id)
        filename = file_path.name
        mime_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"

        headers = {"X-Atlassian-Token": "no-check"}

        if filename in existing:
            att_id = existing[filename]
            url = f"{self.base_url}/wiki/rest/api/content/{page_id}/child/attachment/{att_id}/data"
            print(f"Updating existing attachment '{filename}' (ID: {att_id})...")
        else:
            url = f"{self.base_url}/wiki/rest/api/content/{page_id}/child/attachment"
            print(f"Uploading new attachment '{filename}'...")

        with file_path.open("rb") as f:
            files = {"file": (filename, f, mime_type)}
            data = {"comment": comment}
            resp = self.session.post(url, headers=headers, files=files, data=data, timeout=self.timeout)
            resp.raise_for_status()
            return resp.json()

    def upload_directory(self, page_id: str, directory_path: Path) -> list[str]:
        directory_path = Path(directory_path)
        if not directory_path.is_dir():
            raise NotADirectoryError(f"Directory not found: {directory_path}")

        uploaded = []
        for file in sorted(directory_path.rglob("*")):
            if file.is_file() and not file.name.startswith("."):
                try:
                    self.upload_attachment(page_id, file)
                    uploaded.append(str(file))
                    print(f"  [OK] {file.name}")
                except Exception as exc:
                    print(f"  [ERROR] {file.name}: {exc}")
        return uploaded

    def create_page(self, space_id: str, title: str, html_body: str = "<p>Dataset page</p>") -> dict:
        url = f"{self.base_url}/wiki/api/v2/pages"
        payload = {
            "spaceId": space_id,
            "status": "current",
            "title": title,
            "body": {
                "representation": "storage",
                "value": html_body,
            },
        }
        resp = self.session.post(
            url,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            json=payload,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()


def main():
    load_dotenv(PROJECT_ROOT / ".env")
    parser = argparse.ArgumentParser(description="Upload files or folders to a Confluence page as attachments.")
    parser.add_argument("--page-id", help="Target Confluence Page ID")
    parser.add_argument("--path", help="Path to file or folder to upload")
    parser.add_argument("--base-url", default=os.getenv("CONFLUENCE_BASE_URL"), help="Confluence base URL")
    parser.add_argument("--email", default=os.getenv("CONFLUENCE_EMAIL"), help="Confluence user email")
    parser.add_argument("--token", default=os.getenv("CONFLUENCE_API_TOKEN"), help="Confluence API token")

    args = parser.parse_args()

    if not args.base_url or not args.email or not args.token:
        sys.exit("Error: Confluence URL, email, and API token are required. Set them in .env or pass as arguments.")

    if not args.page_id or not args.path:
        sys.exit("Usage: python scripts/upload_to_confluence.py --page-id <PAGE_ID> --path <FILE_OR_DIR_PATH>")

    uploader = ConfluenceUploader(args.base_url, args.email, args.token)
    target_path = Path(args.path)

    print(f"Target Confluence: {args.base_url}")
    print(f"Verifying Page ID {args.page_id}...")
    page_info = uploader.get_page(args.page_id)
    print(f"Found page: '{page_info.get('title')}' in space ID {page_info.get('spaceId')}")

    if target_path.is_file():
        uploader.upload_attachment(args.page_id, target_path)
        print(f"Successfully uploaded {target_path.name}")
    elif target_path.is_dir():
        results = uploader.upload_directory(args.page_id, target_path)
        print(f"Completed: {len(results)} files uploaded to page {args.page_id}.")
    else:
        sys.exit(f"Invalid path: {target_path}")


if __name__ == "__main__":
    main()
