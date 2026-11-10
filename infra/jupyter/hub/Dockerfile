FROM docker.io/jupyterhub/jupyterhub@sha256:d0f48a46b41c9e6d4a9eeecef6674fd83b1160abfdfe3a6eec49e9d1bedd06c6

ENV PYTHONPATH=/etc/jupyterhub
USER root

COPY requirements.txt requirements-lock.txt /tmp/jupyterhub-deps/
RUN python -m pip install --no-cache-dir \
      --requirement /tmp/jupyterhub-deps/requirements.txt \
      --constraint /tmp/jupyterhub-deps/requirements-lock.txt \
    && rm -rf /tmp/jupyterhub-deps

COPY jupyterhub_config.py lakehouse_spawner.py lakehouse_policy.py lakehouse_token_broker.py lakehouse_jupyterhub.py healthcheck.py /etc/jupyterhub/
CMD ["python", "/etc/jupyterhub/lakehouse_jupyterhub.py", "-f", "/etc/jupyterhub/jupyterhub_config.py"]
