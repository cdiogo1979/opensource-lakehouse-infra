# jupyterhub/jupyterhub:6.1.1-7 (rebuilt 2026-11-07), multi-arch index digest.
FROM docker.io/jupyterhub/jupyterhub@sha256:48973496688583afca1c29571c7e69849ed9b9ffb74874af29b2c87e787aa8c6

ENV PYTHONPATH=/etc/jupyterhub
USER root
# Security updates the base digest doesn't have yet (Trivy: apt, libapt-pkg7.0).
RUN apt-get update \
    && apt-get install --yes --only-upgrade apt libapt-pkg7.0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-lock.txt /tmp/jupyterhub-deps/
RUN python -m pip install --no-cache-dir \
      --requirement /tmp/jupyterhub-deps/requirements.txt \
      --constraint /tmp/jupyterhub-deps/requirements-lock.txt \
    && rm -rf /tmp/jupyterhub-deps

COPY jupyterhub_config.py lakehouse_spawner.py lakehouse_policy.py lakehouse_token_broker.py lakehouse_jupyterhub.py healthcheck.py /etc/jupyterhub/
CMD ["python", "/etc/jupyterhub/lakehouse_jupyterhub.py", "-f", "/etc/jupyterhub/jupyterhub_config.py"]
