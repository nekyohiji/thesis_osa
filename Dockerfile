# ---- Base Python
FROM python:3.13-slim

# ---- System deps: LibreOffice + UNO + fonts
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      libreoffice libreoffice-writer libreoffice-calc \
      python3-uno \
      fonts-dejavu-core fonts-noto \
      libxext6 libxrender1 libxinerama1 && \
    rm -rf /var/lib/apt/lists/*

# ---- App setup
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Collect static (ignore errors if no static yet)
RUN python manage.py collectstatic --noinput || true

# Use system Python (has python3-uno) for the LO script
ENV LIBREOFFICE_PY=/usr/local/bin/python

# Start the app (Render injects $PORT)
CMD gunicorn myproject.wsgi:application --bind 0.0.0.0:$PORT --timeout 120
