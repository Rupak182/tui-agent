


import uuid

from ddgs import DDGS
from pydantic import BaseModel, Field
from config.config import Config
from tools.base import Tool, ToolInvocation, ToolKind, ToolKind, ToolResult
from utils.path import is_binary_file, resolve_path

class TodosParams(BaseModel):
    action: str = Field(..., description="Action: 'add', 'complete', 'list', 'clear'")
    id: str | None = Field(None, description="Todo ID (for complete)")
    content: str | None = Field(None, description="Todo content (for add)")


class TodosTool(Tool):
    name = "todos"
    kind = ToolKind.MEMORY
    description = "Manage a task list for the current session. Use this to track progress on multi-step tasks."
    schema= TodosParams


    def __init__(self,config:Config):
        super().__init__(config=config)
        self._todos:dict[str,str] = {}

    async def execute(self, invocation:ToolInvocation)->ToolResult:
        params= TodosParams(**invocation.params)

        if params.action.lower()=="add":
            if not params.content:
                return ToolResult.error_result("'content' is required for 'add' action")
            
            todo_id=str(uuid.uuid4())[:8]
            self._todos[todo_id]=params.content
            return ToolResult.success_result(
                f"Added todo [{todo_id}]: {params.content}"
            )
        elif params.action.lower()=="complete":
            if not params.id:
                return ToolResult.error_result("'id' is required for 'complete' action")
            
            if params.id not in self._todos:
                return ToolResult.error_result(f"No todo found with id: {params.id}")
            
            content=self._todos.pop(params.id)
            return ToolResult.success_result(
                f"Completed todo [{params.id}]: {content}"
            )
        elif params.action.lower()=="list":
            if not self._todos:
                return ToolResult.success_result("No todos")
            
            lines=['TODOS:']
            for todo_id, content in self._todos.items():
                lines.append(f"- [{todo_id}] {content}")
            
            return ToolResult.success_result("\n".join(lines))
        
        elif params.action.lower()=="clear":
            count=len(self._todos)
            self._todos.clear()
            return ToolResult.success_result(f"Cleared ({count}) todos")
        
        else:
            return ToolResult.error_result(f"Invalid action: {params.action}. Must be one of: add, complete, list, clear")
            


