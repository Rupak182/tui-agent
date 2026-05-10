
from importlib.resources import path

from importlib.resources import path

from pydantic import BaseModel, Field

from tools.base import FileDiff, Tool, ToolConfirmation, ToolInvocation, ToolKind, ToolResult
from utils.path import resolve_path,ensure_parent_dir


class WriteFileParams(BaseModel):
    path: str= Field(..., description="Path of the file to write (relative to the working directory or absolute path)")
    create_directories: bool = Field(True, description="Whether to create parent directories if they don't exist. Defaults to True.")
    content: str = Field(..., description="Content to write to the file")

class WriteFileTool(Tool):
    name = "write_file"
    description = (
        "Write content to a file. Creates the file if it doesn't exist, "
        "or overwrites if it does. Parent directories are created automatically. "
        "Use this for creating new files or completely replacing file contents. "
        "For partial modifications, use the edit tool instead."
    )
        
    kind = ToolKind.WRITE

    schema = WriteFileParams

    def get_confirmation(self, invocation: ToolInvocation) -> ToolConfirmation:
        params= WriteFileParams(**invocation.params)
        path= resolve_path(invocation.cwd, params.path)

        is_new_file = not path.exists()
        old_content = ""
        if not is_new_file:
            try:
                old_content = path.read_text(encoding="utf-8")
            except:
                pass

        action = "Create" if is_new_file else "Overwrite"
        
        diff = FileDiff(
            path=path,
            old_content=old_content,
            new_content=params.content,
            is_new_file=is_new_file,
        )

        return ToolConfirmation(
            tool_name=self.name,
            params=invocation.params,
            description=f"{action} file: {path}",
            diff=diff,
            affected_paths=[path],
            is_dangerous=not is_new_file,
        )

    async def execute(self, invocation:ToolInvocation) -> ToolResult:
        params = WriteFileParams(**invocation.params)
        path=resolve_path(invocation.cwd, params.path) 

        is_new_file = not path.exists()
        old_content = ""
        if not is_new_file:
            try:
                old_content=path.read_text(encoding="utf-8")
            except:
                pass

        try:
            if params.create_directories:
                ensure_parent_dir(path=path)
            
            elif not path.parent.exists():
                return ToolResult.error_result(
                    f"Parent directory doesn't exists:{path.parent}"
                )
            
            path.write_text(params.content, encoding="utf-8")

            action = "Created" if is_new_file else "Updated"
            line_count= len(params.content.splitlines())
            

            return ToolResult.success_result(
                f"{action} {path}  {line_count} lines",
                diff=FileDiff(
                    path=path,
                    old_content=old_content,
                    new_content=params.content,
                    is_new_file=is_new_file
                ),
                metadata={
                    "path": str(path),
                    "is_new_file": is_new_file,
                    "line_count": line_count,
                    'bytes':len(params.content.encode('utf-8'))
                }
            )
            
            

        except OSError as e:
            return ToolResult.error_result(
                f"Failed to write to file: {str(e)}",
            )

