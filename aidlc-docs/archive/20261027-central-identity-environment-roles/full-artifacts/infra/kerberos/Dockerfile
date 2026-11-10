FROM debian:bookworm-slim@sha256:88200866dfff7ea7f5cbcb6ec7c8a701889efe6fe859fe64d6990e4b07ea4171

ARG KRB5_PACKAGE_VERSION=1.20.1-2+deb12u5

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        krb5-kdc=${KRB5_PACKAGE_VERSION} \
        krb5-admin-server=${KRB5_PACKAGE_VERSION} \
        krb5-user=${KRB5_PACKAGE_VERSION} \
    && rm -rf /var/lib/apt/lists/*

COPY krb5.conf /etc/krb5.conf
COPY kdc.conf /etc/krb5kdc/kdc.conf
COPY kadm5.acl /etc/krb5kdc/kadm5.acl
COPY entrypoint.sh /usr/local/sbin/kdc-entrypoint
COPY healthcheck.sh /usr/local/sbin/kdc-healthcheck

RUN chmod 0755 /usr/local/sbin/kdc-entrypoint /usr/local/sbin/kdc-healthcheck

EXPOSE 88/tcp 88/udp 749/tcp

ENTRYPOINT ["/usr/local/sbin/kdc-entrypoint"]
