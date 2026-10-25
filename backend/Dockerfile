# syntax=docker/dockerfile:1.7
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 appuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api.py session_store.py state.py graph.py ./
COPY agents ./agents
COPY data/schemes ./data/schemes

RUN --mount=type=secret,id=nvidia_api_key,required=true \
    NVIDIA_API_KEY="$(cat /run/secrets/nvidia_api_key)" python -m agents.build_index \
    && python -c "import sqlite3; db=sqlite3.connect('/app/data/cache/chroma.sqlite3'); db.execute('PRAGMA wal_checkpoint(TRUNCATE)'); db.close()" \
    && chmod -R a-w /app/data/cache \
    && chown -R root:root /app/data

USER 10001
EXPOSE 8000
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
