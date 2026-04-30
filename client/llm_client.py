import asyncio
from typing import Any, AsyncGenerator

from client.response import StreamEventType, TextDelta, TokenUsage,StreamEvent
from openai import APIError, AsyncOpenAI, RateLimitError

class LLMClient:
    def __init__(self)->None:
        self._client: AsyncOpenAI |None =None
        self._max_retries = 3
    
    def get_client(self)->AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key="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",
                base_url="https://openrouter.ai/api/v1/",
            )
        return self._client

    async def close(self)-> None:
        if self._client:
            await self._client.close()
            self._client = None

    def build_tools(self, tools:list[dict[str,Any]])-> list[dict[str,Any]]:
       return [
           {
               'type':'function',
               'function': {
                     'name': tool.get("name"),
                     'description': tool.get("description",""),
                     'parameters': tool.get("parameters", {
                        "type": "object",
                        "properties": {},
                     })
               }
           }
           for tool in tools
       ]
    
    async def chat_completion(self, messages:list[dict[str,Any]],
                              tools:list[dict[str,Any]]|None=None,
                              stream:bool=False)->AsyncGenerator[StreamEvent, None]  :
        client= self.get_client()
        kwargs={
        "model":"openai/gpt-oss-120b:free",
        "messages":messages,
        "stream":stream
        }
        if tools:
            kwargs["tools"]= self.build_tools(tools)

        kwargs["tool_choice"] = "auto"


        for attempt in range(self._max_retries+1):
            try:
                if stream:
                    async for event in self._stream_response(client, kwargs):
                        yield event
                else:
                    event =await self._non_stream_response(client,kwargs)
                    yield event
                return
            except RateLimitError as e:
                if attempt == self._max_retries:
                    yield StreamEvent.rate_limit_error(error=f"Rate limit exceeded after {self._max_retries} attempts: {str(e)}")   
                    return
                wait_time = 2 ** attempt
                await asyncio.sleep(wait_time)

            except ConnectionError as e:
                if attempt == self._max_retries:
                    yield StreamEvent.connection_error(error=f"Connection error after {self._max_retries} attempts: {str(e)}")
                    return
                wait_time = 2 ** attempt
                await asyncio.sleep(wait_time)
           
            except APIError as e:
                yield StreamEvent.api_error(error=f"API error: {str(e)}")
                return

    async def _stream_response(self,client:AsyncOpenAI,kwargs:dict[str,Any]) -> AsyncGenerator[StreamEvent, None]:
        
        response = await client.chat.completions.create(**kwargs)
        usage:TokenUsage | None = None
        finish_reason:str | None = None
        async for chunk in response:
            if hasattr(chunk,"usage") and chunk.usage:
                usage = TokenUsage(
                    prompt_tokens=chunk.usage.prompt_tokens,
                    completion_tokens=chunk.usage.completion_tokens,
                    total_tokens=chunk.usage.total_tokens,
                    cached_tokens=chunk.usage.prompt_tokens_details.cached_tokens
                )
            if not chunk.choices:
                continue
            choice = chunk.choices[0]
            delta = choice.delta

            if choice.finish_reason:
                finish_reason = choice.finish_reason
            
            if delta.content:
                yield StreamEvent(
                    type=StreamEventType.TEXT_DELTA,
                    text_delta=TextDelta(content=delta.content),
                )
            # print(delta.tool_calls)
            print(delta)
            

        yield StreamEvent(
            type=StreamEventType.MESSAGE_COMPLETE,
            finish_reason=finish_reason,
            usage=usage
        )        
        
        

    async def _non_stream_response(self,client:AsyncOpenAI,kwargs:dict[str,Any])->StreamEvent:
        response = await client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        message=choice.message
        text_delta=None
        if message.content:
            text_delta=TextDelta(content=message.content)

        usage = None
        if response.usage:
            usage =TokenUsage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
                cached_tokens=response.usage.prompt_tokens_details.cached_tokens
            )
        return StreamEvent(
            type=StreamEventType.MESSAGE_COMPLETE,
            text_delta=text_delta,
            finish_reason=choice.finish_reason,
            usage=usage
        )