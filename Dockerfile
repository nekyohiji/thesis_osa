FROM python:3.13-slim

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      libreoffice libreoffice-writer libreoffice-calc \
      python3-uno \
      fonts-dejavu-core fonts-noto \
      libxext6 libxrender1 libxinerama1 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD python manage.py migrate && \
    python manage.py collectstatic --noinput && \
    gunicorn myproject.wsgi:application --bind 0.0.0.0:$PORT --timeout 120

# Use system Python (has python3-uno) to run the LO script
ENV LIBREOFFICE_PY=/usr/local/bin/python

CMD gunicorn myproject.wsgi:application --bind 0.0.0.0:$PORT --timeout 120
RUN mkdir -p /opt/render/project/src/media
