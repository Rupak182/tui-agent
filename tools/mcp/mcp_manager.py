
import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)

from config.config import Config
from tools import registry
from tools.mcp.client import MCPClient, MCPServerStatus
from tools.mcp.mcp_tool import MCPTool
from tools.registry import ToolRegistry


class MCPManager:
    def __init__(self, config: Config):
        self.config = config
        
        self._clients:dict[str,MCPClient]={}
        self._initalized= False

    async def initialize(self)->None:
        if self._initalized:
            return
        
        mcp_configs= self.config.mcp_servers

        if not mcp_configs:
            return
        
        for name, server_config in mcp_configs.items():
            if not server_config:
                continue
            client= MCPClient(name=name,config=server_config,cwd=self.config.cwd)
            self._clients[name]= client

        connection_tasks = [
            asyncio.wait_for(
                client.connect(),
                timeout=client.config.startup_timeout_sec,
            )
            for name, client in self._clients.items()
        ]
        results = await asyncio.gather(*connection_tasks, return_exceptions=True)
        for name, result in zip(self._clients, results):
            if isinstance(result, Exception):
                logger.error(f"MCP server '{name}' failed: {result}", exc_info=result)

        self._initalized= True

    def register_tools(self,tool_registry:ToolRegistry)->None:
        count= 0
        for client in self._clients.values():
            print(f"Registering tools from MCP server: {client.name} with status {client.status}")
            if client.status != MCPServerStatus.CONNECTED:
                continue
            for tool_info in client.tools:
                mcp_tool = MCPTool(
                    tool_info=tool_info,
                    client=client,
                    config=self.config,
                    name=f"{client.name}__{tool_info.name}",
                )
                tool_registry.register_mcp_tool(mcp_tool)
                count += 1

        
        
    def get_all_servers(self)->list[dict[str,Any]]:
            servers=[]
            for name, client in self._clients.items():
                server_info={
                    "name": name,
                    "status": client.status.value,
                    "tools": len(client.tools)
                }
                servers.append(server_info)
            return servers
    
    async def shutdown(self) -> None:
        disconnection_tasks = [client.disconnect() for client in self._clients.values()]

        await asyncio.gather(*disconnection_tasks, return_exceptions=True)

        self._clients.clear()
        self._initialized = False