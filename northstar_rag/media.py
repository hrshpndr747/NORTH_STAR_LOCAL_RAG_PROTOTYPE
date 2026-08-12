from __future__ import annotations

import io
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from pypdf import PdfReader

from .ollama_client import OllamaClient


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}
VIDEO_SUFFIXES = {".mp4", ".mov", ".mkv", ".webm", ".avi"}
AUDIO_SUFFIXES = {".mp3", ".wav", ".m4a", ".flac", ".aac", ".ogg"}
MEDIA_SUFFIXES = IMAGE_SUFFIXES | VIDEO_SUFFIXES | AUDIO_SUFFIXES | {".pdf"}


IMAGE_PROMPT = """Analyze this image as evidence for a RAG knowledge system.
1. Transcribe all readable text exactly, preserving important numbers, units, labels, and table values.
2. Briefly describe meaningful visual information such as a diagram, chart, process, object, or action.
3. Do not guess unreadable text or infer facts not visibly supported.
If the image contains no readable text and no useful informational content, respond exactly: NO_USEFUL_CONTENT
Return concise plain text, not commentary about your task."""


@dataclass(frozen=True)
class MediaSettings:
    vision_model: str = "qwen3.5:4b"
    whisper_model: str = "small"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    whisper_language: str | None = None
    pdf_ocr_min_chars: int = 50
    pdf_ocr_max_pages: int = 100
    video_frame_interval_seconds: float = 15.0
    video_max_frames: int = 40
    enable_frame_analysis: bool = True

    @classmethod
    def from_env(cls, default_vision_model: str = "qwen3.5:4b") -> "MediaSettings":
        language = os.getenv("WHISPER_LANGUAGE", "auto").strip()
        return cls(
            vision_model=os.getenv("OCR_VISION_MODEL", default_vision_model),
            whisper_model=os.getenv("WHISPER_MODEL", "small"),
            whisper_device=os.getenv("WHISPER_DEVICE", "cpu"),
            whisper_compute_type=os.getenv("WHISPER_COMPUTE_TYPE", "int8"),
            whisper_language=None if language.lower() in {"", "auto"} else language,
            pdf_ocr_min_chars=max(0, int(os.getenv("PDF_OCR_MIN_CHARS", "50"))),
            pdf_ocr_max_pages=max(1, int(os.getenv("PDF_OCR_MAX_PAGES", "100"))),
            video_frame_interval_seconds=max(1.0, float(os.getenv("VIDEO_FRAME_INTERVAL_SECONDS", "15"))),
            video_max_frames=max(0, int(os.getenv("VIDEO_MAX_FRAMES", "40"))),
            enable_frame_analysis=os.getenv("VIDEO_FRAME_ANALYSIS", "true").strip().lower() in {"1", "true", "yes", "on"},
        )


@dataclass
class MediaProcessResult:
    processed: list[Path] = field(default_factory=list)
    unchanged: list[Path] = field(default_factory=list)
    skipped: list[Path] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def media_sidecar(path: Path) -> Path:
    return path.with_name(f".{path.name}.media.json")


