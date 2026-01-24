# LibreNMS MCP Server

LibreNMS MCP Server is a Python-based Model Context Protocol (MCP) server designed to provide advanced, programmable access to LibreNMS network monitoring data and management features. It exposes a modern API for querying, automating, and integrating LibreNMS resources such as devices, ports, alerts, inventory, locations, logs, and more. The server supports both read and write operations, robust security features, and is suitable for integration with automation tools, dashboards, and custom network management workflows.

## Features

### Core Features

- Query LibreNMS devices, ports, inventory, locations, logs, and alerts with flexible filtering
- Retrieve network topology, device status, and performance metrics
- Access and analyze alert history, event logs, and system health
- Monitor interface statistics, port status, and traffic data
- Track endpoints and connected devices by MAC or IP address
- Retrieve and manage device groups, port groups, and poller groups
- Get detailed information about network services and routing

### Management Operations

- Create, update, and delete devices, ports, and groups (if enabled)
- Manage alert rules, notifications, and device metadata
- Configure read-only mode to restrict all write operations for safe monitoring
- Support for bulk operations on devices and ports

### Advanced Capabilities

- Rate limiting and API security features
- Real-time network monitoring and health tracking
- Comprehensive logging and audit trails
- SSL/TLS support and configurable timeouts
- Extensible with custom middlewares and utilities

## Installation

### Prerequisites

- Python 3.11 to 3.14
- Access to a LibreNMS
- Valid LibreNMS token with appropriate permissions

### Quick Install from PyPI

The easiest way to get started is to install from PyPI:

```sh
# Using UV (recommended)
uvx librenms-mcp

# Or using pip
pip install librenms-mcp
```

Remember to configure the environment variables for your LibreNMS instance before running the server:

```sh
# Create environment configuration
export LIBRENMS_URL=https://domain.tld:8443
export LIBRENMS_TOKEN=your-librenms-token
```

For more details, visit: https://pypi.org/project/librenms-mcp/

### Install from Source

1. Clone the repository:

```sh
git clone https://github.com/mhajder/librenms-mcp.git
cd librenms-mcp
```

2. Install dependencies:

```sh
# Using UV (recommended)
uv sync

# Or using pip
pip install -e .
```

3. Configure environment variables:

```sh
cp .env.example .env
# Edit .env with your LibreNMS url and token
```

4. Run the server:

```sh
# Using UV
uv run python run_server.py

# Or directly with Python
python run_server.py

# Or using the installed script
librenms-mcp
```

### Using Docker

A Docker images are available on GitHub Packages for easy deployment.

```sh
# Normal STDIO image
docker pull ghcr.io/mhajder/librenms-mcp:latest

# MCPO image for usage with Open WebUI
docker pull ghcr.io/mhajder/librenms-mcpo:latest
```

### Development Setup

For development with additional tools:

```sh
# Clone and install with development dependencies
git clone https://github.com/mhajder/librenms-mcp.git
cd librenms-mcp
uv sync --group dev

# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov=src/

# Run linting and formatting
uv run ruff check .
uv run ruff format .

# Setup pre-commit hooks
uv run pre-commit install
```

## Configuration

### Environment Variables

```env
# LibreNMS Connection Details
LIBRENMS_URL=https://domain.tld:8443
LIBRENMS_TOKEN=your-librenms-token

# SSL Configuration
LIBRENMS_VERIFY_SSL=true
LIBRENMS_TIMEOUT=30

# Read-Only Mode
# Set READ_ONLY_MODE true to disable all write operations (put, post, delete)
READ_ONLY_MODE=false

# Disabled Tags
# Comma-separated list of tags to disable tools for (empty by default)
# Example: DISABLED_TAGS=alert,bills
DISABLED_TAGS=

# Logging Configuration
LOG_LEVEL=INFO

# Rate Limiting (requests per minute)
# Set RATE_LIMIT_ENABLED true to enable rate limiting
RATE_LIMIT_ENABLED=false
RATE_LIMIT_MAX_REQUESTS=100
RATE_LIMIT_WINDOW_MINUTES=1

# Sentry Error Tracking (Optional)
# Set SENTRY_DSN to enable error tracking and performance monitoring
# SENTRY_DSN=https://your-key@o12345.ingest.us.sentry.io/6789
# Optional Sentry configuration
# SENTRY_TRACES_SAMPLE_RATE=1.0
# SENTRY_SEND_DEFAULT_PII=true
# SENTRY_ENVIRONMENT=production
# SENTRY_RELEASE=1.2.3
# SENTRY_PROFILE_SESSION_SAMPLE_RATE=1.0
# SENTRY_PROFILE_LIFECYCLE=trace
# SENTRY_ENABLE_LOGS=true

# MCP Transport Configuration
# Transport type: 'stdio' (default), 'sse' (Server-Sent Events), or 'http' (HTTP Streamable)
MCP_TRANSPORT=stdio

# HTTP Transport Settings (used when MCP_TRANSPORT=sse or MCP_TRANSPORT=http)
# Host to bind the HTTP server (default: 0.0.0.0 for all interfaces)
MCP_HTTP_HOST=0.0.0.0
# Port to bind the HTTP server (default: 8000)
MCP_HTTP_PORT=8000
# Optional bearer token for authentication (leave empty for no auth)
MCP_HTTP_BEARER_TOKEN=
```

