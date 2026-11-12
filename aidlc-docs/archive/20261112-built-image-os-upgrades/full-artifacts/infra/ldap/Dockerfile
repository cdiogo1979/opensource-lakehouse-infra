# OpenLDAP directory for the lakehouse users (Keycloak federates them; StarRocks
# checks passwords against them). Packages are pinned to the probed versions.
FROM alpine:3.22@sha256:49340b346798875b5592e5d420241f2f9cfba5f47e62ebb1446a1b34734e898f

# Take the base's distribution fixes as they are released (built-image-os-upgrades).
RUN apk upgrade --no-cache
RUN apk add --no-cache \
      openldap=2.6.8-r0 \
      openldap-back-mdb=2.6.8-r0 \
      openldap-clients=2.6.8-r0 \
      openldap-passwd-argon2=2.6.8-r0 \
    && mkdir -p /var/lib/openldap/data /var/lib/openldap/run /run/openldap

COPY slapd.conf.template /opt/lakehouse/slapd.conf.template
COPY ldap-entrypoint.sh /opt/lakehouse/ldap-entrypoint.sh
RUN chmod 0755 /opt/lakehouse/ldap-entrypoint.sh

ENTRYPOINT ["/opt/lakehouse/ldap-entrypoint.sh"]
