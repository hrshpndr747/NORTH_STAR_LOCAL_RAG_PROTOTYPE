#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-media.txt
ollama pull qwen3.5:4b
ollama pull qwen3-embedding:0.6b
test -f .env || cp .env.example .env
echo "Setup complete. Run ./run_mac_linux.sh next."