## Available Tools

### Device & Inventory Tools

- `devices_list`: List all devices (with optional filters)
- `device_get`: Get details for a specific device
- `device_add`: Add a new device
- `device_update`: Update device metadata
- `device_delete`: Remove a device
- `device_ports`: List all ports for a device
- `device_ports_get`: Get details for a specific port on a device
- `device_availability`: Get device availability
- `device_outages`: Get device outages
- `device_set_maintenance`: Set device maintenance mode
- `inventory_device`: Get inventory for a device
- `inventory_device_flat`: Get flat inventory for a device
- `devicegroups_list`: List device groups
- `devicegroup_add`: Add a device group
- `devicegroup_update`: Update a device group
- `devicegroup_delete`: Delete a device group
- `devicegroup_devices`: List devices in a device group
- `devicegroup_set_maintenance`: Set maintenance for a device group
- `devicegroup_add_devices`: Add devices to a device group
- `devicegroup_remove_devices`: Remove devices from a device group
- `locations_list`: List all locations
- `location_add`: Add a location
- `location_edit`: Edit a location
- `location_delete`: Delete a location
- `location_get`: Get details for a location

### Port & Port Group Tools

- `ports_list`: List all ports (with optional filters)
- `port_groups_list`: List port groups
- `port_group_add`: Add a port group
- `port_group_list_ports`: List ports in a port group
- `port_group_assign`: Assign ports to a port group
- `port_group_remove`: Remove ports from a port group

### Alerting & Logging Tools

- `alerts_get`: List current and historical alerts
- `alert_get_by_id`: Get details for a specific alert
- `alert_acknowledge`: Acknowledge an alert
- `alert_unmute`: Unmute an alert
- `alert_rules_list`: List alert rules
- `alert_rule_get`: Get details for a specific alert rule
- `alert_rule_add`: Add an alert rule
- `alert_rule_edit`: Edit an alert rule
- `alert_rule_delete`: Delete an alert rule
- `logs_eventlog`: Get event log for a device
- `logs_syslog`: Get syslog for a device
- `logs_alertlog`: Get alert log for a device
- `logs_authlog`: Get auth log for a device
- `logs_syslogsink`: Add a syslog sink

### Billing Tools

- `bills_list`: List bills
- `bill_get`: Get details for a bill
- `bill_graph`: Get bill graph
- `bill_graph_data`: Get bill graph data
- `bill_history`: Get bill history
- `bill_history_graph`: Get bill history graph
- `bill_history_graph_data`: Get bill history graph data
- `bill_create_or_update`: Create or update a bill
- `bill_delete`: Delete a bill

### Network & Monitoring Tools

- `arp_search`: Search ARP entries
- `poller_group_get`: Get poller group(s)
- `routing_ip_addresses`: List all IP addresses from LibreNMS.
- `services_list`: List all services from LibreNMS.
- `services_for_device`: Get services for a device from LibreNMS.
- `switching_vlans`: List all VLANs from LibreNMS.
- `switching_links`: List all links from LibreNMS.
- `system_info`: Get system info from LibreNMS.

### General Query Tools

- Flexible filtering and search for all major resources (devices, ports, alerts, logs, inventory, etc.)

## Security & Safety Features

### Read-Only Mode

The server supports a read-only mode that disables all write operations for safe monitoring:

```env
READ_ONLY_MODE=true
```

### Tag-Based Tool Filtering

You can disable specific categories of tools by setting disabled tags:

```env
DISABLED_TAGS=alert,bills
```

### Rate Limiting

The server supports rate limiting to control API usage and prevent abuse. If enabled, requests are limited per client using a sliding window algorithm.

Enable rate limiting by setting the following environment variables in your `.env` file:

```env
RATE_LIMIT_ENABLED=true
RATE_LIMIT_MAX_REQUESTS=100   # Maximum requests allowed per window
RATE_LIMIT_WINDOW_MINUTES=1   # Window size in minutes
```

