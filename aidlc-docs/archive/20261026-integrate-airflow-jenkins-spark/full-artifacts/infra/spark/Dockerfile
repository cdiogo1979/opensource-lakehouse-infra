ARG SPARK_BASE_IMAGE=tabulario/spark-iceberg:3.5.5_1.8.1@sha256:790a72e744e0d09f161e1b4c7c2f79625cc598cf0476da4703e62f1f4e023460
FROM ${SPARK_BASE_IMAGE}

USER root
# Debian Bullseye's moving security mirror can publish an index before all
# referenced package files are available. Use the matching immutable snapshot
# already documented by the pinned upstream image instead.
RUN sed -i \
      -e 's|^# deb http://snapshot.debian.org/archive/debian/20250224T000000Z bullseye main|deb http://snapshot.debian.org/archive/debian/20250224T000000Z bullseye main|' \
      -e 's|^deb http://deb.debian.org/debian bullseye main|# deb http://deb.debian.org/debian bullseye main|' \
      -e 's|^# deb http://snapshot.debian.org/archive/debian-security/20250224T000000Z bullseye-security main|deb http://snapshot.debian.org/archive/debian-security/20250224T000000Z bullseye-security main|' \
      -e 's|^deb http://deb.debian.org/debian-security bullseye-security main|# deb http://deb.debian.org/debian-security bullseye-security main|' \
      -e 's|^# deb http://snapshot.debian.org/archive/debian/20250224T000000Z bullseye-updates main|deb http://snapshot.debian.org/archive/debian/20250224T000000Z bullseye-updates main|' \
      -e 's|^deb http://deb.debian.org/debian bullseye-updates main|# deb http://deb.debian.org/debian bullseye-updates main|' \
      /etc/apt/sources.list \
    && apt-get -o Acquire::Check-Valid-Until=false update \
    && DEBIAN_FRONTEND=noninteractive apt-get install --yes --no-install-recommends krb5-user \
    && rm -rf /var/lib/apt/lists/*
