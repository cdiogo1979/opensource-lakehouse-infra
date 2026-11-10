FROM docker.io/freeipa/freeipa-server:almalinux-9-4.13.4@sha256:103c6a787f4de0a73fb9add04564ca5895fc5423c17e52fc134dfee3a3eca46d

COPY patch-ra-certificate-nss.py /usr/local/sbin/patch-ra-certificate-nss.py
RUN python3 /usr/local/sbin/patch-ra-certificate-nss.py

COPY patch-volatile-journal.py /usr/local/sbin/patch-volatile-journal.py
RUN python3 /usr/local/sbin/patch-volatile-journal.py
