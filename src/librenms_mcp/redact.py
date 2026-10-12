"""
Redact SNMP credentials from LibreNMS API responses.

LibreNMS returns the full device row from every device endpoint (get, list,
search), including the SNMP community and SNMPv3 username and passphrases in
plain text. None of the tools need them, and anything a tool returns ends up
in an AI client's context, chat history and traces, so they are replaced as
soon as a response is decoded (LibreNMSClient.request). Unset values stay as
they are, so a caller can still see whether a credential is configured; the
SNMP version and algorithms are left visible for troubleshooting.
"""

from typing import Any

CREDENTIAL_KEYS = frozenset({"community", "authname", "authpass", "cryptopass"})
REDACTED = "<redacted>"


def redact_credentials(body: Any) -> Any:
    """Return body with every non-empty credential value replaced, at any depth."""
    if isinstance(body, dict):
        return {
            key: REDACTED
            if key in CREDENTIAL_KEYS and value not in (None, "")
            else redact_credentials(value)
            for key, value in body.items()
        }
    if isinstance(body, list):
        return [redact_credentials(item) for item in body]
    return body
