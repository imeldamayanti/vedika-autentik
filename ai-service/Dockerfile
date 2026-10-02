FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.8.6 /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

RUN apt-get update \
    && apt-get install --no-install-recommends -y tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src src
COPY templates templates
RUN uv sync --frozen --no-dev

EXPOSE 8001
CMD ["uv", "run", "--no-sync", "uvicorn", "vedika_ai.main:app", "--host", "0.0.0.0", "--port", "8001"]
