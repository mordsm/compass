FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
ENV COMPASS_DATABASE_PATH=/data/compass.db

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./

RUN pip install --no-cache-dir uv \
    && uv sync --frozen --no-dev

COPY app ./app

EXPOSE 8000

CMD ["sh", "-c", "uv run uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
