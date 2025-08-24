FROM python:3.13-slim

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      libreoffice libreoffice-writer libreoffice-calc \
      python3-uno \
      fonts-dejavu-core fonts-noto \
      libxext6 libxrender1 libxinerama1 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 
ENV PYTHONUNBUFFERED=1
# Fix the LibreOffice Python path
ENV LIBREOFFICE_PY=/usr/lib/libreoffice/program/python3

# Create necessary directories
RUN mkdir -p /app/staticfiles /opt/render/project/src/media

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Single CMD with all startup commands
CMD python manage.py migrate && \
    python manage.py collectstatic --noinput && \
    gunicorn myproject.wsgi:application --bind 0.0.0.0:$PORT --timeout 120
