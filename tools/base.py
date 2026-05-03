from __future__ import annotations
import abc
from dataclasses import dataclass
import difflib
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field, ValidationError
from pydantic.json_schema import model_json_schema
from pathlib import Path
class ToolKind(Enum):
    READ = "read"
    WRITE = "write"
    SHELL = "shell"
    NETWORK = "network"
    MEMORY = "memory"
    MCP = "mcp"



@dataclass
class ToolInvocation:
   params:dict[str,Any]
   cwd:Path


@dataclass
class ToolConfirmation:
    tool_name:str
    params:dict[str,Any]
    description:str


@dataclass
class FileDiff:
    path: Path
    old_content:str
    new_content:str

    is_new_file:bool = False
    is_deletion:bool = False

    def to_diff(self)->str:
        old_lines= self.old_content.splitlines(keepends=True)
        new_lines= self.new_content.splitlines(keepends=True)

        if old_lines and  not old_lines[-1].endswith("\n"):
            old_lines[-1] += "\n"
        
        if new_lines and not new_lines[-1].endswith("\n"):
            new_lines[-1] += "\n"
        
        old_name = "/dev/null" if self.is_new_file else f"{self.path}"
        new_name = "/dev/null" if self.is_deletion else f"{self.path}"
        diff = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f'{old_name}',
            tofile=f'{new_name}'
        )

        return "".join(diff)    



@dataclass
class ToolResult:
    success:bool
    output:str
    error:str|None = None
    metadata:dict[str,Any]  = Field(default_factory=dict)
    truncated:bool = False
    diff:FileDiff | None = None

    @classmethod
    def error_result(cls, error_message:str, **kwargs)->ToolResult:
        return cls(success=False, output="", error=error_message, **kwargs)

    @classmethod
    def success_result(cls, output:str, **kwargs)->ToolResult:
        return cls(success=True, output=output, error=None,**kwargs)
    
    def to_model_output(self)-> str:
        if self.success:
            return self.output
        else:
            return f"Error: {self.error}\n\n {self.output}"

class Tool(abc.ABC):
    name:str
    description:str ="Base Tool"
    kind:ToolKind=ToolKind.READ

    def __init__(self):
        pass

    @property
    def schema(self)->dict[str,Any] | type['BaseModel']:
        raise NotImplementedError("Tool schema method must be implemented by subclasses")
    

    @abc.abstractmethod
    async def execute(self, invocation:ToolInvocation) -> ToolResult:
        pass
    
    def validate_params(self, params:dict[str,Any])-> list[str]:
        schema = self.schema

        if isinstance(schema, type) and issubclass(schema, BaseModel):
            try:
                schema(**params)
                return []
            except ValidationError as e:
                errors =[]
                for err in e.errors():
                    field= ".".join(str(x) for x in err.get("loc",[]))
                    msg  =err.get("msg","Validation error")
                    errors.append(f"Parameter {field}: {msg}")
                return errors
            except Exception as e:
                return [str(e)]
        
        return []  # openai handles validation errors for dict directly
    
    
    def is_mutating(self,params:dict[str,Any])-> bool:
        return self.kind in {ToolKind.WRITE,ToolKind.SHELL,ToolKind.NETWORK,ToolKind.MEMORY}
    
    async def get_confirmation(self,invokation:ToolInvocation)->ToolInvocation | None:
        if not self.is_mutating(invokation.params):
            return None
        
        return ToolConfirmation(
            tool_name=self.name,
            params=invokation.params,
            description=f"Execute {self.name}"
        )
    

    def to_openai_schema(self)->dict[str,Any]:
        schema = self.schema
        if isinstance(schema, type) and issubclass(schema, BaseModel):
            json_schemma= model_json_schema(schema,mode="serialization")
            
            return {
                'name': self.name,
                'description': self.description,
                'parameters': {
                    'type': 'object',
                    'properties': json_schemma.get("properties", {}),
                    'required': json_schemma.get("required", []),
                }
            }
        
        if isinstance(schema, dict):
            result= {
                'name': self.name,
                'description': self.description,
            }

            if 'parameters' in schema:
                result['parameters'] = schema['parameters']
            else:
                result['parameters']= schema

            return result
        raise ValueError(f"Invalid schema type for tool {self.name}:{type(schema)}")