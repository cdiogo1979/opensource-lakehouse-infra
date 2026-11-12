FROM apache/airflow:3.3.2-python3.10@sha256:db151dc175a22504ba8729ec38dd3964326935dfa6c4c2d6480ebd14d33b3b29

USER root
# Take the base's distribution fixes as they are released (built-image-os-upgrades).
RUN apt-get update \
 && apt-get upgrade --yes --no-install-recommends \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /requirements.txt

USER airflow
RUN pip install --no-cache-dir \
      --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-3.3.2/constraints-3.10.txt" \
      -r /requirements.txt

USER root
RUN mkdir -p /opt/airflow/scripts \
    && chown -R airflow:root /opt/airflow/scripts

COPY --chown=airflow:root --chmod=755 airflow-entrypoint.sh /opt/airflow/scripts/airflow-entrypoint.sh
COPY --chown=airflow:root --chmod=755 validate-bundle-config.py /opt/airflow/scripts/validate-bundle-config.py
COPY --chown=airflow:root --chmod=755 airflow-secret-command.py /opt/airflow/scripts/airflow-secret-command.py
COPY --chown=airflow:root --chmod=755 bootstrap-airflow-admin.py /opt/airflow/scripts/bootstrap-airflow-admin.py
COPY --chown=airflow:root --chmod=755 ensure-git-connection.py /opt/airflow/scripts/ensure-git-connection.py
COPY --chown=airflow:root --chmod=644 airflow_sso_roles.py airflow_oauth_security_manager.py airflow_auth_views.py webserver_config.py /opt/airflow/
USER airflow
ENTRYPOINT ["/usr/bin/dumb-init", "--", "/opt/airflow/scripts/airflow-entrypoint.sh"]
