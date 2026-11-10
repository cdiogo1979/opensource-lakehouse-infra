FROM quay.io/jupyterhub/jupyterhub:5.3.0

ENV PYTHONPATH=/etc/jupyterhub

USER root

COPY requirements.txt /tmp/jupyterhub-requirements.txt
RUN python -m pip install --no-cache-dir --requirement /tmp/jupyterhub-requirements.txt \
    && rm /tmp/jupyterhub-requirements.txt

COPY jupyterhub_config.py /etc/jupyterhub/jupyterhub_config.py
COPY lakehouse_ldap.py user-identities.json /etc/jupyterhub/
RUN mkdir -p /run/credential-validation/keytabs

CMD ["jupyterhub", "-f", "/etc/jupyterhub/jupyterhub_config.py"]
