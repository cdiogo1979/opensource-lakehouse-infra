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

FROM tabulario/spark-iceberg:3.5.5_1.8.1@sha256:790a72e744e0d09f161e1b4c7c2f79625cc598cf0476da4703e62f1f4e023460
RUN rm -f /opt/spark/jars/iceberg-*-1.8.1.jar
COPY --from=token-provider-build /build/iceberg-runtime/iceberg-spark-runtime-3.5_2.12-1.10.2.jar /opt/spark/jars/
COPY --from=token-provider-build /build/iceberg-runtime/iceberg-aws-bundle-1.10.2.jar /opt/spark/jars/
COPY --from=token-provider-build /build/target/lakehouse-spark-token-provider.jar /opt/spark/jars/lakehouse-spark-token-provider.jar
COPY infra/jupyter/singleuser/spark-defaults.conf /opt/spark/conf/spark-defaults.conf
