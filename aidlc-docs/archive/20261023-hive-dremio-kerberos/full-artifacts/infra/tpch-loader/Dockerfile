FROM --platform=linux/amd64 dremio/dremio-oss:26.0.5@sha256:b030b5dbffe2c789de51543763551c6b1fb6737c1030172a3a2d3b83c031588a AS dremio-jdbc

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

COPY --from=dremio-jdbc /opt/dremio/jars/jdbc-driver/dremio-jdbc-driver-26.0.5-202509091642240013-f5051a07.jar /opt/spark/jars/dremio-jdbc-driver-26.0.5.jar

ENV SPARK_SUBMIT_OPTS="--add-opens=java.base/java.nio=ALL-UNNAMED"
