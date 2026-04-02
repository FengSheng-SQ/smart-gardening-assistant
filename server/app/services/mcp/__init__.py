"""
MCP服务模块
提供MCP服务器和MCP Host功能
"""
from .weather_server import mcp, main
from .mcp_host import (
    MCPTool,
    MCPClient,
    MCPHost,
    get_mcp_host,
    initialize_mcp_servers,
    shutdown_mcp_servers
)

__all__ = [
    # FastMCP服务器实例和主函数
    "mcp",
    "main",

    # MCP Host相关
    "MCPTool",
    "MCPClient",
    "MCPHost",
    "get_mcp_host",
    "initialize_mcp_servers",
    "shutdown_mcp_servers",
]
