FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System deps for pdf/image libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libgl1 libglib2.0-0 poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy engine and backend
COPY ocr-engine /app/ocr-engine
COPY backend /app/backend

# Install requirements
RUN pip install --no-cache-dir -r /app/ocr-engine/requirements.txt \
    && pip install --no-cache-dir -r /app/backend/requirements.txt

EXPOSE 8000

CMD ["gunicorn", "-c", "backend/gunicorn_conf.py", "backend.app.main:app"]
