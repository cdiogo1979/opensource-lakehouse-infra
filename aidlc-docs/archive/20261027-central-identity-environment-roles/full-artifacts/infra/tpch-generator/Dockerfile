FROM debian:bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        gcc \
        make \
        libc6-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

RUN curl -L \
    https://github.com/electrum/tpch-dbgen/archive/refs/heads/master.tar.gz \
    -o tpch-dbgen.tar.gz \
    && tar -xzf tpch-dbgen.tar.gz \
    && mv tpch-dbgen-master dbgen

WORKDIR /build/dbgen

RUN make -f makefile MACHINE=LINUX

COPY generate.sh /generate.sh

RUN chmod +x /generate.sh

ENTRYPOINT ["/generate.sh"]