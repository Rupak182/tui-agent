from importlib.metadata import metadata
from os import name
from pathlib import Path
from typing import Any
import re
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.text import Text
from rich.panel import Panel
from rich.console import Console,Group
from rich.theme import Theme
from rich.rule import Rule
from rich.prompt import Prompt
from rich.table import Table
from rich import box
from config.config import Config
from tools.base import FileDiff, ToolConfirmation
from utils.path import display_path_rel_to_cwd
from utils.text import truncate_text
AGENT_THEME = Theme(
    {
        # General
        "info": "cyan",
        "warning": "yellow",
        "error": "bright_red bold",
        "success": "green",
        "dim": "dim",
        "muted": "grey50",
        "border": "grey35",
        "highlight": "bold cyan",
        # Roles
        "user": "bright_blue bold",
        "assistant": "bright_white",
        # Tools
        "tool": "bright_magenta bold",
        "tool.read": "cyan",
        "tool.write": "yellow",
        "tool.shell": "magenta",
        "tool.network": "bright_blue",
        "tool.memory": "green",
        "tool.mcp": "bright_cyan",
        # Code / blocks
        "code": "white",
    }
)

_console: Console | None = None

def get_console() -> Console:
    global _console
    if _console is None:
        _console = Console(theme=AGENT_THEME,highlight=False)
    return _console

