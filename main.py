import sys
from typing import Any
from agent.agent import Agent, AgentEventType
from client.llm_client import LLMClient
import asyncio
import click

from ui.tui import TUI, get_console

console = get_console()
class CLI:
    def __init__(self):
        self.agent:Agent | None = None
        self.tui=TUI(console=console)
    
    async def run_single(self,message:str) :
        async with Agent() as agent:
            self.agent = agent
            return await self._process_message(message)

    async def _process_message(self,message:str) ->str | None:
        if self.agent is None:
            return None

        full_response = ""
        async for event in self.agent.run(message=message):
            if event.type==AgentEventType.TEXT_DELTA:
                content = event.data.get("content", "")
                self.tui.stream_assistant_delta(content=content)
                full_response += content
            elif event.type == AgentEventType.TEXT_COMPLETE:
                full_response = event.data.get("content", "")
        return full_response


async def run(messages:list[dict[str,Any]],stream:bool=False):
   
    print("done")



@click.command()
@click.argument("prompt", required=False)
def main(prompt:str| None):
    cli= CLI()
    messages=[
            {"role":"system","content":"You are a helpful assistant."},  # read about cached tokens
            {"role":"user","content": prompt}
        ]

    if prompt:
        result = asyncio.run(cli.run_single(message=prompt))
        if result is None:
            sys.exit(1)

if __name__ == "__main__":
    main()
