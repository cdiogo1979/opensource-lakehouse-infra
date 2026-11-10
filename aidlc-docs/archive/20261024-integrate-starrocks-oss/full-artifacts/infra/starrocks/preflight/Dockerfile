FROM debian:bookworm-slim@sha256:88200866dfff7ea7f5cbcb6ec7c8a701889efe6fe859fe64d6990e4b07ea4171

COPY check-paired-state.sh /usr/local/bin/check-paired-state
RUN chmod 0755 /usr/local/bin/check-paired-state

ENTRYPOINT ["/bin/sh", "/usr/local/bin/check-paired-state"]
