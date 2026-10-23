# The Edge Service image runs on a nearby Linux-capable computer or Raspberry Pi.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5000

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . ./

# SQLite data is supplied through the named volume declared in compose.
RUN mkdir -p /var/lib/icetrack-edge

EXPOSE 5000

# One worker is intentional: the service owns a local SQLite file and may run its
# synchronization worker. Increase threads, not workers, unless that design changes.
CMD ["/bin/sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-5000} --workers 1 --threads 4 app:app"]
