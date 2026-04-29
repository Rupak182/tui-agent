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

        assistant_steaming = False
        final_response = ""
        async for event in self.agent.run(message=message):
            if event.type==AgentEventType.TEXT_DELTA:
                content = event.data.get("content", "")
                if not assistant_steaming:
                    self.tui.begin_assistant()
                    assistant_steaming = True
                self.tui.stream_assistant_delta(content=content)
            elif event.type == AgentEventType.TEXT_COMPLETE:
                final_response = event.data.get("content", "")
                if assistant_steaming:
                    assistant_steaming = False
                    self.tui.end_assistant()
            elif event.type == AgentEventType.AGENT_ERROR:
                error_message = event.data.get("error", "Unknown error")
                console.print(f"[error]Error: {error_message}[/error]")
                return None

        return final_response         

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
            sys.exit(1)  #error

if __name__ == "__main__":
    main()
