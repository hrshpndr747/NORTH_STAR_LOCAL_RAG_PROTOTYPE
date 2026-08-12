import json
from pathlib import Path

from northstar_rag.confluence import ConfluenceCloudClient, _safe_filename
from northstar_rag.loaders import load_file


class FakeResponse:
    def __init__(self, payload=None, blocks=None, links=None):
        self._payload = payload or {}
        self._blocks = blocks or []
        self.links = links or {}

    def json(self):
        return self._payload

    def raise_for_status(self):
        return None

    def iter_content(self, chunk_size):
        yield from self._blocks


def test_attachment_listing_uses_all_pages(monkeypatch):
    client = ConfluenceCloudClient("https://example.atlassian.net", "user@example.com", "token")
    responses = iter(
        [
            FakeResponse(
                {"results": [{"id": "a1", "title": "one.pdf"}]},
                links={"next": {"url": "https://example.atlassian.net/next-page"}},
            ),
            FakeResponse({"results": [{"id": "a2", "title": "two.docx"}]}),
        ]
    )
    monkeypatch.setattr(client, "_get", lambda url, params=None: next(responses))
    assert [item["id"] for item in client.attachments_for_page("123")] == ["a1", "a2"]


def test_binary_download_uses_documented_endpoint_and_writes_sidecar(tmp_path):
    client = ConfluenceCloudClient("https://example.atlassian.net", "user@example.com", "token")
    calls = []

    class FakeSession:
        def get(self, url, **kwargs):
            calls.append((url, kwargs))
            return FakeResponse(blocks=[b"first ", b"second"])

    client.session = FakeSession()
    page = {"id": "123", "title": "Policy", "version": {"number": 4}, "_links": {"webui": "/wiki/x/PAGE"}}
    attachment = {
        "id": "456",
        "title": "../Policy Guide.txt",
        "fileSize": 12,
        "mediaType": "text/plain",
        "version": {"number": 2},
        "webuiLink": "/wiki/x/ATTACHMENT",
    }
    target, downloaded = client.download_attachment(page, attachment, tmp_path, max_bytes=1024)

    assert downloaded
    assert target.name == "Policy Guide.txt"
    assert target.read_bytes() == b"first second"
    assert calls[0][0].endswith("/wiki/rest/api/content/123/child/attachment/456/download")
    metadata = json.loads(target.with_name(f".{target.name}.confluence.json").read_text(encoding="utf-8"))
    assert metadata["attachment_version"] == 2
    assert metadata["url"] == "https://example.atlassian.net/wiki/x/ATTACHMENT"

    same_target, downloaded_again = client.download_attachment(page, attachment, tmp_path, max_bytes=1024)
    assert same_target == target
    assert not downloaded_again
    assert len(calls) == 1


def test_downloaded_attachment_metadata_is_added_to_citations(tmp_path):
    target = tmp_path / "policy.txt"
    target.write_text("The limit is 42.", encoding="utf-8")
    target.with_name(".policy.txt.confluence.json").write_text(
        json.dumps(
            {
                "confluence_attachment": True,
                "attachment_id": "456",
                "attachment_version": 3,
                "page_id": "123",
                "url": "https://example.atlassian.net/wiki/x/ATTACHMENT",
            }
        ),
        encoding="utf-8",
    )
    documents = load_file(target, tmp_path)
    assert documents[0].source_url.endswith("/wiki/x/ATTACHMENT")
    assert "Confluence attachment 456; version 3; parent page 123" in documents[0].locator


def test_space_sync_filters_unsupported_and_oversized_attachments(monkeypatch, tmp_path):
    client = ConfluenceCloudClient("https://example.atlassian.net", "user@example.com", "token")
    page = {
        "id": "123",
        "title": "Dataset Attachments",
        "body": {"storage": {"value": "<p>Approved files</p>"}},
        "version": {"number": 1},
        "_links": {"webui": "/wiki/x/PAGE"},
    }
    attachments = [
        {"id": "1", "title": "guide.pdf", "fileSize": 100, "version": {"number": 1}},
        {"id": "2", "title": "video.mp4", "fileSize": 100, "version": {"number": 1}},
        {"id": "3", "title": "huge.docx", "fileSize": 2_000, "version": {"number": 1}},
    ]
    monkeypatch.setattr(client, "get_space_id", lambda key: "space-1")
    monkeypatch.setattr(client, "pages", lambda space_id: iter([page]))
    monkeypatch.setattr(client, "attachments_for_page", lambda page_id: iter(attachments))

    def fake_download(page_value, attachment, output_dir, max_bytes):
        return output_dir / "attachments" / page_value["id"] / attachment["title"], True

    monkeypatch.setattr(client, "download_attachment", fake_download)
    result = client.sync_space(
        "DEMO",
        tmp_path,
        allowed_extensions={".pdf", ".docx"},
        max_attachment_bytes=1_000,
    )
    assert len(result.pages) == 1
    assert len(result.attachments) == 1
    assert len(result.skipped_attachments) == 2
    assert any("unsupported file type .mp4" in item for item in result.skipped_attachments)
    assert any("exceeds the 1000 byte limit" in item for item in result.skipped_attachments)


def test_safe_filename_blocks_parent_directories():
    assert _safe_filename("../../secret.pdf", "fallback") == "secret.pdf"
    assert _safe_filename("..\\..\\secret.pdf", "fallback") == "secret.pdf"
