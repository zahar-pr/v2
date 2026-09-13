FROM node:22-slim AS frontend

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install

COPY frontend .
RUN npm run build

FROM python:3.12-slim

RUN useradd -m -u 1000 provizia
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend backend
COPY docker-entrypoint.sh .
COPY data/seed.db seed/provizia.db
COPY --from=frontend /app/frontend/dist frontend/dist

RUN chown -R provizia:provizia /app
USER provizia

ENV PORT=7860
ENV DB_PATH=/app/data/provizia.db
ENV PYTHONUNBUFFERED=1
EXPOSE 7860

CMD ["./docker-entrypoint.sh"]
