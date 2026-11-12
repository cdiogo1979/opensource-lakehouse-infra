FROM python:3.10-slim-bookworm@sha256:5be5aaecb962a41567bc8041f1e9e3432cb085b037fe057f9a562630b2e4b370

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Take the base's distribution fixes as they are released (built-image-os-upgrades).
RUN apt-get update \
 && apt-get upgrade --yes --no-install-recommends \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --disable-pip-version-check -r /app/requirements.txt
COPY app.py /app/app.py

USER 65532:65532
EXPOSE 8443
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8443", "--workers", "1", "--ssl-certfile", "/run/certs/airflow-token-broker-server.crt", "--ssl-keyfile", "/run/certs/airflow-token-broker-server-key.pem", "--no-access-log"]
