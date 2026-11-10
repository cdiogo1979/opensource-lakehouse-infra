ARG STARROCKS_BASE
FROM ${STARROCKS_BASE}

ARG KRB5_USER_VERSION=1.20.1-6ubuntu2.10
ARG CRON_PACKAGE_VERSION=3.0pl1-184ubuntu2
ENV DEBIAN_FRONTEND=noninteractive

USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        krb5-user="${KRB5_USER_VERSION}" \
        cron="${CRON_PACKAGE_VERSION}" \
    && rm -rf /var/lib/apt/lists/*

COPY fe/entrypoint.sh /usr/local/bin/starrocks-fe-entrypoint
COPY kerberos/refresh-ticket.sh /usr/local/bin/starrocks-refresh-ticket
COPY kerberos/render-hadoop-config.sh /usr/local/bin/starrocks-render-hadoop-config
COPY kerberos/starrocks-ticket-refresh /etc/cron.d/starrocks-ticket-refresh
RUN chmod 0755 /usr/local/bin/starrocks-fe-entrypoint /usr/local/bin/starrocks-refresh-ticket /usr/local/bin/starrocks-render-hadoop-config \
    && chmod 0644 /etc/cron.d/starrocks-ticket-refresh

ENTRYPOINT ["/usr/bin/tini-static", "--"]
CMD ["/usr/local/bin/starrocks-fe-entrypoint"]
