FROM tabulario/spark-iceberg:3.5.5_1.8.1@sha256:790a72e744e0d09f161e1b4c7c2f79625cc598cf0476da4703e62f1f4e023460

USER root

RUN printf '%s\n' \
      'deb [check-valid-until=no] http://snapshot.debian.org/archive/debian/20250224T000000Z bullseye main' \
      'deb [check-valid-until=no] http://snapshot.debian.org/archive/debian-security/20250224T000000Z bullseye-security main' \
      'deb [check-valid-until=no] http://snapshot.debian.org/archive/debian/20250224T000000Z bullseye-updates main' \
      > /etc/apt/sources.list \
    && apt-get -o Acquire::Retries=3 update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends krb5-user \
    && rm -rf /var/lib/apt/lists/*

