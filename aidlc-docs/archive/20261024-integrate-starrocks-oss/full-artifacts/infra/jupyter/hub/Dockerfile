FROM quay.io/jupyterhub/jupyterhub:5.3.0

USER root

COPY requirements.txt /tmp/jupyterhub-requirements.txt
RUN python -m pip install --no-cache-dir --requirement /tmp/jupyterhub-requirements.txt \
    && rm /tmp/jupyterhub-requirements.txt

COPY jupyterhub_config.py /etc/jupyterhub/jupyterhub_config.py

CMD ["jupyterhub", "-f", "/etc/jupyterhub/jupyterhub_config.py"]
