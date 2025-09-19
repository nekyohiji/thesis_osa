FROM python:3.13-slim

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      libreoffice-core libreoffice-calc libreoffice-writer \
      fonts-dejavu-core fonts-noto \
      libxext6 libxrender1 libxinerama1 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

# Optional: let you override soffice path if needed
# ENV SOFFICE_BIN=/usr/bin/soffice

RUN mkdir -p /app/staticfiles /app/media
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

CMD python manage.py migrate && \
    python manage.py collectstatic --noinput && \
    gunicorn myproject.wsgi:application \
      --bind 0.0.0.0:$PORT \
      --workers 2 \
      --threads 8 \
      --timeout 60 \
      --keep-alive 2