If `RATE_LIMIT_ENABLED` is set to `true`, the server will apply rate limiting middleware. Adjust `RATE_LIMIT_MAX_REQUESTS` and `RATE_LIMIT_WINDOW_MINUTES` as needed for your environment.

### Sentry Error Tracking & Monitoring (Optional)

The server optionally supports **Sentry** for error tracking, performance monitoring, and debugging. Sentry integration is completely optional and only initialized if configured.

#### Installation

To enable Sentry monitoring, install the optional dependency:

```sh
# Using UV (recommended)
uv sync --extra sentry
```

#### Configuration

Enable Sentry by setting the `SENTRY_DSN` environment variable in your `.env` file:

```env
# Required: Sentry DSN for your project
SENTRY_DSN=https://your-key@o12345.ingest.us.sentry.io/6789

# Optional: Performance monitoring sample rate (0.0-1.0, default: 1.0)
SENTRY_TRACES_SAMPLE_RATE=1.0

# Optional: Include personally identifiable information (default: true)
SENTRY_SEND_DEFAULT_PII=true

# Optional: Environment name (e.g., "production", "staging")
SENTRY_ENVIRONMENT=production

# Optional: Release version (auto-detected from package if not set)
SENTRY_RELEASE=1.2.2

# Optional: Profiling - continuous profiling sample rate (0.0-1.0, default: 1.0)
SENTRY_PROFILE_SESSION_SAMPLE_RATE=1.0

# Optional: Profiling - lifecycle mode for profiling (default: "trace")
# Options: "all", "continuation", "trace"
SENTRY_PROFILE_LIFECYCLE=trace

# Optional: Enable log capture as breadcrumbs and events (default: true)
SENTRY_ENABLE_LOGS=true
```

#### Features

When enabled, Sentry automatically captures:

- **Exceptions & Errors**: All unhandled exceptions with full context
- **Performance Metrics**: Request/response times and traces
- **MCP Integration**: Detailed MCP server activity and interactions
- **Logs & Breadcrumbs**: Application logs and event trails for debugging
- **Context Data**: Environment, client info, and request parameters

#### Getting a Sentry DSN

1. Create a free account at [sentry.io](https://sentry.io)
2. Create a new Python project
3. Copy your DSN from the project settings
4. Set it in your `.env` file

#### Disabling Sentry

Sentry is completely optional. If you don't set `SENTRY_DSN`, the server will run normally without any Sentry integration, and no monitoring data will be collected.

### SSL/TLS Configuration

The server supports SSL certificate verification and custom timeout settings:

```env
LIBRENMS_VERIFY_SSL=true    # Enable SSL certificate verification
LIBRENMS_TIMEOUT=30         # Connection timeout in seconds
```

### Transport Configuration

The server supports multiple transport mechanisms for the MCP protocol:

#### STDIO Transport (Default)

The default transport uses standard input/output for communication. This is ideal for local usage and integration with tools that communicate via stdin/stdout:

```env
MCP_TRANSPORT=stdio
```

#### HTTP SSE Transport (Server-Sent Events)

For network-based deployments, you can use HTTP with Server-Sent Events. This allows the MCP server to be accessed over HTTP with real-time streaming:

```env
MCP_TRANSPORT=sse
MCP_HTTP_HOST=0.0.0.0        # Bind to all interfaces (or specific IP)
MCP_HTTP_PORT=8000           # Port to listen on
MCP_HTTP_BEARER_TOKEN=your-secret-token  # Optional authentication token
```

When using SSE transport with a bearer token, clients must include the token in their requests:

```bash
curl -H "Authorization: Bearer your-secret-token" http://localhost:8000/sse
```

#### HTTP Streamable Transport

The HTTP Streamable transport provides HTTP-based communication with request/response streaming. This is ideal for web integrations and tools that need HTTP endpoints:

```env
MCP_TRANSPORT=http
MCP_HTTP_HOST=0.0.0.0        # Bind to all interfaces (or specific IP)
MCP_HTTP_PORT=8000           # Port to listen on
MCP_HTTP_BEARER_TOKEN=your-secret-token  # Optional authentication token
```

When using streamable transport with a bearer token:

```sh
curl -H "Authorization: Bearer your-secret-token" \
     -H "Accept: application/json, text/event-stream" \
     -H "Content-Type: application/json" \
     -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' \
     http://localhost:8000/mcp
```

**Note**: The HTTP transport requires proper JSON-RPC formatting with `jsonrpc` and `id` fields. The server may also require session initialization for some operations.

For more information on FastMCP transports, see the [FastMCP documentation](https://gofastmcp.com/deployment/running-server#transport-protocols).

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and ensure code quality (`uv run pytest && uv run ruff check .`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## License

MIT License - see LICENSE file for details.
