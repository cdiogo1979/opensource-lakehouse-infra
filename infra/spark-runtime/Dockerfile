FROM maven:3.9.9-eclipse-temurin-17 AS token-provider-build
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
# Hadoop S3A for streaming checkpoints (s3ckpt://): hadoop-aws matches the image's Hadoop
# client 3.3.4, and the SDK bundle is the version that hadoop-aws 3.3.4 is built against.
RUN mvn --batch-mode --no-transfer-progress --strict-checksums org.apache.maven.plugins:maven-dependency-plugin:3.8.1:copy \
    -Dartifact=org.apache.hadoop:hadoop-aws:3.3.4 \
    -DoutputDirectory=/build/s3a \
 && mvn --batch-mode --no-transfer-progress --strict-checksums org.apache.maven.plugins:maven-dependency-plugin:3.8.1:copy \
    -Dartifact=com.amazonaws:aws-java-sdk-bundle:1.12.262 \
    -DoutputDirectory=/build/s3a

FROM tabulario/spark-iceberg:3.5.5_1.8.1@sha256:790a72e744e0d09f161e1b4c7c2f79625cc598cf0476da4703e62f1f4e023460
RUN rm -f /opt/spark/jars/iceberg-*-1.8.1.jar
COPY --from=token-provider-build /build/iceberg-runtime/iceberg-spark-runtime-3.5_2.12-1.10.2.jar /opt/spark/jars/
COPY --from=token-provider-build /build/iceberg-runtime/iceberg-aws-bundle-1.10.2.jar /opt/spark/jars/
COPY --from=token-provider-build /build/target/lakehouse-spark-token-provider.jar /opt/spark/jars/lakehouse-spark-token-provider.jar
COPY --from=token-provider-build /build/s3a/hadoop-aws-3.3.4.jar /build/s3a/aws-java-sdk-bundle-1.12.262.jar /opt/spark/jars/
COPY infra/jupyter/singleuser/spark-defaults.conf /opt/spark/conf/spark-defaults.conf

# The shared workload Python environment (infra/workload-python): a venv holding exactly
# the lock, used by spark-submit drivers and executors. The base image's own packages
# in /usr/local are not on the workload's path.
COPY infra/workload-python/requirements.lock /opt/lakehouse/requirements.lock
COPY infra/workload-python/workload_python.py /opt/lakehouse/workload_python.py
# The platform's Spark session module (lakehouse_spark), on the venv's path through the .pth,
# because Airflow run containers set PYTHONPATH to the product bundle only.
COPY infra/workload-python/python/ /opt/lakehouse/python/
RUN /usr/local/bin/python3 -m venv /opt/lakehouse/venv \
 && env -u PYTHONPATH /opt/lakehouse/venv/bin/pip install --quiet --disable-pip-version-check --no-input --no-cache-dir \
    --no-deps --only-binary=:all: --requirement /opt/lakehouse/requirements.lock \
 && /opt/lakehouse/venv/bin/python /opt/lakehouse/workload_python.py check-venv /opt/lakehouse/venv/bin/python \
    --lock /opt/lakehouse/requirements.lock
COPY infra/workload-python/lakehouse-platform.pth /opt/lakehouse/venv/lib/python3.10/site-packages/lakehouse-platform.pth
RUN env PYTHONPATH=/opt/lakehouse-bundle /opt/lakehouse/venv/bin/python -c "import lakehouse_spark, lakehouse_broker_client"
ENV PYSPARK_PYTHON=/opt/lakehouse/venv/bin/python \
    PYSPARK_DRIVER_PYTHON=/opt/lakehouse/venv/bin/python \
    PATH=/opt/lakehouse/venv/bin:${PATH}
