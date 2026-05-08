
import uuid
import logging
from ddgs import DDGS
from pydantic import BaseModel, Field
import json
from config.config import Config
from config.loader import get_data_dir
from tools.base import Tool, ToolInvocation, ToolKind, ToolKind, ToolResult
from utils.path import is_binary_file, resolve_path


#long term memory ,short term memory , episodic memory,sematic memory, memory optimizations (RAG etc)

logger = logging.getLogger(__name__)

class MemoryParams(BaseModel):
    action: str = Field(
        ..., description="Action: 'set', 'get', 'delete', 'list', 'clear'"
    )
    key: str | None = Field(
        None, description="Memory key (required for `set`, `get`, `delete`)"
    )
    value: str | None = Field(None, description="Value to store (required for `set`)")

class MemoryTool(Tool):
    name = "memory"
    kind = ToolKind.MEMORY
    description = "Store and retrieve persistent memory. Use this to remember user preferences, important context or notes."
    schema= MemoryParams

    def load_memory(self)-> dict:
        data_dir= get_data_dir()
        data_dir.mkdir(parents=True, exist_ok=True)
        path= data_dir / "user_memory.json"

        if not path.exists():
            return {'entries':{}}

        try:
            content= path.read_text(encoding="utf-8")
            return json.loads(content)
        except Exception as e:
            return {'entries':{}}
        
    def save_memory(self, memory:dict)-> None:
        data_dir= get_data_dir()
        data_dir.mkdir(parents=True, exist_ok=True)
        path= data_dir / "user_memory.json"

        try:
            path.write_text(json.dumps(memory, indent=2, ensure_ascii=False))
        except Exception as e:
            logger.error(f"Failed to save memory to {path}: {e}")
            raise


    async def execute(self, invocation:ToolInvocation)->ToolResult:
        params= MemoryParams(**invocation.params)

        if params.action.lower()=="set":
            if not params.key or not params.value:
                return ToolResult.error_result("'key' and 'value' are required for 'set' action")
            
            memory= self.load_memory()

            memory['entries'][params.key]= params.value

            try:
                self.save_memory(memory)
            except Exception as e:
                return ToolResult.error_result(f"Failed to save memory: {e}")
            
            return ToolResult.success_result(
                f"Memory added for key '{params.key}': {params.value}"
            )
        

        elif params.action.lower()=="get":
            if not params.key:
                return ToolResult.error_result("'key' is required for 'get' action")
            
            memory= self.load_memory()
            if params.key not in memory['entries']:
                return ToolResult.error_result(f"No memory found for key: {params.key}", metadata={"found":False})
            
            content=memory['entries'][params.key]
            return ToolResult.success_result(
                f"Retrieved memory for key '{params.key}': {content}",
                metadata={"found":True}
            )
        elif params.action.lower()=="delete":
            if not params.key:
                return ToolResult.error_result("'key' is required for 'delete' action")
            
            memory= self.load_memory()
            if params.key not in memory['entries']:
                return ToolResult.error_result(f"No memory found for key: {params.key}")
            
            del memory['entries'][params.key]
            self.save_memory(memory)
            return ToolResult.success_result(
                f"Deleted memory for key '{params.key}'"
            )
        
        elif params.action.lower()=="list":
            memory= self.load_memory()
            entries=memory.get('entries',{})
            if not entries:
                return ToolResult.success_result("No memory entries found", metadata={"found":False})
            
            lines=['Memory entries:']
            for key, value in sorted(entries.items()):
                lines.append(f"- {key}: {value}")
            
            return ToolResult.success_result("\n".join(lines), metadata={"found":True, })
        

        elif params.action.lower()=="clear":
            memory= self.load_memory()
            count=len(memory['entries'])
            memory['entries'].clear()
            self.save_memory(memory)
            return ToolResult.success_result(f"Cleared ({count}) memory entries")
        
        else:
            return ToolResult.error_result(f"Invalid action: {params.action}. Must be one of: set, get, delete, clear")
            


    
