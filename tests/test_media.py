from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from northstar_rag.loaders import load_file
from northstar_rag.media import MediaProcessor, MediaSettings, group_transcript_segments, media_sidecar


class FakeVisionClient:
    def __init__(self):
        self.calls = 0

    def vision(self, model, prompt, image_bytes):
        self.calls += 1
        assert image_bytes.startswith(b"\xff\xd8")
        return "VISIBLE TEXT: Emergency limit INR 5,000.\nVISUAL: A red warning box."


def test_transcript_segments_are_grouped_with_timestamps():
    groups = group_transcript_segments(
        [
            (1.2, 4.8, "Welcome to training."),
            (5.0, 8.4, "Report incidents immediately."),
        ]
    )
    assert len(groups) == 1
    assert groups[0]["locator"] == "00:00:01–00:00:08; automatic speech transcript"
    assert "Report incidents immediately" in groups[0]["text"]


def test_image_vision_is_cached_and_loaded_as_evidence(tmp_path):
    from PIL import Image, ImageDraw

    path = tmp_path / "notice.png"
    image = Image.new("RGB", (600, 200), "white")
    ImageDraw.Draw(image).text((20, 70), "Emergency limit INR 5,000", fill="black")
    image.save(path)

    client = FakeVisionClient()
    processor = MediaProcessor(client, MediaSettings())
    assert processor.process_file(path)
    assert not processor.process_file(path)
    assert client.calls == 1

    documents = load_file(path, tmp_path)
    assert documents[0].source_type == "image_vision"
    assert "INR 5,000" in documents[0].text
    assert documents[0].locator == "image OCR and visual analysis"


def test_scanned_pdf_uses_page_vision(tmp_path):
    from PIL import Image, ImageDraw

    image = Image.new("RGB", (900, 1200), "white")
    ImageDraw.Draw(image).text((80, 100), "SCANNED POLICY NUMBER 42", fill="black")
    path = tmp_path / "scan.pdf"
    image.save(path, "PDF")

    client = FakeVisionClient()
    processor = MediaProcessor(client, MediaSettings(pdf_ocr_min_chars=50))
    assert processor.process_file(path)
    payload = json.loads(media_sidecar(path).read_text(encoding="utf-8"))
    assert payload["items"][0]["source_type"] == "pdf_ocr"
    assert payload["items"][0]["locator"].startswith("page 1")


def test_audio_transcription_uses_timestamped_evidence(tmp_path):
    path = tmp_path / "meeting.mp3"
    path.write_bytes(b"fake audio for mocked model")
    processor = MediaProcessor(FakeVisionClient(), MediaSettings())

    class FakeWhisper:
        def transcribe(self, path, **kwargs):
            return iter(
                [
                    SimpleNamespace(start=2.0, end=4.0, text="The target is fifteen minutes."),
                    SimpleNamespace(start=4.5, end=8.0, text="Escalate immediately."),
                ]
            ), SimpleNamespace(language="en")

    processor._whisper = FakeWhisper()
    assert processor.process_file(path)
    documents = load_file(path, tmp_path)
    assert documents[0].source_type == "video_transcript"
    assert "00:00:02–00:00:08" in documents[0].locator
    assert "fifteen minutes" in documents[0].text

