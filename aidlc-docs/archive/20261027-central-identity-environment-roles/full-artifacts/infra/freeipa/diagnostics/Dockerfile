FROM docker.io/freeipa/freeipa-server:almalinux-9-4.13.4@sha256:103c6a787f4de0a73fb9add04564ca5895fc5423c17e52fc134dfee3a3eca46d

# Preserve the pinned image's real NSS utility, then install a diagnostic shim
# that copies only the CA-agent PKCS#12 inputs into a container tmpfs and
# reports return codes/error identifiers without printing secrets.
RUN cp -p /usr/bin/pk12util /usr/bin/pk12util.real
COPY diagnostics/pk12util-diagnostic-wrapper /usr/bin/pk12util
COPY patch-ra-certificate-nss.py /usr/local/sbin/patch-ra-certificate-nss.py
RUN chmod 0755 /usr/bin/pk12util
RUN python3 /usr/local/sbin/patch-ra-certificate-nss.py
