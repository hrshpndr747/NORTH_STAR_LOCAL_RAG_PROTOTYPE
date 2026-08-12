#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
test -x .venv/bin/python || { echo "Run ./setup_mac_linux.sh first."; exit 1; }
test -f .env || cp .env.example .env
. .venv/bin/activate
python -m streamlit run app.py

