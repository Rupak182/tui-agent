

from datetime import datetime
from typing import Any

from client.response import TokenUsage
from config.config import Config
from prompts.system import get_system_prompt
from dataclasses import dataclass, field

from tools.base import Tool
from utils.text import count_tokens

@dataclass
class MessageItem:
    role:str
    content:str
    token_count:int=0
    tool_call_id:str|None = None
    tool_calls: list[dict[str,Any]] = field(default_factory=list)
    pruned_at: datetime | None = None

    def to_dict(self)->dict[str,Any]:
        result:dict[str,Any] = {
            "role": self.role,
        }
        if self.content:
            result["content"] = self.content
        
        if self.tool_call_id:
            result["tool_call_id"] = self.tool_call_id
        
        if self.tool_calls:
            result["tool_calls"] = self.tool_calls
        return result

class ContextManager:
    PRUNE_PROTECT_TOKENS=15000
    PRUNE_MINIMUM_TOKENS=5000
    def __init__(self,config:Config,user_memory:str|None = None,tools=list[Tool]| None):
        self._system_prompt = get_system_prompt(config=config, user_memory=user_memory,tools=tools)
        self._messages:list[MessageItem] = []
        self._model_name = config.model_name
        self.config = config
        self.latest_usage: TokenUsage = TokenUsage()
        self.total_usage: TokenUsage = TokenUsage()

    def add_user_message(self,content:str):
        self._messages.append(
            MessageItem(role="user", content=content, token_count=count_tokens(content, self._model_name))
        )

    def add_assistant_message(self,content:str,tool_calls:list[dict[str,Any]]):
        self._messages.append(
            MessageItem(role="assistant", content=content or "", token_count=count_tokens(content or "", self._model_name), tool_calls=tool_calls or [])
        )

    def add_tool_result(self,tool_call_id:str, content:str)->None:
        item= MessageItem(
            role="tool",
            content=content,
            tool_call_id=tool_call_id,
            token_count=count_tokens(content, self._model_name),
        )
        self._messages.append(item)


    def needs_compression(self)->bool:
        context_limit=self.config.model.context_window

        current_tokens= self.latest_usage.total_tokens

        return current_tokens >= context_limit * 0.8


    def get_messages(self)->list[dict[str,Any]]:
        messages = []

        if self._system_prompt:
            messages.append({"role":"system","content":self._system_prompt})

        for item in self._messages:
            messages.append(item.to_dict())
        return messages
    
    def setlatest_usage(self, usage:TokenUsage):
        self.latest_usage = usage

    def add_usage(self, usage:TokenUsage):
        self.total_usage += usage


    
    def replace_with_summary(self, summary:str):
        self._messages = []


        continuation_content = f"""# Context Restoration (Previous Session Compacted)

        The previous conversation was compacted due to context length limits. Below is a detailed summary of the work done so far. 

        **CRITICAL: Actions listed under "COMPLETED ACTIONS" are already done. DO NOT repeat them.**

        ---

        {summary}

        ---

        Resume work from where we left off. Focus ONLY on the remaining tasks."""

        summary_item = MessageItem(
            role="user",
            content=continuation_content,
            token_count=count_tokens(continuation_content, self._model_name),
        )
        self._messages.append(summary_item)


    
    def prune_tool_outputs(self)->int:
        user_messages_count= sum(1 for msg in self._messages if msg.role=="user")
        if user_messages_count<2:
            return 0

        total_tokens=0
        pruned_tokens=0
        to_prune:list[MessageItem] = []
        for msg in reversed(self._messages):
            if msg.role=="tool" and msg.tool_call_id:
                if msg.pruned_at:
                    break
                tokens = msg.token_count or count_tokens(msg.content, self._model_name)
                total_tokens += tokens

                if total_tokens > self.PRUNE_PROTECT_TOKENS:
                    pruned_tokens += tokens
                    to_prune.append(msg)
        
        if pruned_tokens < self.PRUNE_MINIMUM_TOKENS:
            return 0
        
        pruned_count=0

        for msg in to_prune:
            msg.content = "[OLD tool result content cleared]"
            msg.token_count = count_tokens(msg.content, self._model_name)
            msg.pruned_at= datetime.now()
            pruned_count += 1

        return pruned_count
    
    def clear(self)->None:
        self._messages.clear()

    
    @property
    def message_count(self)->int:
        return len(self._messages)
    


                    
            


            