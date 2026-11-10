FROM python:3.10-slim-bookworm@sha256:5be5aaecb962a41567bc8041f1e9e3432cb085b037fe057f9a562630b2e4b370 AS python-runtime

FROM jenkins/jenkins:lts-jdk21@sha256:a660310e39ade10631f774bacd5219de767dfd08947ea5c32a739b5e5bb382c1

USER root

# Keep the Jenkins image as the runtime base and add only the pinned Python 3.10 runtime.
COPY --from=python-runtime /usr/local/ /usr/local/

# Fail the image build if the copied interpreter cannot load on the Jenkins base
# or if a required validation tool is missing.
RUN ldconfig \
    && python3.10 --version \
    && python3.10 -c 'import bz2, ctypes, hashlib, lzma, pathlib, py_compile, sqlite3, ssl, unittest' \
    && command -v bash \
    && bash --version >/dev/null \
    && command -v git \
    && git --version

USER jenkins
