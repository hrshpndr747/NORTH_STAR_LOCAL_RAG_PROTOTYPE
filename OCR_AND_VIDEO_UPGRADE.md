# Local OCR and video understanding upgrade

The RAG prototype can now generate searchable evidence from images, scanned PDFs, video, and audio without sending media to a cloud AI API.

## Upgrade an existing Windows installation

1. Keep your existing `.env` file.
2. Extract the upgraded project over your project folder.
3. Run `setup_windows.bat` once to install Pillow, PDFium, PyAV, and Faster-Whisper.
4. Run `run_windows.bat`.
5. Select **Build / rebuild index**.

The first build may be slow because the Whisper speech model is downloaded and each scanned page/video frame is analyzed locally. Later builds reuse cached media analysis until a source file changes.

## What each pipeline reads

| Source | Local extraction | Citation |
| --- | --- | --- |
| PNG/JPG/TIFF/BMP/WebP | Visible-text OCR plus factual visual description using Qwen3.5 Vision | Image attachment |
| Scanned/image-only PDF | Render page, then local OCR/vision | PDF page |
| MP4/MOV/MKV/WebM/AVI | Faster-Whisper speech transcript plus sampled-frame OCR/vision | Timestamp |
| MP3/WAV/M4A/FLAC/AAC/OGG | Faster-Whisper speech transcript | Timestamp |
| Existing VTT | Uses the supplied transcript; does not transcribe the matching video again | Timestamp |

## Accuracy controls

- Use `WHISPER_MODEL=medium` for better speech accuracy if your computer has enough memory and you accept slower processing.
- Set `WHISPER_LANGUAGE=en` (or another language code) when automatic language detection is unreliable.
- Reduce `VIDEO_FRAME_INTERVAL_SECONDS` from `15` to `5` for slide-heavy videos, which increases processing time substantially.
- Increase `PDF_OCR_MIN_CHARS` when pages contain a weak text layer and OCR should still run.
- Always open the cited page/image/timestamp to verify consequential numbers or instructions.

This is retrieval-oriented video understanding, not continuous event detection: audio is transcribed, and representative frames are analyzed at intervals.
