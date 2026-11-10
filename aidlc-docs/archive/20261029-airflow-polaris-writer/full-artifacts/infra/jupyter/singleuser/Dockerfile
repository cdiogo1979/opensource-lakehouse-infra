FROM local/lakehouse-spark-runtime:3.5.5_1.10.2 AS spark-runtime
FROM docker.io/jupyterhub/singleuser@sha256:def86b5a77bf6a69753454e32ad6c29e1772f48073793db62c91a19cf6c57cb7

USER root
COPY --from=spark-runtime /opt/spark /opt/spark
COPY --from=spark-runtime /usr/lib/jvm /usr/lib/jvm
COPY --from=spark-runtime /etc/java-17-openjdk /etc/java-17-openjdk
COPY infra/jupyter/singleuser/requirements.txt /tmp/singleuser-requirements.txt
RUN python -m pip install --no-cache-dir --requirement /tmp/singleuser-requirements.txt \
    && rm /tmp/singleuser-requirements.txt \
    && install -d -o jovyan -g users /home/jovyan/work

ENV SPARK_HOME=/opt/spark \
    JAVA_HOME=/usr/lib/jvm/java-17-openjdk-arm64 \
    PATH=/opt/spark/bin:/opt/spark/sbin:/usr/lib/jvm/java-17-openjdk-arm64/bin:${PATH} \
    PYTHONPATH=/opt/lakehouse:/opt/spark/python:/opt/spark/python/lib/py4j-0.10.9.7-src.zip

COPY infra/jupyter/singleuser/spark-defaults.conf /opt/spark/conf/spark-defaults.conf
COPY infra/jupyter/singleuser/lakehouse_broker_client.py infra/jupyter/singleuser/lakehouse_spark.py /opt/lakehouse/
COPY infra/jupyter/singleuser/start-session.sh /usr/local/bin/start-session.sh
RUN chmod 0755 /usr/local/bin/start-session.sh

WORKDIR /home/jovyan/work
USER jovyan
ENTRYPOINT ["/usr/local/bin/start-session.sh"]
