from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


class ConfluenceError(RuntimeError):
    pass


DEFAULT_ATTACHMENT_EXTENSIONS = {
    ".aac",
    ".avi",
    ".bmp",
    ".csv",
    ".db",
    ".docx",
    ".flac",
    ".jpeg",
    ".jpg",
    ".json",
    ".m4a",
    ".md",
    ".mkv",
    ".mov",
    ".mp3",
    ".mp4",
    ".ogg",
    ".pdf",
    ".png",
    ".sqlite",
    ".sqlite3",
    ".tif",
    ".tiff",
    ".txt",
    ".vtt",
    ".wav",
    ".webm",
    ".webp",
    ".xlsx",
}


@dataclass
class SyncResult:
    pages: list[Path] = field(default_factory=list)
    attachments: list[Path] = field(default_factory=list)
    unchanged_attachments: list[Path] = field(default_factory=list)
    skipped_attachments: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _safe_filename(value: str, fallback: str) -> str:
    # Path.name removes attempted parent directories before character cleanup.
    original = Path(value.replace("\\", "/")).name.strip()
    cleaned = re.sub(r"[^A-Za-z0-9 ._()-]+", "_", original).strip(" .")
    return (cleaned or fallback)[:180]


class ConfluenceCloudClient:
    def __init__(self, base_url: str, email: str, api_token: str, timeout: int = 60) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.auth = (email, api_token)
        self.session.headers.update({"Accept": "application/json"})

    def _get(self, url: str, params: dict | None = None) -> requests.Response:
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            raise ConfluenceError(f"Confluence request failed: {exc}") from exc

    def _next_url(self, response: requests.Response, payload: dict) -> str:
        link_next = response.links.get("next", {}).get("url")
        if link_next:
            return link_next
        next_value = payload.get("_links", {}).get("next", "")
        return urljoin(self.base_url, next_value) if next_value else ""

    def get_space_id(self, space_key: str) -> str:
        response = self._get(f"{self.base_url}/wiki/api/v2/spaces", params={"keys": space_key, "limit": 100})
        results = response.json().get("results", [])
        for space in results:
            if space.get("key", "").lower() == space_key.lower():
                return str(space["id"])
        raise ConfluenceError(f"No Confluence space was found for key {space_key!r}.")

    def pages(self, space_id: str):
        url = f"{self.base_url}/wiki/api/v2/pages"
        params = {"space-id": space_id, "body-format": "storage", "limit": 100, "status": "current"}
        while url:
            response = self._get(url, params=params)
            params = None
            payload = response.json()
            for page in payload.get("results", []):
                yield page
            url = self._next_url(response, payload)

    def page_with_body(self, page_id: str) -> dict:
        response = self._get(
            f"{self.base_url}/wiki/api/v2/pages/{page_id}",
            params={"body-format": "storage"},
        )
        return response.json()

    def attachments_for_page(self, page_id: str):
        url = f"{self.base_url}/wiki/api/v2/pages/{page_id}/attachments"
        params = {"limit": 100, "status": "current"}
        while url:
            response = self._get(url, params=params)
            params = None
            payload = response.json()
            for attachment in payload.get("results", []):
                yield attachment
            url = self._next_url(response, payload)

    def _attachment_sidecar(self, target: Path) -> Path:
        return target.with_name(f".{target.name}.confluence.json")

    def _attachment_is_current(self, target: Path, metadata: dict) -> bool:
        sidecar = self._attachment_sidecar(target)
        if not target.exists() or not sidecar.exists():
            return False
        try:
            previous = json.loads(sidecar.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False
        expected_size = metadata.get("file_size")
        size_matches = expected_size in (None, 0) or target.stat().st_size == expected_size
        return (
            str(previous.get("attachment_id")) == str(metadata.get("attachment_id"))
            and previous.get("attachment_version") == metadata.get("attachment_version")
            and size_matches
        )

    def download_attachment(
        self,
        page: dict,
        attachment: dict,
        output_dir: Path,
        max_bytes: int,
    ) -> tuple[Path, bool]:
        page_id = str(page["id"])
        attachment_id = str(attachment["id"])
        version = attachment.get("version", {}).get("number")
        filename = _safe_filename(attachment.get("title", ""), f"attachment_{attachment_id}")
        target_dir = output_dir / "attachments" / page_id
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / filename
        webui = attachment.get("webuiLink") or attachment.get("_links", {}).get("webui", "")
        page_webui = page.get("_links", {}).get("webui", "")
        source_url = (
            urljoin(self.base_url, webui)
            if webui
            else urljoin(self.base_url, page_webui)
            if page_webui
            else f"{self.base_url}/wiki/pages/viewpage.action?pageId={page_id}"
        )
        metadata = {
            "confluence_attachment": True,
            "attachment_id": attachment_id,
            "attachment_version": version,
            "file_size": attachment.get("fileSize"),
            "media_type": attachment.get("mediaType", ""),
            "title": attachment.get("title", filename),
            "page_id": page_id,
            "page_title": page.get("title", ""),
            "page_version": page.get("version", {}).get("number"),
            "space_id": page.get("spaceId"),
            "url": source_url,
        }
        if self._attachment_is_current(target, metadata):
            return target, False

        endpoint = f"{self.base_url}/wiki/rest/api/content/{page_id}/child/attachment/{attachment_id}/download"
        params = {"version": version} if version is not None else None
        temporary = target.with_name(f".{target.name}.part")
        bytes_written = 0
        try:
            response = self.session.get(
                endpoint,
                params=params,
                headers={"Accept": "*/*"},
                timeout=self.timeout,
                stream=True,
                allow_redirects=True,
            )
            response.raise_for_status()
            with temporary.open("wb") as handle:
                for block in response.iter_content(chunk_size=1024 * 1024):
                    if not block:
                        continue
                    bytes_written += len(block)
                    if bytes_written > max_bytes:
                        raise ConfluenceError(f"attachment exceeded the {max_bytes} byte download limit")
                    handle.write(block)
            if not bytes_written:
                raise ConfluenceError("attachment download returned an empty file")
            temporary.replace(target)
            self._attachment_sidecar(target).write_text(
                json.dumps(metadata, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            return target, True
        except (OSError, requests.RequestException) as exc:
            raise ConfluenceError(f"attachment download failed: {exc}") from exc
        finally:
            if temporary.exists():
                temporary.unlink()

    def sync_space(
        self,
        space_key: str,
        output_dir: Path,
        *,
        download_attachments: bool = True,
        allowed_extensions: set[str] | None = None,
        max_attachment_bytes: int = 50 * 1024 * 1024,
    ) -> SyncResult:
        space_id = self.get_space_id(space_key)
        output_dir.mkdir(parents=True, exist_ok=True)
        result = SyncResult()
        extensions = {value.lower() if value.startswith(".") else f".{value.lower()}" for value in (allowed_extensions or DEFAULT_ATTACHMENT_EXTENSIONS)}
        for page in self.pages(space_id):
            storage = page.get("body", {}).get("storage", {}).get("value", "")
            if not storage:
                page = self.page_with_body(str(page["id"]))
                storage = page.get("body", {}).get("storage", {}).get("value", "")
            soup = BeautifulSoup(storage, "html.parser")
            text = "\n".join(line.strip() for line in soup.get_text("\n").splitlines() if line.strip())
            page_id = str(page["id"])
            safe_title = re.sub(r"[^A-Za-z0-9._-]+", "_", page.get("title", "page")).strip("_")[:100]
            webui = page.get("_links", {}).get("webui", "")
            record = {
                "confluence_page_id": page_id,
                "space_key": space_key,
                "title": page.get("title", safe_title),
                "version": page.get("version", {}).get("number"),
                "url": urljoin(self.base_url, webui) if webui else f"{self.base_url}/wiki/spaces/{space_key}/pages/{page_id}",
                "text": text,
            }
            target = output_dir / f"{page_id}_{safe_title or 'page'}.json"
            target.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
            result.pages.append(target)

            if not download_attachments:
                continue
            try:
                attachments = list(self.attachments_for_page(page_id))
            except ConfluenceError as exc:
                result.errors.append(f"Page {page_id} ({page.get('title', '')}): could not list attachments: {exc}")
                continue
            for attachment in attachments:
                title = attachment.get("title", f"attachment_{attachment.get('id', 'unknown')}")
                suffix = Path(title).suffix.lower()
                size = attachment.get("fileSize")
                if suffix not in extensions:
                    result.skipped_attachments.append(f"{title}: unsupported file type {suffix or '(none)'}")
                    continue
                if isinstance(size, int) and size > max_attachment_bytes:
                    result.skipped_attachments.append(
                        f"{title}: {size} bytes exceeds the {max_attachment_bytes} byte limit"
                    )
                    continue
                try:
                    path, downloaded = self.download_attachment(page, attachment, output_dir, max_attachment_bytes)
                    if downloaded:
                        result.attachments.append(path)
                    else:
                        result.unchanged_attachments.append(path)
                except ConfluenceError as exc:
                    result.errors.append(f"{title} on page {page_id}: {exc}")

        manifest = {
            "space_key": space_key,
            "pages": [str(path.relative_to(output_dir)) for path in result.pages],
            "attachments": [str(path.relative_to(output_dir)) for path in result.attachments + result.unchanged_attachments],
            "skipped_attachments": result.skipped_attachments,
            "errors": result.errors,
        }
        (output_dir / ".confluence-sync-manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return result
