FROM python:3.12-alpine@sha256:1b668429b3511ab407d8e00648891631b0b1a4d7e15e3ca70f38ab5b91ad4ab4

# Take the base's distribution fixes as they are released (built-image-os-upgrades).
RUN apk upgrade --no-cache
# MySQL-protocol client for the scheduled StarRocks user reconcile.
RUN apk add --no-cache mariadb-client=11.8.9-r0
# The product model parses the mounted data product files.
RUN python -m pip install --no-cache-dir PyYAML==6.0.3

WORKDIR /opt/lakehouse
COPY infra/products/data_products.py ./products/data_products.py
COPY infra/polaris/reconcile-keycloak-groups.py ./polaris/reconcile-keycloak-groups.py
COPY infra/starrocks/starrocks_common.py ./starrocks/starrocks_common.py
COPY infra/starrocks/reconcile-starrocks-users.py ./starrocks/reconcile-starrocks-users.py
COPY infra/polaris/reconciler/run.sh ./run.sh
RUN chmod 0755 ./run.sh

# Product files are mounted read-only and read on every cycle.
ENV LAKEHOUSE_DATA_PRODUCTS_DIR=/opt/lakehouse/data-products
# compose.core.yml mounts the current platform code over these copies (read-only), so the
# cycle always runs the repository's product model and scripts; sh runs the mounted run.sh.
ENTRYPOINT ["/bin/sh", "/opt/lakehouse/run.sh"]
