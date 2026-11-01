# Security Policy

## Supported versions

Only the latest release gets security fixes. If you can, check that the issue still happens on it before reporting.

## Reporting a vulnerability

Please do not open a public issue. Report it privately through [GitHub private vulnerability reporting](https://github.com/mhajder/librenms-mcp/security/advisories/new).

Include the affected version, how to reproduce it and what an attacker could do with it. Do not send real tokens or passwords; redact them.

I aim to acknowledge a report within 7 days and will keep you updated until it is fixed and released.

## Scope

In scope is this MCP server, for example:

- credentials or tokens leaking into logs, errors or tool output
- a write operation that still runs with `READ_ONLY_MODE=true`
- missing or bypassable authentication on the HTTP transports
- tool arguments that reach LibreNMS in a way they should not (path or query injection)

Vulnerabilities in LibreNMS itself belong with the LibreNMS project.
