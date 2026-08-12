from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from northstar_rag import RAGService, Settings


if __name__ == "__main__":
    service = RAGService(Settings.from_env())
    manifest = service.build_index()
    print(f"Built {manifest.chunk_count} chunks from {manifest.source_count} files.")
    if manifest.errors:
        print("Skipped files:")
        for error in manifest.errors:
            print(f"- {error}")

