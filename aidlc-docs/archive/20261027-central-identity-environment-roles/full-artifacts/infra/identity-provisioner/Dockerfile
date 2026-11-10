FROM debian:bookworm-slim@sha256:88200866dfff7ea7f5cbcb6ec7c8a701889efe6fe859fe64d6990e4b07ea4171

ENV DEBIAN_FRONTEND=noninteractive
COPY apt-packages.lock /usr/local/share/identity-provisioner/apt-packages.lock

RUN printf '%s\n' \
      "Types: deb" \
      "URIs: http://snapshot.debian.org/archive/debian/20261026T000000Z/" \
      "Suites: bookworm" \
      "Components: main" \
      "Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg" \
      "Check-Valid-Until: no" \
      "" \
      "Types: deb" \
      "URIs: http://snapshot.debian.org/archive/debian-security/20261026T000000Z/" \
      "Suites: bookworm-security" \
      "Components: main" \
      "Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg" \
      "Check-Valid-Until: no" \
    > /etc/apt/sources.list.d/debian.sources \
    && rm -f /etc/apt/sources.list \
    && apt-get update \
    && xargs -a /usr/local/share/identity-provisioner/apt-packages.lock \
        apt-get install -y --no-install-recommends \
    && mkdir -p /usr/share/identity-provisioner \
    && dpkg-query -W -f='${binary:Package}=${Version}\n' \
        | sort > /usr/share/identity-provisioner/package-inventory.txt \
    && chmod 0644 /usr/share/identity-provisioner/package-inventory.txt \
    && rm -rf /var/lib/apt/lists/*

COPY provision-kerberos-identities.sh /usr/local/bin/provision-kerberos-identities
COPY provision-postgres-roles.sh /usr/local/bin/provision-postgres-roles
COPY provision-rustfs-identities.py /usr/local/bin/provision-rustfs-identities
COPY reconcile-rustfs-roles.py /usr/local/bin/reconcile-rustfs-roles.py
COPY rustfs-role-policy.json /etc/lakehouse/rustfs-role-policy.json
RUN chmod 0755 /usr/local/bin/provision-kerberos-identities /usr/local/bin/provision-postgres-roles /usr/local/bin/provision-rustfs-identities
ENTRYPOINT ["/usr/local/bin/provision-kerberos-identities"]
