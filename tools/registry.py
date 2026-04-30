    

import logging
from os import name
from typing import Any
from zipfile import Path
from tools.base import Tool, ToolInvokation ,ToolResult
from tools.builtin import ReadFileTool,get_all_builtin_tools

logger = logging.getLogger(__name__)

class ToolRegistery:
    def __init__(self):
        self._tools:dict[str,Tool] = {} 
    
    def register(self, tool:Tool):
        if tool.name in self._tools:
            logger.warning(f"Overwriting existing tool: {tool.name}")

        self._tools[tool.name] = tool
        logger.debug(f"Registered tool: {tool.name}")

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
        return tools
    
    def get(self, tool_name:str)->Tool | None:
        return self._tools.get(tool_name)

    async def invoke(self,name:str,params:dict[str,Any],cwd:str|None=None):
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
        
        invocation = ToolInvokation(
            params=params,
            cwd=cwd
        )
        try:
            result = await tool.execute(invocation)
            return result
        except Exception as e:
            logger.exception(f"Error executing tool {name}: {e}")
            return ToolResult.error_result(
                f"Error executing tool: {str(e)}",
                metadata={"tool_name": name},
            )
        

      
def create_default_registery()->ToolRegistery:
    registery = ToolRegistery()
    BUILTIN_TOOLS = [ReadFileTool]
    for tool_class in get_all_builtin_tools():
        registery.register(tool_class())
    return registery