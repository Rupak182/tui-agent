from __future__ import annotations
from typing import Any, AsyncGenerator
from agent.events import AgentEvent, AgentEventType
from client.llm_client import LLMClient
from client.response import StreamEventType  



class Agent:
    def __init__(self):
        self.client = LLMClient()

    async def run(self, message: str) -> AsyncGenerator[AgentEvent, None]:
        yield AgentEvent.agent_start(message=message)
        # ADD user message to context
        final_response = ""
        async for event in self._agentic_loop():
            yield event

            if event.type == AgentEventType.TEXT_COMPLETE:
                final_response = event.data.get("content", "") if event.data else ""
        yield AgentEvent.agent_end(response=final_response, usage=None)  # You can pass actual response and usage if available


    async def _agentic_loop(self) -> AsyncGenerator[AgentEvent, None]:
        response_text = ""
        async for event in self.client.chat_completion(
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello, how are you?"},
            ]
            ,
            stream=True
        ):
            if event.type == StreamEventType.TEXT_DELTA:
                if event.text_delta:
                    content = event.text_delta.content if event.text_delta else ""
                    response_text += content
                    yield AgentEvent.text_delta(content=content)

            elif event.type == StreamEventType.ERROR:
                yield AgentEvent.agent_error(error=event.error) or "Unknown error"

        if response_text:
            yield AgentEvent.text_complete(content=response_text)


    async def __aenter__(self) ->Agent:
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.client:
            await self.client.close()
        