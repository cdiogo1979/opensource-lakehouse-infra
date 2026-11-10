# Hive 3.1.3's upstream container is amd64-only. Reuse its pinned,
# architecture-neutral Hive/Hadoop/Tez distributions while running them on
# the host-native Java 8 runtime. This avoids executing the Hive JVM under
# QEMU on arm64 hosts.
ARG HIVE_DIST_PLATFORM=linux/amd64
FROM --platform=${HIVE_DIST_PLATFORM} apache/hive:3.1.3@sha256:d102ba29ad07e93c303894896203a80b903c0001d80221f1cb9fea92dcac06e4 AS hive-distribution

FROM eclipse-temurin:8-jre-jammy@sha256:49b31e882495abeb1118de417ee696bdc929d2de238730920f1468025fc393a4

USER root
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends postgresql-client \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1000 hive \
    && useradd --uid 1000 --gid hive --create-home --shell /bin/bash hive

ENV HADOOP_HOME=/opt/hadoop \
    HIVE_HOME=/opt/hive \
    TEZ_HOME=/opt/tez \
    JAVA_HOME=/opt/java/openjdk \
    PATH=/opt/hive/bin:/opt/hadoop/bin:/opt/java/openjdk/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

COPY --from=hive-distribution --chown=1000:1000 /opt/hadoop /opt/hadoop
COPY --from=hive-distribution --chown=1000:1000 /opt/hive /opt/hive
COPY --from=hive-distribution --chown=1000:1000 /opt/tez /opt/tez
COPY --from=hive-distribution --chown=1000:1000 /entrypoint.sh /entrypoint.sh

# The distribution stage is amd64. Force Hadoop's portable Java fallbacks on
# the native arm64 runtime rather than trying to load its amd64 JNI libraries.
RUN rm -rf /opt/hadoop/lib/native/* \
    && mkdir -p /opt/hive/data/warehouse /opt/hive/scratch /home/hive/.beeline \
    && chown -R hive:hive /opt/hadoop /opt/hive /opt/tez /home/hive \
    && chmod +x /entrypoint.sh

ADD https://repo.maven.apache.org/maven2/org/postgresql/postgresql/42.7.14/postgresql-42.7.14.jar /opt/hive/lib/postgresql-42.7.14.jar
ADD https://repo.maven.apache.org/maven2/org/apache/hadoop/hadoop-aws/3.1.0/hadoop-aws-3.1.0.jar /opt/hive/lib/hadoop-aws-3.1.0.jar
ADD https://repo.maven.apache.org/maven2/com/amazonaws/aws-java-sdk-bundle/1.11.271/aws-java-sdk-bundle-1.11.271.jar /opt/hive/lib/aws-java-sdk-bundle-1.11.271.jar
RUN chown hive:hive /opt/hive/lib/postgresql-42.7.14.jar \
    /opt/hive/lib/hadoop-aws-3.1.0.jar \
    /opt/hive/lib/aws-java-sdk-bundle-1.11.271.jar

USER hive
WORKDIR /opt/hive
EXPOSE 9083
ENTRYPOINT ["sh", "-c", "/entrypoint.sh"]
