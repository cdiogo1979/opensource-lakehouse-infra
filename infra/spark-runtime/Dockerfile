FROM maven:3.9.9-eclipse-temurin-17@sha256:f58d59b6273e785ac0a4477f6e9b5ba1d7731c75b906c0f7b34076f1851318cc AS token-provider-build
WORKDIR /build
COPY infra/spark-token-provider/pom.xml ./pom.xml
COPY infra/spark-token-provider/src ./src
RUN mvn --batch-mode --no-transfer-progress -DskipTests package
RUN mvn --batch-mode --no-transfer-progress org.apache.maven.plugins:maven-dependency-plugin:3.8.1:copy \
    -Dartifact=org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.10.2 \
    -DoutputDirectory=/build/iceberg-runtime \
 && mvn --batch-mode --no-transfer-progress org.apache.maven.plugins:maven-dependency-plugin:3.8.1:copy \
    -Dartifact=org.apache.iceberg:iceberg-aws-bundle:1.10.2 \
    -DoutputDirectory=/build/iceberg-runtime
# Hadoop S3A for streaming checkpoints (s3ckpt://): hadoop-aws matches the Spark image's Hadoop
# client 3.3.4, and the SDK bundle is the version that hadoop-aws 3.3.4 is built against.
RUN mvn --batch-mode --no-transfer-progress --strict-checksums org.apache.maven.plugins:maven-dependency-plugin:3.8.1:copy \
    -Dartifact=org.apache.hadoop:hadoop-aws:3.3.4 \
    -DoutputDirectory=/build/s3a \
 && mvn --batch-mode --no-transfer-progress --strict-checksums org.apache.maven.plugins:maven-dependency-plugin:3.8.1:copy \
    -Dartifact=com.amazonaws:aws-java-sdk-bundle:1.12.262 \
    -DoutputDirectory=/build/s3a

# The official Apache Spark image (Spark 3.5.9, Scala 2.12, Java 17 in /opt/java/openjdk, Python 3.10
# on Ubuntu 22.04), multi-architecture. It runs as root here, as the platform's run containers expect.
FROM apache/spark:3.5.9-scala2.12-java17-python3-ubuntu@sha256:f3d6eaa8bab8ec2e38f3c3918a5b2f8b253c95bcb19f9e87ad0e0cdacf9df2d5
USER root
# Ubuntu's security updates published since the image was built, and venv support for the
# workload environment (the image's Python 3.10 ships without ensurepip).
RUN apt-get update \
 && apt-get upgrade --yes --no-install-recommends \
 && apt-get install --yes --no-install-recommends python3.10-venv \
 && rm -rf /var/lib/apt/lists/*
COPY --from=token-provider-build /build/iceberg-runtime/iceberg-spark-runtime-3.5_2.12-1.10.2.jar /opt/spark/jars/
COPY --from=token-provider-build /build/iceberg-runtime/iceberg-aws-bundle-1.10.2.jar /opt/spark/jars/
COPY --from=token-provider-build /build/target/lakehouse-spark-token-provider.jar /opt/spark/jars/lakehouse-spark-token-provider.jar
COPY --from=token-provider-build /build/s3a/hadoop-aws-3.3.4.jar /build/s3a/aws-java-sdk-bundle-1.12.262.jar /opt/spark/jars/
COPY infra/jupyter/singleuser/spark-defaults.conf /opt/spark/conf/spark-defaults.conf

# The shared workload Python environment (infra/workload-python): a venv holding exactly
# the lock, used by spark-submit drivers and executors. The base image's system Python
# packages are not on the workload's path.
COPY infra/workload-python/requirements.lock /opt/lakehouse/requirements.lock
COPY infra/workload-python/workload_python.py /opt/lakehouse/workload_python.py
# The platform's Spark session module (lakehouse_spark), on the venv's path through the .pth,
# because Airflow run containers set PYTHONPATH to the product bundle only.
COPY infra/workload-python/python/ /opt/lakehouse/python/
RUN /usr/bin/python3 -m venv /opt/lakehouse/venv \
 && env -u PYTHONPATH /opt/lakehouse/venv/bin/pip install --quiet --disable-pip-version-check --no-input --no-cache-dir \
    --no-deps --only-binary=:all: --requirement /opt/lakehouse/requirements.lock \
 && /opt/lakehouse/venv/bin/python /opt/lakehouse/workload_python.py check-venv /opt/lakehouse/venv/bin/python \
    --lock /opt/lakehouse/requirements.lock
COPY infra/workload-python/lakehouse-platform.pth /opt/lakehouse/venv/lib/python3.10/site-packages/lakehouse-platform.pth
# A smaller runtime (spark-image-hardening): the base's compiler toolchain (gcc, headers, Perl,
# X11 and image libraries) isn't needed, since the platform installs prebuilt wheels only; and
# Spark here runs local[*] on Iceberg's REST catalog, so Hive (and Derby), ZooKeeper/Curator
# (standalone-master HA) and the Kubernetes, YARN and Mesos cluster managers are removed.
# hive-storage-api stays: Spark's ORC support needs it.
RUN apt-mark manual netbase >/dev/null \
 && apt-get purge --yes --auto-remove linux-libc-dev \
 && rm -rf /var/lib/apt/lists/* /opt/spark/yarn \
 && cd /opt/spark/jars \
 && find . -maxdepth 1 \( -name 'hive-*.jar' ! -name 'hive-storage-api-*.jar' -o -name 'spark-hive_*.jar' -o -name 'spark-hive-thriftserver_*.jar' \
      -o -name 'derby-*.jar' -o -name 'zookeeper*.jar' -o -name 'curator-*.jar' -o -name 'spark-kubernetes_*.jar' -o -name 'kubernetes-*.jar' \
      -o -name 'spark-yarn_*.jar' -o -name 'hadoop-yarn-server-web-proxy-*.jar' -o -name 'spark-mesos_*.jar' -o -name 'mesos-*.jar' \) -delete \
 && ! dpkg -s linux-libc-dev gcc >/dev/null 2>&1 \
 && /usr/bin/python3 --version && java -version 2>&1 | head -1 && /opt/spark/bin/spark-submit --version 2>&1 | grep -m1 -o "version 3\.5\.[0-9]*"
RUN env PYTHONPATH=/opt/lakehouse-bundle /opt/lakehouse/venv/bin/python -c "import lakehouse_spark, lakehouse_broker_client"
ENV PYSPARK_PYTHON=/opt/lakehouse/venv/bin/python \
    PYSPARK_DRIVER_PYTHON=/opt/lakehouse/venv/bin/python \
    PATH=/opt/lakehouse/venv/bin:${PATH}
