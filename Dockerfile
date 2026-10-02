# Image untuk Railway: API + worker + (sementara) stub mesin dalam satu container.
# Dibangun dari akar repo karena API membaca dataset/manifest.json.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend backend
COPY dataset/manifest.json dataset/manifest.json

WORKDIR /app/backend
CMD ["sh", "start.sh"]
