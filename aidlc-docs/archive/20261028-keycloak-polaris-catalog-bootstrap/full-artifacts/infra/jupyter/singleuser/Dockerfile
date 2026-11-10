FROM tabulario/spark-iceberg:3.5.5_1.8.1@sha256:790a72e744e0d09f161e1b4c7c2f79625cc598cf0476da4703e62f1f4e023460

USER root

RUN printf '%s\n' \
      'deb [check-valid-until=no] http://snapshot.debian.org/archive/debian/20250224T000000Z bullseye main' \
      'deb [check-valid-until=no] http://snapshot.debian.org/archive/debian-security/20250224T000000Z bullseye-security main' \
      'deb [check-valid-until=no] http://snapshot.debian.org/archive/debian/20250224T000000Z bullseye-updates main' \
      > /etc/apt/sources.list \
    && apt-get -o Acquire::Retries=3 update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends krb5-user \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 jovyan \
    && useradd --uid 10001 --gid 10001 --create-home --shell /bin/bash jovyan \
    && install -d -o 10001 -g 10001 /home/jovyan/work /run/credentials

COPY infra/kerberos/krb5.conf /etc/krb5.conf
COPY infra/jupyter/singleuser/requirements.txt /tmp/jupyter-requirements.txt
RUN python -m pip install --no-cache-dir --requirement /tmp/jupyter-requirements.txt \
    && rm /tmp/jupyter-requirements.txt

COPY infra/jupyter/singleuser/spark-defaults.conf /opt/spark/conf/spark-defaults.conf
COPY infra/jupyter/singleuser/start-session.sh /usr/local/bin/start-session.sh
RUN chmod 0755 /usr/local/bin/start-session.sh

WORKDIR /home/jovyan/work
USER 10001:10001

ENTRYPOINT ["/usr/local/bin/start-session.sh"]
