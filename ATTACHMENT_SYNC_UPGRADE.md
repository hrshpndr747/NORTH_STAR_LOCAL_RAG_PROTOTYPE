# Automatic Confluence attachment sync

This build adds automatic attachment retrieval to the existing page sync.

## Use it

Keep the existing `.env` values and optionally add:

```text
CONFLUENCE_DOWNLOAD_ATTACHMENTS=true
CONFLUENCE_ATTACHMENT_MAX_MB=250
CONFLUENCE_ATTACHMENT_EXTENSIONS=.pdf,.docx,.xlsx,.vtt,.txt,.md,.csv,.json,.db,.sqlite,.sqlite3,.png,.jpg,.jpeg,.tif,.tiff,.bmp,.webp,.mp4,.mov,.mkv,.webm,.avi,.mp3,.wav,.m4a,.flac,.aac,.ogg
```

Then run from the project directory on Windows:

```powershell
.\.venv\Scripts\python.exe scripts\sync_confluence.py
```

The command now reports downloaded pages, new or updated attachments, unchanged attachments, skipped files, and errors. Start the app and select **Build / rebuild index** after the sync.

## Storage layout

```text
data/confluence/
  PAGE_ID_Page_Title.json
  attachments/
    PAGE_ID/
      Attachment.pdf
      .Attachment.pdf.confluence.json
```

The hidden JSON file supplies attachment version and Confluence link information for citations. Do not delete it while keeping the corresponding attachment.

## Defaults

- Supported: document/data files, common images, common video formats, and common audio formats.
- Maximum size: 250 MB per attachment.
- Images receive local OCR/vision analysis. Video/audio receive automatic speech transcription; sampled video frames receive OCR/vision analysis.
- Existing files are downloaded again only when their Confluence attachment version changes.
