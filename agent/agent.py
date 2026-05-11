from __future__ import annotations
from typing import Any, AsyncGenerator, Callable

from agent.events import AgentEvent, AgentEventType
from agent.session import Session
from client.llm_client import LLMClient
from client.response import StreamEventType, TokenUsage, ToolCall
from context.manager import ContextManager
from pathlib import Path
import json
from client.response import ToolResultMessage
from config.config import Config
from prompts.system import create_loop_breaker_prompt
from tools.base import ToolConfirmation
from tools.base import ToolConfirmation
class Agent:
    def __init__(
        self,
        config: Config,
        confirmation_callback: Callable[[ToolConfirmation], bool] | None = None,
    ):        
        self.config = config
        self.session: Session | None = Session(config=config)
        self.session.approval_manager.confirmation_callback = confirmation_callback

    async def run(self, message: str) -> AsyncGenerator[AgentEvent, None]:
        await self.session.hook_system.trigger_before_agent(user_message=message)
        yield AgentEvent.agent_start(message=message)
        # ADD user message to context
        self.session.context_manager.add_user_message(message)
        final_response:str|None = None
        async for event in self._agentic_loop():
            yield event

            if event.type == AgentEventType.TEXT_COMPLETE:
                final_response = event.data.get("content", "") if event.data else ""
                await self.session.hook_system.trigger_after_agent(user_message=message, agent_response=final_response)
        yield AgentEvent.agent_end(response=final_response, usage=None)  # You can pass actual response and usage if available


    async def _agentic_loop(self) -> AsyncGenerator[AgentEvent, None]:
        max_turns= self.config.max_turns

        for turn_num in range(max_turns):
            self.session.increment_turn()
            self.session.context_manager.prune_tool_outputs()
            response_text = ""
            tool_schemas= self.session.tool_registry.get_schemas()
            tool_calls:list[ToolCall] = []

            if self.session.context_manager.needs_compression():
                summary,usage= await self.session.chat_compactor.compress(self.session.context_manager)

                if summary:
                    self.session.context_manager.replace_with_summary(summary)
                    self.session.context_manager.add_usage(usage) #approx
                    self.session.context_manager.set_latest_usage(usage)



            usage: TokenUsage | None = None




            async for event in self.session.client.chat_completion(
            self.session.context_manager.get_messages(),
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

                elif event.type == StreamEventType.MESSAGE_COMPLETE:
                    usage = event.usage
                    
            self.session.context_manager.add_assistant_message(
                response_text or None,
                [
                    {
                        "id": tool_call.call_id,
                        "type": "function",
                        "function": {
                            "name": tool_call.name,
                            "arguments": json.dumps(tool_call.arguments or {})
                        },
                    }
                    for tool_call in tool_calls
                ] if tool_calls else None,
            )

            if response_text:
                yield AgentEvent.text_complete(content=response_text)
                self.session.loop_detector.record_action("response", text=response_text)

            if usage:
                self.session.context_manager.set_latest_usage(usage)
                self.session.context_manager.add_usage(usage)

            if not tool_calls:
                return
            
            tool_call_results: list[ToolResultMessage] = []
            for tool_call in tool_calls:
                yield AgentEvent.tool_call_start(
                    call_id=tool_call.call_id,
                    name=tool_call.name,
                    arguments=tool_call.arguments
                )
                self.session.loop_detector.record_action("tool_call", args=tool_call.arguments)

               

                tool_result = await self.session.tool_registry.invoke(
                    name=tool_call.name,
                    params=tool_call.arguments,
                    cwd=self.session.config.cwd,
                    hook_system=self.session.hook_system,
                    approval_manager=self.session.approval_manager
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
                self.session.context_manager.add_tool_result(
                    tool_result.tool_call_id,
                    tool_result.content,
                )
            
            loop_detection=self.session.loop_detector.check_for_loop()

            if loop_detection:
                loop_prompt = create_loop_breaker_prompt(loop_detection)
                self.session.context_manager.add_user_message(loop_prompt)
                      



        yield AgentEvent.agent_error(f'Maximum number of turns ({self.config.max_turns}) reached for the conversation')


    async def __aenter__(self) ->Agent:
        await self.session.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.session and self.session.client:
            await self.session.client.close()
            self.session = None
        