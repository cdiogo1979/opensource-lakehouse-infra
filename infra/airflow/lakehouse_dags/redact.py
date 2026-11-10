"""Redact credentials from Spark output before it reaches task logs (ported from the workload repository)."""

import re

_JWT_RE = re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")
_SENSITIVE_VALUE_RE = re.compile(r"(?i)\b(authorization|access[_ -]?token|refresh[_ -]?token|token|client[_ -]?secret|password|secret|credential)\b" r"([\"']?\s*[:=]\s*[\"']?)([^\s,;\"'}]+)")


def redact_spark_output(output: bytes | str) -> str:
    """Keep useful Spark failure context while removing common credential forms."""
    text = output.decode("utf-8", errors="replace") if isinstance(output, bytes) else output
    text = re.sub(r"(?i)(bearer\s+)[A-Za-z0-9._~+/-]+=*", r"\1<redacted>", text)
    text = _SENSITIVE_VALUE_RE.sub(r"\1\2<redacted>", text)
    text = _JWT_RE.sub("<redacted-jwt>", text)
    text = re.sub(r"\b[A-Za-z0-9_-]{48,}\b", "<redacted-value>", text)
    return text[-20000:]
