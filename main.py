from email import message
import sys
from typing import Any
from agent.agent import Agent, AgentEventType
from client.llm_client import LLMClient
import asyncio
import click
from pathlib import Path
from ui.tui import TUI, get_console
from config.loader import load_config
from config.config import Config
console = get_console()
class CLI:
    def __init__(self,config:Config):
        self.agent:Agent | None = None
        self.tui=TUI(config=config, console=console)
        self.config = config

    async def run_single(self,message:str) :
        async with Agent(config=self.config) as agent:
            self.agent = agent
            return await self._process_message(message)
        
    
    async def run_interactive(self) :
        self.tui.print_welcome(
            'AI Agent',
            lines=[
                f"model: {self.config.model_name}",
                f"cwd: {self.config.cwd}",
                "commands: /help /config /approval /model /exit",
            ],
        )
        async with Agent(config=self.config) as agent:
            self.agent = agent
            
            while True:
                try:
                    user_input=console.input("\n[user]> [/user]").strip()
                    if not user_input:
                        continue
                    
                    await self._process_message(user_input)
                except KeyboardInterrupt:
                    console.input("\n[dim] Use /exit to quit. [/dim]")
                except EOFError:
                    break
        console.print("\n[dim] Goodbye! [/dim]")

    def get_tool_kind(self, tool_name: str) -> str | None:
        tool = self.agent.session.tool_registry.get(tool_name)
        if tool:
            return tool.kind.value
        return None

    async def _process_message(self,message:str) ->str | None:
        if self.agent is None:
            return None

        assistant_steaming = False
        final_response = ""
        async for event in self.agent.run(message=message):
            # print(event)
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

            elif event.type == AgentEventType.TOOL_CALL_START:
                tool_name= event.data.get("name", "Unknown")
                tool=self.agent.session.tool_registry.get(tool_name)
                
                if not tool:
                    tool_kind=None
                tool_kind = tool.kind.value
                self.tui.tool_call_start(
                    event.data.get("call_id", ""),
                    tool_name,
                    tool_kind,
                    event.data.get("arguments", {})
                )

            elif event.type == AgentEventType.TOOL_CALL_COMPLETE:
                tool_name= event.data.get("name", "Unknown")
                tool_kind = self.get_tool_kind(tool_name)
                self.tui.tool_call_complete(
                    event.data.get("call_id", ""),
                    tool_name,
                    tool_kind,
                    event.data.get("success", False),
                    event.data.get("output", ""),
                    event.data.get("error", None),
                    event.data.get("metadata"),
                    event.data.get("truncated", False),
                    event.data.get("diff", None),
                    event.data.get("exit_code", None)
                )       
                

            elif event.type == AgentEventType.AGENT_ERROR:
                error_message = event.data.get("error", "Unknown error")
                console.print(f"[error]Error: {error_message}[/error]")
                return None

        return final_response         

async def run(messages:list[dict[str,Any]],stream:bool=False):
   
    print("done")



@click.command()
@click.argument("prompt", required=False)
@click.option("--cwd", "-c",help="Current working directory",
              type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path))
def main(prompt:str| None, cwd: Path):
    try:
        config= load_config(cwd=cwd)
    except Exception as e:
        console.print(f"[error]Config load error: {e}[/error] " )
        sys.exit(1)

    errors =config.validate()

    if errors:
        for error in errors:
            console.print(f"[error]{error}[/error]")
        sys.exit(1)
    cli= CLI(config=config)

    
    if prompt:
        result = asyncio.run(cli.run_single(message=prompt))
        if result is None:
            sys.exit(1)  #error
    else:
        asyncio.run(cli.run_interactive())

if __name__ == "__main__":
    main()
