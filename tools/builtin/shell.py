from tools.base import Tool, ToolConfirmation, ToolInvocation, ToolKind, ToolResult
from pydantic import BaseModel, Field

from utils.path import resolve_path
import os
import fnmatch
import sys
import asyncio
import signal


BLOCKED_COMMANDS = {
    "rm -rf /",
    "rm -rf ~",
    "rm -rf /*",
    "dd if=/dev/zero",
    "dd if=/dev/random",
    "mkfs",
    "fdisk",
    "parted",
    ":(){ :|:& };:",  # Fork bomb
    "chmod 777 /",
    "chmod -R 777",
    "shutdown",
    "reboot",
    "halt",
    "poweroff",
    "init 0",
    "init 6",
}

class ShellParams(BaseModel):
    command:str =Field(..., description="The shell command to execute. ")
    timeout:int =Field(120,ge=1,le=600, description="Timeout in seconds (default: 120)")
    cwd: str | None = Field(None, description="Working directory for the command")



class ShellTool(Tool):
    name="shell"
    kind=ToolKind.SHELL
    description = "Execute a shell command. Use this for running system commands, scripts and CLI tools."
    schema = ShellParams

    def get_confirmation(
        self, invocation: ToolInvocation
    ) -> ToolConfirmation | None:
        params = ShellParams(**invocation.params)

        for blocked in BLOCKED_COMMANDS:
            if blocked in params.command:
                return ToolConfirmation(
                    tool_name=self.name,
                    params=invocation.params,
                    description=f"Execute (BLOCKED): {params.command}",
                    command=params.command,
                    is_dangerous=True,
                )

        return ToolConfirmation(
            tool_name=self.name,
            params=invocation.params,
            description=f"Execute: {params.command}",
            command=params.command,
            is_dangerous=False,
        )
    async def execute(self, invocation: ToolInvocation) -> ToolResult:
        params = ShellParams(**invocation.params)

        command = params.command.lower()
        for blocked in BLOCKED_COMMANDS:
                if blocked in command:
                    return ToolResult.error_result(
                    f"Command blocked for safety: {params.command}",
                    metadata={"blocked": True},
                )
        cwd = resolve_path(invocation.cwd, params.cwd) if params.cwd else invocation.cwd

        if not cwd.exists():
            return ToolResult.error_result(f"Working directory doesn't exist: {cwd}")

        env = self._build_environment()

        if sys.platform == "win32":
            shell_cmd = ["cmd.exe", "/c", params.command]
        else:
            shell_cmd = ["/bin/bash", "-c", params.command]

        process = await asyncio.create_subprocess_exec(
            *shell_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(cwd),
            env=env,
            start_new_session=True,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=params.timeout
            )
        except asyncio.TimeoutError:
            if sys.platform != "win32":
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            else:
                process.kill()
            await process.wait()
            return ToolResult.error_result(
                f"Command timed out after {params.timeout} seconds: {params.command}",
            )

        stdout_text = stdout.decode("utf-8", errors="replace")
        stderr_text = stderr.decode("utf-8", errors="replace")
        exit_code = process.returncode
        output = ""
        if stdout_text.strip():
            output += stdout_text.rstrip()

        if stderr_text.strip():
            output += "\n--- stderr ---\n"
            output += stderr_text.rstrip()

        if exit_code != 0:
            output += f"\nExit code: {exit_code}"

        if len(output) > 100 * 1024:
            output = output[: 100 * 1024] + "\n...[Output truncated]"

        return ToolResult(
            success=exit_code == 0,
            output=output,
            error=stderr_text if exit_code != 0 else None,
            exit_code=exit_code,
        )

            
            
               
                
                    

                   



    def _build_environment(self) -> dict[str,str]:
        env = os.environ.copy()
        shell_environment=self.config.shell_environment

        if not shell_environment.ignore_default_excludes:
            for pattern in shell_environment.exclude_patterns:
                keys_to_remove = [key for key in env if fnmatch.fnmatch(key.upper(), pattern.upper())]
                for key in keys_to_remove:
                    del env[key]

        if shell_environment.set_vars:
            env.update(shell_environment.set_vars)

        return env

        