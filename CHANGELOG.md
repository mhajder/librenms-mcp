# Changelog

## [1.7.0](https://github.com/mhajder/librenms-mcp/compare/v1.6.0...v1.7.0) (2026-02-18)


### 🚀 Features

* add 'ty' typechecker and resolve typing issues ([#30](https://github.com/mhajder/librenms-mcp/issues/30)) ([9d894d4](https://github.com/mhajder/librenms-mcp/commit/9d894d495047d63b304b8d22d22504626c35f001))
* add alert template management tools ([#13](https://github.com/mhajder/librenms-mcp/issues/13)) ([0aa6ed2](https://github.com/mhajder/librenms-mcp/commit/0aa6ed2d018e1fc1abf244477650bd2c888d13f7))
* add global-read/admin tags to tools ([#28](https://github.com/mhajder/librenms-mcp/issues/28)) ([47bcf84](https://github.com/mhajder/librenms-mcp/commit/47bcf84c7d7bb9b6d0e1699b1329bd6902462588))
* adds env vars in server.json ([#34](https://github.com/mhajder/librenms-mcp/issues/34)) ([90c0a4f](https://github.com/mhajder/librenms-mcp/commit/90c0a4f723fd2323ac198612a56f6ec5de3e444a))
* improves API request handling and endpoints ([#27](https://github.com/mhajder/librenms-mcp/issues/27)) ([56090d6](https://github.com/mhajder/librenms-mcp/commit/56090d69d0ff4cc24a7b1d589a66ddc67158aa3b))
* refactors CI to isolate MCP Registry publishing ([#16](https://github.com/mhajder/librenms-mcp/issues/16)) ([7e81a63](https://github.com/mhajder/librenms-mcp/commit/7e81a6325912b0e80318031c9f225179f3911a78))


### 🐛 Bug Fixes

* transform device_update payload to LibreNMS API field/data format ([#19](https://github.com/mhajder/librenms-mcp/issues/19)) ([d0a602f](https://github.com/mhajder/librenms-mcp/commit/d0a602f9080681478130168286a419a6fd760508))
* update healthcheck command to use nc for service availability ([#21](https://github.com/mhajder/librenms-mcp/issues/21)) ([0718374](https://github.com/mhajder/librenms-mcp/commit/0718374df1ad8a7c3cff854b495ad309ed8d0ce4))
* use GET instead of POST for device_discover endpoint ([#14](https://github.com/mhajder/librenms-mcp/issues/14)) ([14338b2](https://github.com/mhajder/librenms-mcp/commit/14338b200b619888bc57bc923700d863d835878b))


### 🧹 Refactoring

* **tools:** split monolithic tools into modules ([#32](https://github.com/mhajder/librenms-mcp/issues/32)) ([d108518](https://github.com/mhajder/librenms-mcp/commit/d108518f810232bd038beafa7bec588d2c6243d1))


### 📚 Documentation

* add missing tools ([#18](https://github.com/mhajder/librenms-mcp/issues/18)) ([7bc6ece](https://github.com/mhajder/librenms-mcp/commit/7bc6ece8a800b4836c5199fe88e1f287829aa8c2))
* Updates README dev commands ([#31](https://github.com/mhajder/librenms-mcp/issues/31)) ([8d4b28f](https://github.com/mhajder/librenms-mcp/commit/8d4b28fea68676c7dcf7506f2bac8b797955de9e))

## [1.6.0](https://github.com/mhajder/librenms-mcp/compare/v1.5.0...v1.6.0) (2026-02-04)


### 🚀 Features

* add MCP Registry integration and metadata ([4a04ea7](https://github.com/mhajder/librenms-mcp/commit/4a04ea7252fcfe9f6f418f7373fd553beee56bb0))
* add MCP transport configuration and support for multiple transport types ([81e0cbb](https://github.com/mhajder/librenms-mcp/commit/81e0cbba83e560c2a6a61ce63207e086d49581fc))
* add Python 3.14 support ([2fe5342](https://github.com/mhajder/librenms-mcp/commit/2fe5342dd03a80699ce5efa43597c460af3a34c7))
* add sensor and health management tools ([#7](https://github.com/mhajder/librenms-mcp/issues/7)) ([6c8da99](https://github.com/mhajder/librenms-mcp/commit/6c8da9916b501857e359d30f629c8b77a7df15b8))
* add snmp_disable support to device_update tool ([#8](https://github.com/mhajder/librenms-mcp/issues/8)) ([529d644](https://github.com/mhajder/librenms-mcp/commit/529d644e1a99448512252b3a14d47a151109b76e))
* add support for disabling tools via tags ([4ff53af](https://github.com/mhajder/librenms-mcp/commit/4ff53af4e980fe038d47ea4b3bbcbe3ef8dd3b12))
* **dependencies:** add fastmcp and sentry-sdk to fastmcp.json dependencies ([3bd6f8b](https://github.com/mhajder/librenms-mcp/commit/3bd6f8ba4fcecf3478fab35fcaede19850735296))
* **deps:** add commitizen for conventional commits ([65dfbbb](https://github.com/mhajder/librenms-mcp/commit/65dfbbbae46aef4b42abdfb9c23e5c1c5912012f))
* **docker:** change MCP image to http transport as default ([2c6aae8](https://github.com/mhajder/librenms-mcp/commit/2c6aae8402063a067024f845275f39a144aa7466))
* improve tool descriptions and add missing API endpoints ([#1](https://github.com/mhajder/librenms-mcp/issues/1)) ([d9b143a](https://github.com/mhajder/librenms-mcp/commit/d9b143a6638c9b2bf10df65e3549984ea74a9768))
* **pre-commit:** add commitizen hooks for conventional commits ([f4d5d9b](https://github.com/mhajder/librenms-mcp/commit/f4d5d9b7c83a5ad4cd384cf41267934a3631441f))
* **publish:** add workflow for publishing to PyPI and configuration ([a3e956f](https://github.com/mhajder/librenms-mcp/commit/a3e956f947a0deabf4e45a9df84083d2281933d7))
* **sentry:** add optional Sentry integration for error tracking and performance monitoring ([dfe9c79](https://github.com/mhajder/librenms-mcp/commit/dfe9c79d85f3906fd6d5327469b5d75c4abf6935))


### 🐛 Bug Fixes

* **docker:** improve healthcheck configuration ([e748e0e](https://github.com/mhajder/librenms-mcp/commit/e748e0e6da09d66e57857074272e516a0a050977))
* **docker:** update base image to alpine3.23 and improve uv installation commands ([0d26397](https://github.com/mhajder/librenms-mcp/commit/0d26397e14cd164f6e893a7b43598d232f6f5cca))
* **docker:** update uv sync command to include all extras ([81583d0](https://github.com/mhajder/librenms-mcp/commit/81583d040b7b0b27177585908fa967d2d1f49e42))
* **publish:** change trigger from release types to push tags for PyPI publishing ([3c3e16d](https://github.com/mhajder/librenms-mcp/commit/3c3e16dd31f2370f0888cda0d42d899d46a703a5))
* **publish:** update release types to include 'created' ([f1e649c](https://github.com/mhajder/librenms-mcp/commit/f1e649cf17877277b0541e13dc82885bde4229f2))
* use rule_id instead of id in alert_rule_edit tool ([#6](https://github.com/mhajder/librenms-mcp/issues/6)) ([d6d29f3](https://github.com/mhajder/librenms-mcp/commit/d6d29f3ff1f412847480f65f49c5d97c46146580))


### 📚 Documentation

* update installation instructions ([d0797cc](https://github.com/mhajder/librenms-mcp/commit/d0797ccf203075ef676487e108fdea13617425a7))
* update Python version requirements and add Docker images information ([10cbac4](https://github.com/mhajder/librenms-mcp/commit/10cbac4453e547ca04553674788015602b3ec2dc))


### 🧩 CI

* migrate to release-please and improve workflows ([#10](https://github.com/mhajder/librenms-mcp/issues/10)) ([88f1a90](https://github.com/mhajder/librenms-mcp/commit/88f1a902810561c24d82f1eed646dc17d19dfe0c))

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
