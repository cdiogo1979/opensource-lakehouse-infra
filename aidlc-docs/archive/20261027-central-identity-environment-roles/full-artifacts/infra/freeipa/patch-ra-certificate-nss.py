#!/usr/bin/env python3
"""Use Dogtag's NSS client authentication for FreeIPA's bootstrap RA cert."""

from pathlib import Path


source = Path("/usr/lib/python3.9/site-packages/ipaserver/install/certs.py")
text = source.read_text()

import_start_marker = "    def import_pkcs12(self, pkcs12_fname, pkcs12_passwd=None):"
import_end_marker = "    def export_pkcs12("
import_start = text.index(import_start_marker)
import_end = text.index(import_end_marker, import_start)
import_replacement = '''    def import_pkcs12(self, pkcs12_fname, pkcs12_passwd=None):
        """Import PKCS#12, falling back to Dogtag's JSS importer."""
        try:
            return self.nssdb.import_pkcs12(
                pkcs12_fname, pkcs12_passwd=pkcs12_passwd
            )
        except Exception as import_error:
            password_file = ipautil.write_tmp_file(pkcs12_passwd or "")
            try:
                return ipautil.run(
                    [
                        "/usr/bin/pki",
                        "-d", self.secdir,
                        "-C", self.passwd_fname,
                        "pkcs12-import",
                        "--pkcs12", pkcs12_fname,
                        "--password-file", password_file.name,
                        "--no-trust-flags",
                    ],
                    capture_output=True,
                )
            except Exception:
                raise import_error

'''
text = text[:import_start] + import_replacement + text[import_end:]

start_marker = "    def pki_issue_ra_certificate(self, csrfile, certfile, dm_password):"
end_marker = "    def pki_issue_certificate("
start = text.index(start_marker)
end = text.index(end_marker, start)

replacement = '''    def pki_issue_ra_certificate(self, csrfile, certfile, dm_password):
        """Issue the IPA RA certificate using the imported NSS agent key.

        The PKCS#12 bundle produced by Dogtag can be imported into NSS by
        JSS, but OpenSSL cannot decrypt its private key on this platform.
        Use Dogtag's CLI with NSS client-certificate authentication so the
        private key remains inside the NSS database.
        """
        import re

        def run_pki(*arguments):
            return ipautil.run(
                [
                    "/usr/bin/pki",
                    "-U", "https://{}:8443".format(api.env.host),
                    "-d", self.secdir,
                    "-C", self.passwd_fname,
                    "-n", "ipa-ca-agent",
                    "--skip-revocation-check",
                    *arguments,
                ],
                capture_output=True,
            ).output

        output = run_pki(
            "ca-cert-request-submit",
            "--profile", constants.RA_AGENT_PROFILE,
            "--csr-file", csrfile,
        )
        match = re.search(r"^\\s*Request ID:\\s*(\\S+)", output, re.MULTILINE)
        if not match:
            raise RuntimeError("Dogtag did not return a certificate request ID")
        request_id = match.group(1)

        output = run_pki("ca-cert-request-show", request_id)
        status_match = re.search(
            r"^\\s*Request Status:\\s*(\\S+)", output,
            re.MULTILINE | re.IGNORECASE,
        )
        if status_match and status_match.group(1).lower() == "pending":
            run_pki(
                "ca-cert-request-review", request_id,
                "--action", "approve",
            )
            output = run_pki("ca-cert-request-show", request_id)
            status_match = re.search(
                r"^\\s*Request Status:\\s*(\\S+)", output,
                re.MULTILINE | re.IGNORECASE,
            )
        if not status_match or status_match.group(1).lower() != "complete":
            status = status_match.group(1) if status_match else "unknown"
            raise RuntimeError(
                "The IPA RA certificate request did not complete "
                "(status: {})".format(status)
            )
        if not re.search(
                r"^\\s*Operation Result:\\s*success\\s*$", output,
                re.MULTILINE | re.IGNORECASE):
            raise RuntimeError("The IPA RA certificate request was unsuccessful")
        match = re.search(r"^\\s*Certificate ID:\\s*(\\S+)", output,
                          re.MULTILINE)
        if not match:
            raise RuntimeError("Dogtag did not return the issued certificate ID")

        run_pki(
            "ca-cert-export", match.group(1),
            "--output-file", certfile,
            "--output-format", "pem",
        )
        if not os.path.isfile(certfile) or os.path.getsize(certfile) == 0:
            raise RuntimeError("Dogtag did not export the IPA RA certificate")

'''

source.write_text(text[:start] + replacement + text[end:])
