


import os
from pathlib import Path

from pydantic import BaseModel, Field
import re
from tools.base import Tool, ToolInvocation, ToolKind, ToolKind, ToolResult
from utils.path import is_binary_file, resolve_path

class GlobParams(BaseModel):
    pattern: str = Field(..., description="Glob pattern to match")
    path: str = Field(
        ".", description="Directory to search in (default: current directory)"
    )
    case_insensitive: bool = Field(
        False,
        description="Case-insensitive search (default: false)",
    )


class GlobTool(Tool):
    name = "glob"
    kind = ToolKind.READ
    description = (
        "Find files matching a glob pattern. Supports ** for recursive matching."
    )    
    schema= GlobParams


    async def execute(self, invocation:ToolInvocation)->ToolResult:
        params= GlobParams(**invocation.params)

        search_path= resolve_path(invocation.cwd, params.path)

        if not search_path.exists() or not search_path.is_dir():
            return ToolResult.error_result(f"Path does not exist or is not a directory: {search_path}")
        
        try:
            matches= list(search_path.glob(params.pattern))
            matches= [m for m in matches if m.is_file()]
        except re.error as e:
            return ToolResult.error_result(f"Error searching: {e}")
        
        
        
        output_lines=[]
        # matches=0
        for file_path in matches[:1000]:
            try:
                rel_path= file_path.relative_to(invocation.cwd)

            except Exception:
                file_path= file_path


            output_lines.append(str(rel_path))
           
        if len(matches) > 1000:
            output_lines.append(f"...(limited to 1000 results)")
        return ToolResult.success_result(
            "\n".join(output_lines),
            metadata={
                "path": str(search_path),
                'matches': len(matches),
            },
        )
            





    
