FROM python:3.10-slim-bookworm@sha256:5be5aaecb962a41567bc8041f1e9e3432cb085b037fe057f9a562630b2e4b370 AS python-runtime

FROM jenkins/jenkins:lts-jdk21@sha256:a660310e39ade10631f774bacd5219de767dfd08947ea5c32a739b5e5bb382c1

USER root
# Take the base's distribution fixes as they are released (built-image-os-upgrades).
RUN apt-get update \
 && apt-get upgrade --yes --no-install-recommends \
 && rm -rf /var/lib/apt/lists/*

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

# Install the exact plugin set; the entrypoint copies it over the home's
# plugins at start when PLUGINS_FORCE_UPGRADE=true, so the image is authoritative.
COPY --chown=jenkins:jenkins plugins.txt /usr/share/jenkins/ref/plugins.txt
# The check compares name:version from each plugin's manifest, so a dependency
# resolved to another version also fails the build.
RUN jenkins-plugin-cli --plugin-file /usr/share/jenkins/ref/plugins.txt \
    && expected="$(grep -v -e '^#' -e '^$' /usr/share/jenkins/ref/plugins.txt | sort)" \
    && installed="$(cd /usr/share/jenkins/ref/plugins && for plugin in *.jpi; do \
         printf '%s:%s\n' "${plugin%.jpi}" "$(unzip -p "$plugin" META-INF/MANIFEST.MF | tr -d '\r' | sed -n 's/^Plugin-Version: //p')"; \
       done | sort)" \
    && [ "$expected" = "$installed" ] \
    || { echo "Installed plugins do not match plugins.txt (name:version)" >&2; exit 1; }
