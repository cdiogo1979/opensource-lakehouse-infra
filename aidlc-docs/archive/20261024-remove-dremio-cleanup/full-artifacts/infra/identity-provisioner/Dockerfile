FROM debian:bookworm-slim@sha256:88200866dfff7ea7f5cbcb6ec7c8a701889efe6fe859fe64d6990e4b07ea4171

ARG KRB5_USER_VERSION=1.20.1-2+deb12u5
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        krb5-user="${KRB5_USER_VERSION}" \
        postgresql-client \
        python3 \
        python3-botocore \
    && rm -rf /var/lib/apt/lists/*

COPY provision-kerberos-identities.sh /usr/local/bin/provision-kerberos-identities
COPY provision-postgres-roles.sh /usr/local/bin/provision-postgres-roles
COPY provision-rustfs-identities.py /usr/local/bin/provision-rustfs-identities
RUN chmod 0755 /usr/local/bin/provision-kerberos-identities /usr/local/bin/provision-postgres-roles /usr/local/bin/provision-rustfs-identities
ENTRYPOINT ["/usr/local/bin/provision-kerberos-identities"]
