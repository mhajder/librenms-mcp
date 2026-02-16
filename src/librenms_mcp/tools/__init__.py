"""LibreNMS MCP Server Tools."""

from librenms_mcp.tools.alerts import register_alert_tools
from librenms_mcp.tools.bills import register_bill_tools
from librenms_mcp.tools.devices import register_device_tools
from librenms_mcp.tools.health import register_health_tools
from librenms_mcp.tools.inventory import register_inventory_tools
from librenms_mcp.tools.locations import register_location_tools
from librenms_mcp.tools.logs import register_logs_tools
from librenms_mcp.tools.network import register_network_tools
from librenms_mcp.tools.pollers import register_poller_tools
from librenms_mcp.tools.ports import register_port_tools
from librenms_mcp.tools.services import register_service_tools
from librenms_mcp.tools.system import register_system_tools


def register_tools(mcp, config):
    """Register all LibreNMS tools with the MCP server."""
    register_alert_tools(mcp, config)
    register_bill_tools(mcp, config)
    register_device_tools(mcp, config)
    register_health_tools(mcp, config)
    register_inventory_tools(mcp, config)
    register_location_tools(mcp, config)
    register_logs_tools(mcp, config)
    register_network_tools(mcp, config)
    register_poller_tools(mcp, config)
    register_port_tools(mcp, config)
    register_service_tools(mcp, config)
    register_system_tools(mcp, config)