def _timestamp(seconds: float) -> str:
    value = max(0, int(seconds))
    hours, remainder = divmod(value, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def group_transcript_segments(segments: Iterable[tuple[float, float, str]], max_words: int = 220) -> list[dict]:
    groups: list[dict] = []
    current: list[tuple[float, float, str]] = []
    words = 0
    for start, end, text in segments:
        clean = text.strip()
        if not clean:
            continue
        count = len(clean.split())
        if current and words + count > max_words:
            groups.append(
                {
                    "text": " ".join(item[2] for item in current),
                    "locator": f"{_timestamp(current[0][0])}–{_timestamp(current[-1][1])}; automatic speech transcript",
                    "source_type": "video_transcript",
                }
            )
            current = []
            words = 0
        current.append((start, end, clean))
        words += count
    if current:
        groups.append(
            {
                "text": " ".join(item[2] for item in current),
                "locator": f"{_timestamp(current[0][0])}–{_timestamp(current[-1][1])}; automatic speech transcript",
                "source_type": "video_transcript",
            }
        )
    return groups


class MediaProcessor:
    def __init__(self, client: OllamaClient, settings: MediaSettings) -> None:
        self.client = client
        self.settings = settings
        self._whisper = None

    def _image_bytes(self, image) -> bytes:
        try:
            from PIL import Image, ImageOps
        except ImportError as exc:
            raise RuntimeError("Pillow is required. Run setup_windows.bat again to install media support.") from exc
        image = ImageOps.exif_transpose(image)
        image.thumbnail((2200, 2200))
        if image.mode not in {"RGB", "L"}:
            background = Image.new("RGB", image.size, "white")
            if "A" in image.getbands():
                background.paste(image, mask=image.getchannel("A"))
            else:
                background.paste(image)
            image = background
        buffer = io.BytesIO()
        image.convert("RGB").save(buffer, format="JPEG", quality=92, optimize=True)
        return buffer.getvalue()

    def _analyze_image(self, image) -> str:
        return self.client.vision(self.settings.vision_model, IMAGE_PROMPT, self._image_bytes(image)).strip()

    def _process_image(self, path: Path) -> list[dict]:
        try:
            from PIL import Image
        except ImportError as exc:
            raise RuntimeError("Pillow is required. Run setup_windows.bat again to install media support.") from exc
        with Image.open(path) as image:
            text = self._analyze_image(image)
        if not text or text == "NO_USEFUL_CONTENT":
            return []
        return [{"text": text, "locator": "image OCR and visual analysis", "source_type": "image_vision"}]

    def _process_pdf(self, path: Path) -> list[dict]:
        reader = PdfReader(path)
        pages = []
        for page_number, page in enumerate(reader.pages, 1):
            extracted = (page.extract_text() or "").strip()
            if len(extracted) < self.settings.pdf_ocr_min_chars:
                pages.append(page_number)
        if not pages:
            return []
        pages = pages[: self.settings.pdf_ocr_max_pages]
        try:
            import pypdfium2 as pdfium
        except ImportError as exc:
            raise RuntimeError("pypdfium2 is required for scanned-PDF OCR. Run setup_windows.bat again.") from exc
        pdf = pdfium.PdfDocument(str(path))
        items: list[dict] = []
        try:
            for page_number in pages:
                page = pdf[page_number - 1]
                bitmap = page.render(scale=2.2)
                image = bitmap.to_pil()
                text = self._analyze_image(image)
                if text and text != "NO_USEFUL_CONTENT":
                    items.append(
                        {
                            "text": text,
                            "locator": f"page {page_number}; scanned-page OCR and visual analysis",
                            "source_type": "pdf_ocr",
                        }
                    )
                image.close()
                bitmap.close()
                page.close()
        finally:
            pdf.close()
        return items

    def _whisper_model(self):
        if self._whisper is None:
            try:
                from faster_whisper import WhisperModel
            except ImportError as exc:
                raise RuntimeError("faster-whisper is required for audio/video transcription. Run setup_windows.bat again.") from exc
            self._whisper = WhisperModel(
                self.settings.whisper_model,
                device=self.settings.whisper_device,
                compute_type=self.settings.whisper_compute_type,
            )
        return self._whisper

    def _transcribe(self, path: Path) -> list[dict]:
        model = self._whisper_model()
        try:
            from faster_whisper.audio import decode_audio
            audio = decode_audio(str(path), sampling_rate=16000)
        except Exception:
            audio = None

        if audio is not None and len(audio) > 0:
            chunk_size = 16000 * 180  # 3-minute chunks to avoid NumPy memory allocation spikes
            all_values: list[tuple[float, float, str]] = []
            for offset in range(0, len(audio), chunk_size):
                chunk = audio[offset : offset + chunk_size]
                offset_seconds = offset / 16000.0
                segments, _ = model.transcribe(
                    chunk,
                    language=self.settings.whisper_language,
                    beam_size=5,
                    vad_filter=True,
                    condition_on_previous_text=False,
                )
                for item in segments:
                    all_values.append((offset_seconds + float(item.start), offset_seconds + float(item.end), item.text))
            return group_transcript_segments(all_values)

        segments, _ = model.transcribe(
            str(path),
            language=self.settings.whisper_language,
            beam_size=5,
            vad_filter=True,
            condition_on_previous_text=False,
        )
        values = [(float(item.start), float(item.end), item.text) for item in segments]
        return group_transcript_segments(values)

    def _video_frames(self, path: Path) -> list[dict]:
        if not self.settings.enable_frame_analysis or self.settings.video_max_frames == 0:
            return []
        try:
            import av
        except ImportError as exc:
            raise RuntimeError("PyAV is required for video-frame analysis. Run setup_windows.bat again.") from exc
        container = av.open(str(path))
        items: list[dict] = []
        next_time = 0.0
        previous_text = ""
        try:
            if not container.streams.video:
                return []
            stream = container.streams.video[0]
            for frame in container.decode(stream):
                seconds = float(frame.time) if frame.time is not None else float(frame.pts * stream.time_base) if frame.pts is not None else 0.0
                if seconds + 0.001 < next_time:
                    continue
                text = self._analyze_image(frame.to_image())
                next_time = seconds + self.settings.video_frame_interval_seconds
                if not text or text == "NO_USEFUL_CONTENT" or text == previous_text:
                    continue
                previous_text = text
                items.append(
                    {
                        "text": text,
                        "locator": f"{_timestamp(seconds)}; sampled video frame OCR and visual analysis",
                        "source_type": "video_frame_vision",
                    }
                )
                if len(items) >= self.settings.video_max_frames:
                    break
        finally:
            container.close()
        return items

    def _is_current(self, path: Path) -> bool:
        sidecar = media_sidecar(path)
        if not sidecar.exists():
            return False
        try:
            payload = json.loads(sidecar.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False
        stat = path.stat()
        return payload.get("source_size") == stat.st_size and payload.get("source_mtime_ns") == stat.st_mtime_ns

    def process_file(self, path: Path, force: bool = False) -> bool:
        suffix = path.suffix.lower()
        if suffix not in MEDIA_SUFFIXES:
            return False
        if not force and self._is_current(path):
            return False
        if suffix in IMAGE_SUFFIXES:
            items = self._process_image(path)
        elif suffix == ".pdf":
            items = self._process_pdf(path)
        elif suffix in VIDEO_SUFFIXES:
            supplied_transcript = path.with_suffix(".vtt")
            transcript_items = [] if supplied_transcript.exists() else self._transcribe(path)
            items = transcript_items + self._video_frames(path)
        else:
            items = self._transcribe(path)
        stat = path.stat()
        payload = {
            "media_analysis": True,
            "source_size": stat.st_size,
            "source_mtime_ns": stat.st_mtime_ns,
            "vision_model": self.settings.vision_model,
            "whisper_model": self.settings.whisper_model if suffix in VIDEO_SUFFIXES | AUDIO_SUFFIXES else None,
            "items": items,
        }
        media_sidecar(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return True

    def process_paths(self, paths: Iterable[Path], force: bool = False) -> MediaProcessResult:
        result = MediaProcessResult()
        for path in paths:
            if path.suffix.lower() not in MEDIA_SUFFIXES:
                result.skipped.append(path)
                continue
            try:
                if self.process_file(path, force=force):
                    result.processed.append(path)
                else:
                    result.unchanged.append(path)
            except Exception as exc:
                result.errors.append(f"{path}: {exc}")
        return result

    def process_tree(self, root: Path, force: bool = False) -> MediaProcessResult:
        paths = [
            path
            for path in sorted(root.rglob("*"))
            if path.is_file() and path.suffix.lower() in MEDIA_SUFFIXES and not any(part.startswith(".") for part in path.parts)
        ]
        return self.process_paths(paths, force=force)
