    

import logging
from typing import Any
from zipfile import Path
from tools.base import Tool, ToolInvocation ,ToolResult
from tools.builtin import ReadFileTool,get_all_builtin_tools
from tools.subagents import SubAgentTool, SubAgentTool, get_default_subagent_definitions
from config.config import Config
from safety.approval import ApprovalManager, ApprovalContext,ApprovalDecision
logger = logging.getLogger(__name__)

class ToolRegistry:
    def __init__(self,config:Config):
        self.config = config
        self._tools:dict[str,Tool] = {} 
        self._mcp_tools: dict[str,Tool] = {} 
        
    
    def register(self, tool:Tool):
        if tool.name in self._tools:
            logger.warning(f"Overwriting existing tool: {tool.name}")

        self._tools[tool.name] = tool
        logger.debug(f"Registered tool: {tool.name}")

    def register_mcp_tool(self, tool:Tool):
        if tool.name in self._mcp_tools:
            logger.warning(f"Overwriting existing MCP tool: {tool.name}")

        self._mcp_tools[tool.name] = tool
        logger.debug(f"Registered MCP tool: {tool.name}")

    def unregister(self, tool_name:str):
        if tool_name in self._tools:
            del self._tools[tool_name]
            return True 
        else:
            return False
        
    def get_schemas(self)->list[dict[str,Any]]:
        return [tool.to_openai_schema() for tool in self.get_tools()]

    def get_tools(self)->list[Tool]:
        tools: list[Tool] = []
        for tool in self._tools.values():
            tools.append(tool)
        for tool in self._mcp_tools.values():
            tools.append(tool)

        if self.config.allowed_tools:
            allowed_set=set(self.config.allowed_tools)
            tools = [tool for tool in tools if tool.name in allowed_set]
        return tools
    
    def get(self, tool_name:str)->Tool | None:
        if tool_name in self._tools:
            return self._tools[tool_name]
        elif tool_name in self._mcp_tools:
            return self._mcp_tools[tool_name]
        return None

    async def invoke(self,name:str,params:dict[str,Any],cwd:Path,approval_manager:ApprovalManager|None= None)->ToolResult:
        tool = self.get(name)
        if tool is None:    
            result = ToolResult.error_result(
                f"Unknown tool: {name}",
                metadata={"tool_name": name},
            )        

            return result
    
        validation_errors= tool.validate_params(params)

        if validation_errors:
            result = ToolResult.error_result(
                f"Invalid parameters: {'; '.join(validation_errors)}",
                metadata={
                    "tool_name": name,
                    "validation_errors": validation_errors,
                },
            )
            return result
        
        invocation = ToolInvocation(
            params=params,
            cwd=cwd
        )
        if approval_manager:
            confirmation=tool.get_confirmation(invocation)
            if confirmation:
                context=ApprovalContext(
                    tool_name=tool.name,
                    params=params,
                    is_mutating=tool.is_mutating(params),
                    affected_paths=confirmation.affected_paths ,
                    command=confirmation.command ,
                    is_dangerous=confirmation.is_dangerous   
                )

                decision = await approval_manager.check_approval(context)
                if decision ==ApprovalDecision.REJECTED:
                    return ToolResult.error_result(
                            "Operation rejected by safety policy"
                    )
                
                if decision == ApprovalDecision.NEEDS_CONFIRMATION:
                    approved= await approval_manager.request_confirmation(confirmation)

                    if not approved:
                        return ToolResult.error_result("User rejected the operation")
                        
        try:

            result = await tool.execute(invocation)
            return result
        except Exception as e:
            logger.exception(f"Error executing tool {name}: {e}")
            return ToolResult.error_result(
                f"Error executing tool: {str(e)}",
                metadata={"tool_name": name},
            )
        

      
def create_default_registry(config:Config)->ToolRegistry:
    registry = ToolRegistry(config=config)
    BUILTIN_TOOLS = [ReadFileTool]
    for tool_class in get_all_builtin_tools():
        registry.register(tool_class(config=config))

    for subagent_def in get_default_subagent_definitions():
        registry.register(SubAgentTool(config=config, definition=subagent_def))

    return registry