FROM python:3.11-slim

# Prevent Python from writing bytecode and enable unbuffered output
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Set working directory
WORKDIR /app

# Install system dependencies required for PDF parsing, image OCR, and audio/video handling
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    ffmpeg \
    libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy python dependency lists and install them
COPY requirements.txt requirements-media.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-media.txt

# Copy application source code and sample datasets
COPY . .

# Expose Streamlit default port
EXPOSE 8501

# Default environment configuration for containerized execution
ENV OLLAMA_BASE_URL=http://host.docker.internal:11434

# Streamlit Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Launch Streamlit app
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]
