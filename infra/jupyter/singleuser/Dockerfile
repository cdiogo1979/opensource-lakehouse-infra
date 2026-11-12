FROM local/lakehouse-spark-runtime:3.5.9_1.10.2 AS spark-runtime
# jupyterhub/singleuser:6.1.1-7 (rebuilt 2026-11-07), multi-arch index digest.
FROM docker.io/jupyterhub/singleuser@sha256:4f4b2240f6645834fe68358ac4b0c2e1fc4d0c70549910d682281fee352c3fd6

USER root
COPY --from=spark-runtime /opt/spark /opt/spark
COPY --from=spark-runtime /opt/java/openjdk /opt/java/openjdk
# git for the users' own clones, and the JupyterLab Git extension (requirements.txt) uses it.
# Plus security updates the base digest doesn't have yet (Trivy: apt, libapt-pkg7.0).
RUN apt-get update \
    && apt-get install --yes --no-install-recommends git \
    && apt-get install --yes --only-upgrade apt libapt-pkg7.0 \
    && rm -rf /var/lib/apt/lists/*
COPY infra/jupyter/singleuser/requirements.txt /tmp/singleuser-requirements.txt
# The base's JupyterLab and notebook stay as shipped (patched upstream): they constrain the
# install, so an extension that needs older ones fails the build instead of downgrading them.
RUN python -m pip list --format=freeze | grep -iE '^(jupyterlab|notebook)==' > /tmp/base-pins.txt \
    && python -m pip install --no-cache-dir --requirement /tmp/singleuser-requirements.txt --constraint /tmp/base-pins.txt \
    && rm /tmp/singleuser-requirements.txt /tmp/base-pins.txt \
    && install -d -o jovyan -g users /home/jovyan/work

# The shared workload Python environment (infra/workload-python), as in the Spark runtime:
# Python 3.10.16 from conda-forge (not on PATH; JupyterLab keeps its own Python) and a venv
# holding exactly the lock. HOME=/root keeps the build out of /home/jovyan.
COPY infra/workload-python/requirements.lock /opt/lakehouse/requirements.lock
COPY infra/workload-python/workload_python.py /opt/lakehouse/workload_python.py
# The platform's Spark session module (lakehouse_spark), on the venv's path through the .pth.
COPY infra/workload-python/python/ /opt/lakehouse/python/
RUN HOME=/root mamba create --quiet --yes --prefix /opt/lakehouse/python3.10 \
       --override-channels --channel conda-forge python=3.10.16 \
    && HOME=/root mamba clean --all --yes --quiet \
    && /opt/lakehouse/python3.10/bin/python -m venv /opt/lakehouse/venv \
    && env -u PYTHONPATH HOME=/root /opt/lakehouse/venv/bin/pip install --quiet --disable-pip-version-check \
       --no-input --no-cache-dir --no-deps --only-binary=:all: --requirement /opt/lakehouse/requirements.lock \
    && /opt/lakehouse/venv/bin/python /opt/lakehouse/workload_python.py check-venv /opt/lakehouse/venv/bin/python \
       --lock /opt/lakehouse/requirements.lock
# The only kernel, under the name python3 so existing notebooks open with it; product
# extras from lakehouse-install-requirements are added to its path by the .pth file.
COPY infra/jupyter/singleuser/kernel.json /opt/conda/share/jupyter/kernels/python3/kernel.json
# A config.d drop-in (the base image's own jupyter_server_config.py stays): without it the
# server would also offer its own Python, because ipykernel is installed there.
COPY infra/jupyter/singleuser/lakehouse-kernels.json /etc/jupyter/jupyter_server_config.d/lakehouse-kernels.json
COPY infra/jupyter/singleuser/lakehouse-user-extras.pth /opt/lakehouse/venv/lib/python3.10/site-packages/lakehouse-user-extras.pth
COPY infra/workload-python/lakehouse-platform.pth /opt/lakehouse/venv/lib/python3.10/site-packages/lakehouse-platform.pth
RUN env -u PYTHONPATH /opt/lakehouse/venv/bin/python -c "import lakehouse_spark, lakehouse_broker_client, ipywidgets"
COPY infra/jupyter/singleuser/lakehouse-install-requirements /usr/local/bin/lakehouse-install-requirements
RUN chmod 0755 /usr/local/bin/lakehouse-install-requirements

ENV SPARK_HOME=/opt/spark \
    JAVA_HOME=/opt/java/openjdk \
    PATH=/opt/spark/bin:/opt/spark/sbin:/opt/java/openjdk/bin:${PATH} \
    PYSPARK_PYTHON=/opt/lakehouse/venv/bin/python \
    PYSPARK_DRIVER_PYTHON=/opt/lakehouse/venv/bin/python \
    PYTHONPATH=/opt/spark/python:/opt/spark/python/lib/py4j-0.10.9.7-src.zip

COPY infra/jupyter/singleuser/spark-defaults.conf /opt/spark/conf/spark-defaults.conf
COPY infra/jupyter/singleuser/start-session.sh /usr/local/bin/start-session.sh
RUN chmod 0755 /usr/local/bin/start-session.sh

WORKDIR /home/jovyan/work
USER jovyan
ENTRYPOINT ["/usr/local/bin/start-session.sh"]
