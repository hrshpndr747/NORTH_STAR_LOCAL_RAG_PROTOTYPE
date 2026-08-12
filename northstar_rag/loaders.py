from __future__ import annotations

import csv
import json
import re
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Iterable

from docx import Document
from openpyxl import load_workbook
from pypdf import PdfReader

from .media import AUDIO_SUFFIXES, IMAGE_SUFFIXES, VIDEO_SUFFIXES, media_sidecar
from .models import SourceDocument


SUPPORTED_SUFFIXES = {
    ".docx", ".pdf", ".xlsx", ".vtt", ".txt", ".md", ".csv", ".json",
    ".db", ".sqlite", ".sqlite3",
} | IMAGE_SUFFIXES | VIDEO_SUFFIXES | AUDIO_SUFFIXES


def _display_path(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.name


def load_docx(path: Path, root: Path) -> list[SourceDocument]:
    document = Document(path)
    blocks: list[str] = []
    for paragraph in document.paragraphs:
        value = paragraph.text.strip()
        if value:
            blocks.append(value)
    for table_number, table in enumerate(document.tables, 1):
        rows = []
        for row in table.rows:
            cells = [re.sub(r"\s+", " ", cell.text).strip() for cell in row.cells]
            if any(cells):
                rows.append(" | ".join(cells))
        if rows:
            blocks.append(f"Table {table_number}\n" + "\n".join(rows))
    return [
        SourceDocument(
            text="\n\n".join(blocks),
            title=path.stem.replace("_", " "),
            source_path=_display_path(path, root),
            source_type="word",
            locator="document",
        )
    ]


def load_pdf(path: Path, root: Path) -> list[SourceDocument]:
    reader = PdfReader(path)
    output: list[SourceDocument] = []
    for page_number, page in enumerate(reader.pages, 1):
        text = (page.extract_text() or "").strip()
        if text:
            output.append(
                SourceDocument(
                    text=text,
                    title=path.stem.replace("_", " "),
                    source_path=_display_path(path, root),
                    source_type="pdf",
                    locator=f"page {page_number}",
                )
            )
    return output


_TIME_RANGE = re.compile(r"(?P<start>\d{2}:\d{2}:\d{2}[.,]\d{3})\s+-->\s+(?P<end>\d{2}:\d{2}:\d{2}[.,]\d{3})")


def load_vtt(path: Path, root: Path) -> list[SourceDocument]:
    lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    cues: list[tuple[str, str, str]] = []
    index = 0
    while index < len(lines):
        match = _TIME_RANGE.search(lines[index])
        if not match:
            index += 1
            continue
        text_lines: list[str] = []
        index += 1
        while index < len(lines) and lines[index].strip():
            text_lines.append(re.sub(r"<[^>]+>", "", lines[index]).strip())
            index += 1
        text = " ".join(value for value in text_lines if value)
        if text:
            cues.append((match.group("start").replace(",", "."), match.group("end").replace(",", "."), text))

    documents: list[SourceDocument] = []
    for start in range(0, len(cues), 8):
        group = cues[start : start + 8]
        documents.append(
            SourceDocument(
                text=" ".join(item[2] for item in group),
                title=path.stem.replace("_", " ") + " transcript",
                source_path=_display_path(path, root),
                source_type="video_transcript",
                locator=f"{group[0][0]}–{group[-1][1]}",
            )
        )
    return documents


def _clean_cell(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def load_xlsx(path: Path, root: Path) -> list[SourceDocument]:
    workbook = load_workbook(path, data_only=True, read_only=True)
    documents: list[SourceDocument] = []
    source_path = _display_path(path, root)
    for worksheet in workbook.worksheets:
        values = list(worksheet.iter_rows(values_only=True))
        if not values:
            continue
        headers = [_clean_cell(value) or f"column_{index + 1}" for index, value in enumerate(values[0])]
        rows: list[dict[str, str]] = []
        for value_row in values[1:]:
            row = {headers[index]: _clean_cell(value) for index, value in enumerate(value_row) if index < len(headers)}
            if any(row.values()):
                rows.append(row)

        if rows:
            summary_lines = [f"Workbook: {path.name}", f"Sheet: {worksheet.title}", f"Total data rows: {len(rows)}"]
            normalized_headers = {header.lower().replace(" ", "_"): header for header in headers}
            for key in ("priority", "team", "category", "status", "within_sla"):
                original = normalized_headers.get(key)
                if original:
                    counts = Counter(row.get(original, "") for row in rows if row.get(original, ""))
                    summary_lines.append(f"Counts by {original}: " + ", ".join(f"{name}={count}" for name, count in sorted(counts.items())))
            documents.append(
                SourceDocument(
                    text="\n".join(summary_lines),
                    title=f"{path.stem.replace('_', ' ')} — {worksheet.title} summary",
                    source_path=source_path,
                    source_type="spreadsheet",
                    locator=f"sheet {worksheet.title}; computed summary",
                )
            )
            for row_start in range(0, len(rows), 12):
                group = rows[row_start : row_start + 12]
                row_lines = [
                    "; ".join(f"{header}={row.get(header, '')}" for header in headers if row.get(header, ""))
                    for row in group
                ]
                documents.append(
                    SourceDocument(
                        text="\n".join(row_lines),
                        title=f"{path.stem.replace('_', ' ')} — {worksheet.title}",
                        source_path=source_path,
                        source_type="spreadsheet",
                        locator=f"sheet {worksheet.title}; rows {row_start + 2}–{row_start + len(group) + 1}",
                    )
                )
    workbook.close()
    return documents


def _quote_identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def load_sqlite(path: Path, root: Path) -> list[SourceDocument]:
    uri = f"file:{path.resolve().as_posix()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    source_path = _display_path(path, root)
    documents: list[SourceDocument] = []
    try:
        objects = connection.execute(
            "SELECT name, type, sql FROM sqlite_master WHERE type IN ('table','view') AND name NOT LIKE 'sqlite_%' ORDER BY type, name"
        ).fetchall()
        schema_text = "\n\n".join(f"{row['type']} {row['name']}: {row['sql']}" for row in objects)
        documents.append(
            SourceDocument(
                text=schema_text,
                title=f"{path.stem.replace('_', ' ')} database schema",
                source_path=source_path,
                source_type="database",
                locator="schema",
            )
        )
        for item in objects:
            name = item["name"]
            quoted = _quote_identifier(name)
            total = connection.execute(f"SELECT COUNT(*) FROM {quoted}").fetchone()[0]
            columns = [row[1] for row in connection.execute(f"PRAGMA table_info({quoted})").fetchall()]
            summary_lines = [f"Database object: {name}", f"Total rows: {total}", f"Columns: {', '.join(columns)}"]
            for column in columns:
                if column.lower() in {"department", "priority", "status", "request_type", "team", "category"}:
                    column_q = _quote_identifier(column)
                    counts = connection.execute(
                        f"SELECT {column_q}, COUNT(*) FROM {quoted} GROUP BY {column_q} ORDER BY COUNT(*) DESC, {column_q}"
                    ).fetchall()
                    summary_lines.append(f"Counts by {column}: " + ", ".join(f"{row[0]}={row[1]}" for row in counts))
            documents.append(
                SourceDocument(
                    text="\n".join(summary_lines),
                    title=f"{path.stem.replace('_', ' ')} — {name} summary",
                    source_path=source_path,
                    source_type="database",
                    locator=f"{name}; computed summary",
                    metadata={"database_path": str(path.resolve()), "object": name},
                )
            )
    finally:
        connection.close()
    return documents


def load_confluence_json(path: Path, root: Path) -> list[SourceDocument]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict) or "text" not in payload or "confluence_page_id" not in payload:
        return load_text(path, root)
    return [
        SourceDocument(
            text=payload["text"],
            title=payload.get("title", path.stem),
            source_path=_display_path(path, root),
            source_type="confluence",
            locator=f"page {payload['confluence_page_id']}; version {payload.get('version', '?')}",
            source_url=payload.get("url", ""),
            metadata={"page_id": payload["confluence_page_id"], "version": payload.get("version")},
        )
    ]


def load_csv(path: Path, root: Path) -> list[SourceDocument]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    output: list[SourceDocument] = []
    for row_start in range(0, len(rows), 15):
        group = rows[row_start : row_start + 15]
        text = "\n".join("; ".join(f"{key}={value}" for key, value in row.items()) for row in group)
        output.append(
            SourceDocument(
                text=text,
                title=path.stem.replace("_", " "),
                source_path=_display_path(path, root),
                source_type="csv",
                locator=f"rows {row_start + 2}–{row_start + len(group) + 1}",
            )
        )
    return output


def load_text(path: Path, root: Path) -> list[SourceDocument]:
    return [
        SourceDocument(
            text=path.read_text(encoding="utf-8-sig", errors="replace"),
            title=path.stem.replace("_", " "),
            source_path=_display_path(path, root),
            source_type=path.suffix.lower().lstrip(".") or "text",
            locator="document",
        )
    ]


def load_media_analysis(path: Path, root: Path) -> list[SourceDocument]:
    sidecar = media_sidecar(path)
    if not sidecar.exists():
        return []
    payload = json.loads(sidecar.read_text(encoding="utf-8"))
    if not payload.get("media_analysis"):
        return []
    output: list[SourceDocument] = []
    for item in payload.get("items", []):
        text = str(item.get("text", "")).strip()
        if not text:
            continue
        output.append(
            SourceDocument(
                text=text,
                title=path.stem.replace("_", " "),
                source_path=_display_path(path, root),
                source_type=item.get("source_type", "media_analysis"),
                locator=item.get("locator", "automatic media analysis"),
                metadata={
                    "vision_model": payload.get("vision_model"),
                    "whisper_model": payload.get("whisper_model"),
                },
            )
        )
    return output


def _apply_confluence_attachment_metadata(path: Path, documents: list[SourceDocument]) -> list[SourceDocument]:
    sidecar = path.with_name(f".{path.name}.confluence.json")
    if not sidecar.exists():
        return documents
    try:
        metadata = json.loads(sidecar.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return documents
    if not metadata.get("confluence_attachment"):
        return documents
    attachment_id = metadata.get("attachment_id", "?")
    attachment_version = metadata.get("attachment_version", "?")
    page_id = metadata.get("page_id", "?")
    for document in documents:
        attachment_locator = f"Confluence attachment {attachment_id}; version {attachment_version}; parent page {page_id}"
        document.locator = f"{document.locator}; {attachment_locator}" if document.locator else attachment_locator
        document.source_url = metadata.get("url", "")
        document.metadata = {**document.metadata, **metadata}
    return documents


def load_file(path: Path, root: Path) -> list[SourceDocument]:
    suffix = path.suffix.lower()
    if suffix == ".docx":
        documents = load_docx(path, root)
    elif suffix == ".pdf":
        documents = load_pdf(path, root) + load_media_analysis(path, root)
    elif suffix == ".xlsx":
        documents = load_xlsx(path, root)
    elif suffix == ".vtt":
        documents = load_vtt(path, root)
    elif suffix in {".db", ".sqlite", ".sqlite3"}:
        documents = load_sqlite(path, root)
    elif suffix == ".csv":
        documents = load_csv(path, root)
    elif suffix == ".json":
        documents = load_confluence_json(path, root)
    elif suffix in IMAGE_SUFFIXES | VIDEO_SUFFIXES | AUDIO_SUFFIXES:
        documents = load_media_analysis(path, root)
    else:
        documents = load_text(path, root)
    return _apply_confluence_attachment_metadata(path, documents)


def discover_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES and not any(part.startswith(".") for part in path.parts):
            yield path


def load_tree(root: Path) -> tuple[list[SourceDocument], list[str]]:
    documents: list[SourceDocument] = []
    errors: list[str] = []
    for path in discover_files(root):
        try:
            documents.extend(load_file(path, root))
        except Exception as exc:  # continue indexing other sources and report the exact file
            errors.append(f"{_display_path(path, root)}: {exc}")
    return documents, errors
