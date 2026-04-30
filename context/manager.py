

from typing import Any

from prompts.system import get_system_prompt
from dataclasses import dataclass

from utils.text import count_tokens

@dataclass
class MessageItem:
    role:str
    content:str
    token_count:int=0

    def to_dict(self)->dict[str,Any]:
        result:dict[str,Any] = {
            "role": self.role,
            "content": self.content,
        }
        return result

class ContextManager:
    def __init__(self):
        self._system_prompt = get_system_prompt()
        self._messages:list[MessageItem] = []
        self.model_name="nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"
    

    def add_user_message(self,content:str):
        self._messages.append(
            MessageItem(role="user", content=content, token_count=count_tokens(content, self.model_name))
        )

    def add_assistant_message(self,content:str):
        self._messages.append(
            MessageItem(role="assistant", content=content or "", token_count=count_tokens(content or "", self.model_name))
        )

    def get_messages(self)->list[dict[str,Any]]:
        messages = []

        if self._system_prompt:
            messages.append({"role":"system","content":self._system_prompt})

        for item in self._messages:
            messages.append(item.to_dict())
        return messages