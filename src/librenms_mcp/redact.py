"""
Redact SNMP credentials from LibreNMS API responses.

LibreNMS returns the full device row from every device endpoint (get, list,
search), including the SNMP community and SNMPv3 username and passphrases in
plain text, and a check_snmp service keeps the community or SNMPv3
credentials in its ``service_param`` arguments. None of the tools need them,
and anything a tool returns ends up in an AI client's context, chat history
and traces, so they are replaced as soon as a response is decoded
(LibreNMSClient.request), unless REDACT_SNMP_CREDENTIALS is false. Error
messages that quote a raw response body are scrubbed too (redact_text).

Only device records and snmp services are touched: a ``community`` key
elsewhere (a BGP community, say) is not a credential and is left as is.
Unset values stay as they are, so a caller can still see whether a credential
is configured; the SNMP version and algorithms are left visible for
troubleshooting. Credentials of other service types (check_mysql's password,
for instance) are not redacted.
"""

import re
from typing import Any

CREDENTIAL_KEYS = ("community", "authname", "authpass", "cryptopass")
REDACTED = "<redacted>"

# check_snmp's community (-C), SNMPv3 username (-U) and passphrases (-A, -X),
# short or long, with the value attached, after a space or after "=".
_SNMP_ARG = re.compile(
    r"(?<!\S)(-[CUAX]\s*|--(?:community|secname|authpasswd|privpasswd)(?:=|\s+))"
    r"""("[^"]*"|'[^']*'|\S+)"""
)
# A credential key/value pair in raw JSON text. The closing quote is optional:
# a proxy can cut the body short inside the value.
_JSON_CREDENTIAL = re.compile(
    r'("(?:' + "|".join(CREDENTIAL_KEYS) + r')"\s*:\s*)"(?:[^"\\]|\\.)*(?:"|$)'
)


def _is_device(obj: dict[str, Any]) -> bool:
    return "device_id" in obj and ("hostname" in obj or "snmpver" in obj)


def _is_snmp_service(obj: dict[str, Any]) -> bool:
    return obj.get("service_type") == "snmp" and isinstance(
        obj.get("service_param"), str
    )


def redact_credentials(body: Any) -> Any:
    """Replace set credentials in device records and snmp services, in place.

    The body is a freshly decoded response that nothing else holds, so it is
    changed rather than copied: some responses (ports, FDB, logs) have tens of
    thousands of rows.

    Returns:
        The same body, for convenience.
    """
    stack = [body]
    while stack:
        node = stack.pop()
        if isinstance(node, list):
            stack.extend(node)
            continue
        if not isinstance(node, dict):
            continue
        if _is_device(node):
            for key in CREDENTIAL_KEYS:
                if node.get(key) not in (None, ""):
                    node[key] = REDACTED
        if _is_snmp_service(node):
            node["service_param"] = _SNMP_ARG.sub(
                rf"\g<1>{REDACTED}", node["service_param"]
            )
        stack.extend(v for v in node.values() if isinstance(v, (dict, list)))
    return body


def redact_text(text: str) -> str:
    """Scrub credential values from raw response text quoted in an error message.

    Used when a body cannot be decoded (a PHP notice before the JSON, a body
    cut short) or has no message, so its text is quoted instead. Call it
    before truncating, so a value cut in half is still recognised.
    """
    return _JSON_CREDENTIAL.sub(rf'\g<1>"{REDACTED}"', text)
