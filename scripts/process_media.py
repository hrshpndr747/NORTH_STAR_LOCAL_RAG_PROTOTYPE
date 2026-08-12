from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from northstar_rag import RAGService, Settings
from northstar_rag.media import MediaProcessor, MediaSettings


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create local OCR, transcript, and sampled-frame evidence sidecars.")
    parser.add_argument("--force", action="store_true", help="Reprocess media even when the cached analysis is current")
    args = parser.parse_args()
    settings = Settings.from_env()
    service = RAGService(settings)
    processor = MediaProcessor(service.client, MediaSettings.from_env(settings.chat_model))
    total_processed = total_unchanged = 0
    errors: list[str] = []
    for root in service.source_roots():
        result = processor.process_tree(root, force=args.force)
        total_processed += len(result.processed)
        total_unchanged += len(result.unchanged)
        errors.extend(result.errors)
    print(f"Processed {total_processed} media files; kept {total_unchanged} cached analyses.")
    for error in errors:
        print(f"ERROR: {error}")
    if errors:
        raise SystemExit(1)
