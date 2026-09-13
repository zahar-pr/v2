#!/bin/sh
# Первый старт: разворачиваем готовый индекс, чтобы сервис не прогревался с нуля.
set -e
DB_PATH="${DB_PATH:-/app/data/provizia.db}"
if [ ! -f "$DB_PATH" ] && [ -f /app/seed/provizia.db ]; then
  mkdir -p "$(dirname "$DB_PATH")"
  cp /app/seed/provizia.db "$DB_PATH"
  echo "индекс развёрнут из образа: $DB_PATH"
fi
export DB_PATH
exec uvicorn main:app --app-dir backend --host 0.0.0.0 --port "${PORT:-7860}"
