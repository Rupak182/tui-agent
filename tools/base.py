from __future__ import annotations
import abc
from dataclasses import dataclass
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field, ValidationError
from pydantic.schema import model_json_schema
from pathlib import Path

class ToolKind(Enum):
    READ = "read"
    WRITE = "write"
    SHELL = "shell"
    NETWORK = "network"
    MEMORY = "memory"
    MCP = "mcp"



@dataclass
class ToolInvokation:
   params:dict[str,Any]
   cwd:Path


@dataclass
class ToolConfirmation:
    tool_name:str
    params:dict[str,Any]
    description:str

@dataclass
class ToolResult:
    success:bool
    output:str
    error:str|None = None
    metadata:dict[str,Any]  = Field(default_factory=dict)

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
    async def execute(self, invocation:ToolInvokation) -> ToolResult:
        pass
    
    def validate_params(self, params:dict[str,Any])-> list[str]:
        schema = self.schema

        if isinstance(schema, type) and issubclass(schema, BaseModel):
            try:
                BaseModel(**params)
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
    
    async def get_confirmation(self,invokation:ToolInvokation)->ToolInvokation | None:
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