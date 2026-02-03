# Changelog

## v1.5.0 (2026-01-25)

### Feat

- add MCP Registry integration and metadata
- improve tool descriptions and add missing API endpoints (#1)
- add Python 3.14 support

### Fix

- **docker**: improve healthcheck configuration

## v1.4.0 (2025-12-22)

### Feat

- add support for disabling tools via tags

## v1.3.0 (2025-12-21)

### Feat

- **dependencies**: add fastmcp and sentry-sdk to fastmcp.json dependencies
- **docker**: change MCP image to http transport as default
- **sentry**: add optional Sentry integration for error tracking and performance monitoring

### Fix

- **docker**: update uv sync command to include all extras

## v1.2.2 (2025-12-18)

### Fix

- **publish**: change trigger from release types to push tags for PyPI publishing

## v1.2.1 (2025-12-18)

### Fix

- **publish**: update release types to include 'created'

## v1.2.0 (2025-12-18)

### Feat

- **publish**: add workflow for publishing to PyPI and configuration
- **pre-commit**: add commitizen hooks for conventional commits
- **deps**: add commitizen for conventional commits

### Fix

- **docker**: update base image to alpine3.23 and improve uv installation commands

## v1.1.0 (2025-10-18)

### Feat

- add MCP transport configuration and support for multiple transport types

## v1.0.1 (2025-10-18)

## v1.0.0 (2025-08-09)
