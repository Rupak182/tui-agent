from __future__ import annotations
from typing import Any, AsyncGenerator
from agent.events import AgentEvent, AgentEventType
from client.llm_client import LLMClient
from client.response import StreamEventType, ToolCall
from context.manager import ContextManager
from tools.registry import create_default_registry  
from pathlib import Path
from client.response import ToolResultMessage

class Agent:
    def __init__(self):
        self.client = LLMClient()
        self.context_manager = ContextManager()
        self.tool_registry = create_default_registry()

    async def run(self, message: str) -> AsyncGenerator[AgentEvent, None]:
        yield AgentEvent.agent_start(message=message)
        # ADD user message to context
        self.context_manager.add_user_message(message)
        final_response:str|None = None
        async for event in self._agentic_loop():
            yield event

            if event.type == AgentEventType.TEXT_COMPLETE:
                final_response = event.data.get("content", "") if event.data else ""
        yield AgentEvent.agent_end(response=final_response, usage=None)  # You can pass actual response and usage if available


    async def _agentic_loop(self) -> AsyncGenerator[AgentEvent, None]:
        response_text = ""
        tool_schemas= self.tool_registry.get_schemas()
        tool_calls:list[ToolCall] = []
        async for event in self.client.chat_completion(
           self.context_manager.get_messages(),
           tools=tool_schemas if tool_schemas else None,
            stream=True
        ):
            if event.type == StreamEventType.TEXT_DELTA:
                if event.text_delta:
                    content = event.text_delta.content if event.text_delta else ""
                    response_text += content
                    yield AgentEvent.text_delta(content=content)

            elif event.type == StreamEventType.TOOL_CALL_COMPLETE:
                if event.tool_call:
                    tool_calls.append(event.tool_call)

            elif event.type == StreamEventType.ERROR:
                yield AgentEvent.agent_error(error=event.error) or "Unknown error"

        self.context_manager.add_assistant_message(response_text or None)

        if response_text:
            yield AgentEvent.text_complete(content=response_text)


        tool_call_results: list[ToolResultMessage] = []
        for tool_call in tool_calls:
            yield AgentEvent.tool_call_start(
                call_id=tool_call.call_id,
                name=tool_call.name,
                arguments=tool_call.arguments
             )
            tool_result = await self.tool_registry.invoke(
                name=tool_call.name,
                params=tool_call.arguments,
                cwd=Path.cwd()
            )

            yield AgentEvent.tool_call_complete(
                call_id=tool_call.call_id,
                name=tool_call.name,
                result=tool_result
             )
            
            tool_call_results.append(
                ToolResultMessage(
                    tool_call_id=tool_call.call_id,
                    content=tool_result.to_model_output(),
                    is_error=not tool_result.success
                )
            )


        for tool_result in tool_call_results:
            self.context_manager.add_tool_result(
                tool_result.tool_call_id,
                tool_result.content,
            )
            



    async def __aenter__(self) ->Agent:
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.client:
            await self.client.close()
        