#!/usr/bin/env bash
# Запуск сервиса: http://127.0.0.1:8000
set -e
cd "$(dirname "$0")"
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q -r requirements.txt
exec .venv/bin/uvicorn main:app --app-dir backend --host 127.0.0.1 --port "${PORT:-8000}"