class TUI:
    def __init__(self,config:Config, console: Console | None = None):
        self.console = console if console is not None else get_console()
        self._assistant_stream_open = False
        self._tool_args_by_call_id: dict[str,dict[str,Any]] = {}
        self.config = config
        self.cwd= self.config.cwd
        self.max_blob_tokens=240
    def begin_assistant(self)-> None:
        self.console.print()

        self.console.print(Rule(Text("Assistant", style="assistant")))
        self._assistant_stream_open=True
    
    def stream_assistant_delta(self,content:str)-> None:
        self.console.print(content, end="",markup=False)


    def end_assistant(self)-> None:
        if self._assistant_stream_open:
            self.console.print()
            self._assistant_stream_open=False

    def ordered_arguments(self,tool_name:str, arguments:dict[str,Any])-> list[tuple]:
        _PREFERRED_ORDER={
            'read_file':['path','offset','limit'],
            'write_file':['path','create_directories','content'],
            'edit':['path','replace_all','old_string','new_string'],
            'shell':['command','timeout','cwd'],
            'list_dir':['path','include_hidden'],
            'grep':['path','case_insensitive','pattern'],
            'glob':['path','pattern'],
            'todos':['id','action','content'],
            'memory':['action','key','value'],
        }

        preferred = _PREFERRED_ORDER.get(tool_name, [])

        ordered:list[tuple[str,Any]] = []
        seen=set()
        for key in preferred:
            if key in arguments:
                ordered.append((key, arguments[key]))
                seen.add(key)

        remaining_keys = set(arguments.keys() - seen)
        ordered.extend((key, arguments[key]) for key in remaining_keys)  # halucination maybe

        return ordered
    

    def _render_args_table(self,tool_name:str, arguments:dict[str,Any])->Table:
        table= Table.grid(padding=(0,1))
        table.add_column(style="muted", no_wrap=True)
        table.add_column(style="code",overflow="fold")

        for key, value in self.ordered_arguments(tool_name, arguments):
            if isinstance(value,str):
                if key in {'content','old_string','new_string'}:
                    line_count= len(value.splitlines()) or 0
                    byte_count= len(value.encode('utf-8',errors='replace'))
                    value= f"<{line_count} line(s), {byte_count} bytes>"
            
            if isinstance(value,bool):
                value= str(value)
                

            table.add_row(key, str(value))

        return table

    def tool_call_start(self,call_id:str, name:str, tool_kind:str, arguments:dict[str,Any])-> None:
        self._tool_args_by_call_id[call_id]=arguments
        border_style= f"tool.{tool_kind}" if tool_kind else "tool"
        
        
        title = Text.assemble(
            ("⏺ ", "muted"),
            (name, "tool"),
            ("  ", "muted"),
            (f"#{call_id[:8]}", "muted"),
        )

        display_args = dict(arguments)
        for key in ("path", "cwd"):
            val= display_args.get(key)

            if isinstance(val, str)  and self.cwd:
                display_args[key]= str(display_path_rel_to_cwd(val,self.cwd))
            
        panel = Panel(
            self._render_args_table(name, display_args) if display_args else Text("(no args)", style="muted"),
            border_style=border_style,
            title=title,
            padding=(1,2),
            box=box.ROUNDED,
            subtitle=Text("running", style="muted"),
            title_align="left",
            subtitle_align="right"
        )
        self.console.print()
        self.console.print(panel)

    def _extract_read_file_code(self,text:str)-> tuple[int,str]|None:
        body =text
        header_match = re.match(r"^Showing lines (\d+)-(\d+) of (\d+)\n\n", text)

        if header_match:
            body = text[header_match.end() :]

        code_lines:list[str] = []
        start_line:int |None = None

        for line in body.splitlines():
            m = re.match(r"^\s*(\d+)[:|](.*)$", line)
            if not m:
                return None
            line_num = int(m.group(1))
            code_lines.append(m.group(2))
            if start_line is None:
                start_line = line_num
            
        if start_line is None:
            return None
        
        return start_line, "\n".join(code_lines)



    def print_welcome(self, title: str, lines: list[str]) -> None:
        body = "\n".join(lines)
        self.console.print(
            Panel(
                Text(body, style="code"),
                title=Text(title, style="highlight"),
                title_align="left",
                border_style="border",
                box=box.ROUNDED,
                padding=(1, 2),
            )
        )

    def handle_confirmation(self,confirmation:ToolConfirmation)-> bool:
        output=[
            Text(confirmation.tool_name, style="tool"),
            Text(confirmation.description, style="code"),
            
        ]
        if confirmation.command:
            output.append(Text(f"$ {confirmation.command}", style="warning"))

        if confirmation.diff:
            diff_text= confirmation.diff.to_diff()
            output.append(
                Syntax(
                    diff_text,
                    'diff',
                    theme="monokai",
                    line_numbers=False,
                    word_wrap=True,
                )
            )
            self.console.print()
            self.console.print(
                 Panel(
                Group(*output),
                title=Text("Approval required", style="warning"),
                title_align="left",
                border_style="warning",
                box=box.ROUNDED,
                padding=(1, 2),
            )
            )

        response=Prompt.ask(
            "\nApprove this action?",
            choices=["y", "n",'yes','no'],
            default="n",
        )

        return response.lower() in {"y","yes"}







    def _guess_language(self, path: str | None) -> str:
        if not path:
            return "text"
        suffix = Path(path).suffix.lower()
        return {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "jsx",
            ".ts": "typescript",
            ".tsx": "tsx",
            ".json": "json",
            ".toml": "toml",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".md": "markdown",
            ".sh": "bash",
            ".bash": "bash",
            ".zsh": "bash",
            ".rs": "rust",
            ".go": "go",
            ".java": "java",
            ".kt": "kotlin",
            ".swift": "swift",
            ".c": "c",
            ".h": "c",
            ".cpp": "cpp",
            ".hpp": "cpp",
            ".css": "css",
            ".html": "html",
            ".xml": "xml",
            ".sql": "sql",
        }.get(suffix, "text")

    def tool_call_complete(
        self,
        call_id: str,
        name: str,
        tool_kind: str | None,
        success: bool,
        output: str,
        error: str | None,
        metadata: dict[str, Any] | None,
        truncated: bool,
        diff: str | None = None,
        exit_code: int | None = None
    ) -> None:

        border_style= f"tool.{tool_kind}" if tool_kind else "tool"
        status_icon = "✓" if success else "✗"
        status_style = "success" if success else "error"
        title = Text.assemble(
            (f"{status_icon} ", status_style),
            (name, "tool"),
            ("  ", "muted"),
            (f"#{call_id[:8]}", "muted"),
        )

        args = self._tool_args_by_call_id.get(call_id, {})
        primary_path= None
        blocks=[]
        if isinstance(metadata, dict) and isinstance(metadata.get("path"), str):
            primary_path = metadata["path"]

        if name == "read_file" and success:
            if primary_path:
                extracted = self._extract_read_file_code(output)
                start_line, code = extracted
                shown_start= None
                shown_end = None
                total_lines = None

                shown_start = metadata.get("shown_start") if isinstance(metadata, dict) else None
                total_lines = metadata.get("total_lines") if isinstance(metadata, dict) else None
                shown_end = metadata.get("shown_end") if isinstance(metadata, dict) else None
                pl=self._guess_language(primary_path)
                

                header_parts=[str(display_path_rel_to_cwd(primary_path,self.cwd))]
                
                header_parts.append(" ")

                if shown_start and shown_end and total_lines:
                    header_parts.append(
                        f"lines {shown_start}-{shown_end} of {total_lines}"
                    )
                header = "".join(header_parts)

                blocks.append(Text(header, style="muted"))

                blocks.append(
                            Syntax(
                                code,
                                pl,
                                theme="monokai",
                                line_numbers=True,
                                start_line=start_line,
                                word_wrap=False,
                            )
                )
            else:
                output_display=truncate_text(output,"",self.max_blob_tokens,)
                blocks.append(
                    Syntax(
                        output_display,
                        'text',
                        theme="monokai",
                        line_numbers=True,
                        word_wrap=False,
                    )
                )

        elif name in {"write_file", "edit"} and success and diff:
            output_line= output.strip() if output.strip() else "Done."
            blocks.append(Text(output_line, style="muted"))
            diff_text= diff
            diff_display=truncate_text(diff_text,self.config.model_name,self.max_blob_tokens)
            blocks.append(
                Syntax(
                    diff_display,
                    'diff',
                    theme="monokai",
                    line_numbers=False,
                    word_wrap=True,
                )
            )

        elif name=="shell" and success:
            command =args.get("command") 
            if isinstance(command, str) and command.strip():
                blocks.append(Text(f"$ {command.strip()}", style="muted"))

            if exit_code is not None:
                blocks.append(Text(f"Exit code: {exit_code}", style="muted"))
            
            output_display=truncate_text(output,self.config.model_name,self.max_blob_tokens)
            blocks.append(
                Syntax(
                    output_display,
                    'text',
                    theme="monokai",
                    word_wrap=True,
                )
            )


        elif name=="list_dir" and success:
            entries = metadata.get("entries") 
            path= metadata.get("path")
            summary=[]
            if isinstance(path, str) :
                summary.append(path)

            if isinstance(entries, int):
                summary.append(f"{entries} entr{'y' if entries<=1 else 'ies'}")
            
            if summary:
                blocks.append(Text(" • ".join(summary), style="muted"))

            output_display=truncate_text(output,self.config.model_name,self.max_blob_tokens)

            blocks.append(
                Syntax(
                    output_display,
                    'text',
                    theme="monokai",
                    word_wrap=True,
                )
            )

        elif name=="grep" and success:
            matches = metadata.get("matches")
            files_searched = metadata.get("files_searched")
            summary = []

            if isinstance(matches, int):
                summary.append(f"{matches} match{'es' if matches!=1 else ''}")
            
            if isinstance(files_searched, int):
                summary.append(f" in {files_searched} file{'s' if files_searched!=1 else ''}")
            
            if summary:
                blocks.append(Text(" • ".join(summary), style="muted"))
            
            truncate_text(output,self.config.model_name,self.max_blob_tokens)

            blocks.append(
                Syntax(
                    output,
                    'text',
                    theme="monokai",
                    word_wrap=True,
                )
            )

        elif name=="glob" and success:
            matches = metadata.get("matches")
            files_searched = metadata.get("files_searched")

            if isinstance(matches, int):
                blocks.append(f"{matches} match{'es' if matches!=1 else ''}")
            
            
            output_display=truncate_text(output,self.config.model_name,self.max_blob_tokens)

            blocks.append(
                Syntax(
                    output_display,
                    'text',
                    theme="monokai",
                    word_wrap=True,
                )
            )
        
        elif name=="web_search" and success:
            results = metadata.get("results")
            summary = []
            if isinstance(results, int):
                summary.append(f"{results} result{'s' if results!=1 else ''}")
            query = args.get("query")
            if isinstance(query, str) and query.strip():
                summary.append(query)
            
            blocks.append(Text(" • ".join(summary), style="muted"))

          
            
            output_display=truncate_text(output,self.config.model_name,self.max_blob_tokens)

            blocks.append(
                Syntax(
                    output_display,
                    'text',
                    theme="monokai",
                    word_wrap=True,
                )
            )
            
        elif name=="web_fetch" and success:
            status_code = metadata.get("status_code")
            content_length = metadata.get("content_length")
            url= args.get("url")
            summary=[]
            if isinstance(status_code, int):
                summary.append(str(status_code))

            if isinstance(content_length, int):
                summary.append(Text(f"{content_length} bytes"))

            if isinstance(url, str) and url.strip():
                summary.append(Text(url))

            blocks.append(Text(" • ".join(summary), style="muted"))

          
            
            output_display=truncate_text(output,self.config.model_name,self.max_blob_tokens)

            blocks.append(
                Syntax(
                    output_display,
                    'text',
                    theme="monokai",
                    word_wrap=True,
                )
            )
     
        elif name=="todos" and success:
            output_display=truncate_text(output,self.config.model_name,self.max_blob_tokens)

            blocks.append(
                Syntax(
                    output_display,
                    'text',
                    theme="monokai",
                    word_wrap=True,
                )
            )
            # can make a table for better ui

        elif name=="memory" and success:
            summary=[]
            action = args.get("action")
            key= args.get("key")
            found= metadata.get("found") if isinstance(metadata, dict) else None
            if isinstance(action, str) and action.strip():
                summary.append(action)
            
            if isinstance(key, str) and key.strip():
                summary.append(key)

            if  isinstance(found, bool):
                summary.append("found" if found else "not found")
            
            if summary:
                blocks.append(Text(" • ".join(summary), style="muted"))
            


            output_display=truncate_text(output,self.config.model_name,self.max_blob_tokens)
            blocks.append(
                Syntax(
                    output_display,
                    'text',
                    theme="monokai",
                    word_wrap=True,
                )
            )

        if error and not success:
            blocks.append(Text(error, style="error"))
            output_display=truncate_text(output,self.config.model_name,self.max_blob_tokens)

            if output_display:
                blocks.append(
                    Syntax(
                        output_display,
                        'text',
                        theme="monokai",
                        word_wrap=True,
                    )
                )
            else:
                blocks.append(Text("(no output)", style="muted"))



    
        if truncated:
            blocks.append(Text("\n[output truncated]", style="warning"))

        panel = Panel(
            Group(*blocks),
            title=title,
            padding=(1,2),
            box=box.ROUNDED,
            subtitle=Text("done" if success else "failed", style=status_style),
            title_align="left",
            subtitle_align="right",
            border_style=border_style,
        )


        self.console.print()
        self.console.print(panel)

    def show_help(self) -> None:
        help_text = """
## Commands

- `/help` - Show this help
- `/exit` or `/quit` - Exit the agent
- `/clear` - Clear conversation history
- `/config` - Show current configuration
- `/model <name>` - Change the model
- `/approval <mode>` - Change approval mode
- `/stats` - Show session statistics
- `/tools` - List available tools
- `/mcp` - Show MCP server status
- `/save` - Save current session
- `/checkpoint [name]` - Create a checkpoint
- `/checkpoints` - List available checkpoints
- `/restore <checkpoint_id>` - Restore a checkpoint
- `/sessions` - List saved sessions
- `/resume <session_id>` - Resume a saved session

## Tips

- Just type your message to chat with the agent
- The agent can read, write, and execute code
- Some operations require approval (can be configured)
"""
        self.console.print(Markdown(help_text))