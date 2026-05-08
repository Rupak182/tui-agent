from typing import Any

from pydantic import BaseModel,Field
from pathlib import Path
import os
class ModelConfig(BaseModel):
    name:str= Field("nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free", description="Model name to use for the agent")
    temperature:float= Field(1, ge=0.0, le=2.0, description="Sampling temperature for the model")
    context_window:int = 256_000

class ShellEnvironmentPolicy(BaseModel):
    ignore_default_excludes:bool=False
    exclude_patterns: list[str] = Field(default_factory=lambda:['*KEY*','*SECRET*','*TOKEN*'])
    set_vars:dict[str,str] = Field(default_factory=dict)


class Config(BaseModel):
    model:ModelConfig= Field(default_factory=ModelConfig)
    cwd:Path= Field(default_factory=Path.cwd, description="Current working directory for the agent. Tool calls with relative paths will be resolved against this directory.")
    max_turns:int = 100
    shell_environment:ShellEnvironmentPolicy=Field(default_factory=ShellEnvironmentPolicy)

    developer_instructions:str |None= None
    user_instructions:str |None= None
    debug:bool = False
    allowed_tools:list[str] | None = None
    # subagent config 

    @property
    def api_key(self)->str|None:
        return os.environ.get("API_KEY")

    @property
    def base_url(self)->str|None:
        return os.environ.get("BASE_URL")
    
    @property
    def model_name(self)->str:
        return self.model.name

    @model_name.setter
    def model_name(self, value:str)->None:
     self.model.name = value
    
    @property
    def temperature(self)->float:
        return self.model.temperature
    
    @temperature.setter
    def temperature(self, value:float)->None:
        self.model.temperature = value

    
    def validate(self)->list[str]:
        errors = []
        if not self.api_key:
            errors.append("API_KEY environment variable is not set.")
        if not self.base_url:
            errors.append("BASE_URL environment variable is not set.")
        if not self.cwd.exists() or not self.cwd.is_dir():
            errors.append(f"CWD '{self.cwd}' does not exist or is not a directory.")
        
        return errors
    
    def to_dict(self)->dict[str,Any]:
        return self.model_dump(mode='json')