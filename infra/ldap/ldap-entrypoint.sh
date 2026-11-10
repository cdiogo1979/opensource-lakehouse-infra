#!/bin/sh
# Render slapd.conf, seed an empty directory once, keep the Keycloak bind
# password in step with its protected file, and run slapd on LDAPS and the
# local ldapi socket only. Passwords are read from files and hashed in-process;
# none appears in arguments, the config, or logs.
set -eu

SUFFIX="dc=lakehouse,dc=local"
CONF=/etc/openldap/slapd.conf
DATA=/var/lib/openldap/data

secret() {
  [ -f "$1" ] && [ ! -L "$1" ] || { echo "Required LDAP secret is unavailable: $(basename "$1")" >&2; exit 1; }
  head -n 1 "$1"
}

# slappasswd -T reads the password from a file, so it never becomes an argument.
hash_file() {
  slappasswd -o module-load=argon2.so -h '{ARGON2}' -T "$1"
}

for path in /run/certs/ldap-ca.crt /run/certs/ldap-server.crt /run/certs/ldap-server-key.pem; do
  [ -f "$path" ] || { echo "Required LDAP TLS material is unavailable: $(basename "$path")" >&2; exit 1; }
done

mkdir -p /var/lib/openldap/run /run/openldap
umask 077
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
secret /run/secrets/ldap_admin_password | tr -d '\n' > "$work/admin"
secret /run/secrets/ldap_keycloak_password | tr -d '\n' > "$work/keycloak"
admin_hash=$(hash_file "$work/admin")
keycloak_hash=$(hash_file "$work/keycloak")

sed "s|@ADMIN_HASH@|$admin_hash|" /opt/lakehouse/slapd.conf.template > "$CONF"
chmod 0600 "$CONF"

if [ ! -f "$DATA/data.mdb" ]; then
  cat > "$work/seed.ldif" <<LDIF
dn: $SUFFIX
objectClass: dcObject
objectClass: organization
o: lakehouse
dc: lakehouse

dn: ou=people,$SUFFIX
objectClass: organizationalUnit
ou: people

dn: ou=services,$SUFFIX
objectClass: organizationalUnit
ou: services

dn: cn=keycloak,ou=services,$SUFFIX
objectClass: applicationProcess
objectClass: simpleSecurityObject
cn: keycloak
userPassword: $keycloak_hash
LDIF
  slapadd -f "$CONF" -l "$work/seed.ldif"
  echo "LDAP directory seeded (ou=people, ou=services, cn=keycloak)."
else
  # The bind password file is the source of truth: refresh its hash offline.
  cat > "$work/keycloak.ldif" <<LDIF
dn: cn=keycloak,ou=services,$SUFFIX
changetype: modify
replace: userPassword
userPassword: $keycloak_hash
LDIF
  slapmodify -f "$CONF" -l "$work/keycloak.ldif" >/dev/null
fi

rm -rf "$work"
trap - EXIT
exec slapd -d 0 -f "$CONF" -h "ldaps:/// ldapi:///"
