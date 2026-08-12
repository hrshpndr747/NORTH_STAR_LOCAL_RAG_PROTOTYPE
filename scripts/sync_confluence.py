from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from northstar_rag.confluence import ConfluenceCloudClient, DEFAULT_ATTACHMENT_EXTENSIONS


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


if __name__ == "__main__":
    load_dotenv(PROJECT_ROOT / ".env")
    required = ["CONFLUENCE_BASE_URL", "CONFLUENCE_EMAIL", "CONFLUENCE_API_TOKEN", "CONFLUENCE_SPACE_KEY"]
    missing = [name for name in required if not os.getenv(name) or os.getenv(name, "").startswith("https://your-")]
    if missing:
        raise SystemExit("Set these values in .env first: " + ", ".join(missing))
    output = Path(os.getenv("CONFLUENCE_OUTPUT_DIR", "data/confluence"))
    if not output.is_absolute():
        output = PROJECT_ROOT / output
    client = ConfluenceCloudClient(
        os.environ["CONFLUENCE_BASE_URL"],
        os.environ["CONFLUENCE_EMAIL"],
        os.environ["CONFLUENCE_API_TOKEN"],
    )
    extensions_value = os.getenv("CONFLUENCE_ATTACHMENT_EXTENSIONS", "")
    extensions = (
        {item.strip().lower() for item in extensions_value.split(",") if item.strip()}
        if extensions_value
        else DEFAULT_ATTACHMENT_EXTENSIONS
    )
    max_megabytes = max(1, int(os.getenv("CONFLUENCE_ATTACHMENT_MAX_MB", "250")))
    result = client.sync_space(
        os.environ["CONFLUENCE_SPACE_KEY"],
        output,
        download_attachments=env_bool("CONFLUENCE_DOWNLOAD_ATTACHMENTS", True),
        allowed_extensions=extensions,
        max_attachment_bytes=max_megabytes * 1024 * 1024,
    )
    print(f"Downloaded {len(result.pages)} Confluence pages to {output}.")
    print(f"Downloaded {len(result.attachments)} new or updated supported attachments.")
    print(f"Kept {len(result.unchanged_attachments)} unchanged supported attachments.")
    if result.skipped_attachments:
        print(f"Skipped {len(result.skipped_attachments)} attachments because of type or size limits:")
        for item in result.skipped_attachments:
            print(f"- {item}")
    if result.errors:
        print(f"Completed with {len(result.errors)} attachment errors:")
        for item in result.errors:
            print(f"- {item}")
    print("Rebuild the RAG index to include them.")
