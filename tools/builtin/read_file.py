from pydantic import BaseModel, Field

from tools.base import Tool, ToolInvocation, ToolKind, ToolKind, ToolResult
from utils.path import is_binary_file, resolve_path
from utils.text import count_tokens, truncate_text


class ReadFileParams(BaseModel):
    path: str= Field(..., description="Path of the file to read (relative to the working directory or absolute path)")
    offset:int = Field(1,ge=1, description="Line number to start reading from (1-based index).Defaults to 1")
    limit:int |None = Field(None, ge=1, description="Maximum number of lines to read. If not specified, reads the entire file starting from the offset line.")

class ReadFileTool(Tool):
    name = "read_file"
    description = (
        "Read the contents of a text file. Returns the file content with line numbers. "
        "For large files, use offset and limit to read specific portions. "
        "Cannot read binary files (images, executables, etc.)."
    )    
    kind =  ToolKind.READ

    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
    MAX_OUTPUT_TOKENS = 25000

    @property
    def schema(self) -> type[BaseModel]:
        return ReadFileParams

    async def execute(self, invocation:ToolInvocation) -> ToolResult:
        try:
            params = ReadFileParams(**invocation.params)
            path = resolve_path(invocation.cwd, params.path)
            if not path.exists():
                return ToolResult.error_result(
                    "File not found: {}".format(params.path)
                )
            
            if not path.is_file():
                return ToolResult.error_result(
                    "Path is not a file: {}".format(params.path),
                )
            
            file_size= path.stat().st_size
            if file_size > self.MAX_FILE_SIZE:
                return ToolResult.error_result(
                    "File too large: {:.2f} MB. Maximum allowed size is {:.2f} MB".format(
                        file_size / (1024 * 1024), self.MAX_FILE_SIZE / (1024 * 1024)
                    )
                )
            
            if is_binary_file(path):
                file_size_mb = file_size / (1024 * 1024)
                size_str = (
                    f"{file_size_mb:.2f}MB" if file_size_mb >= 1 else f"{file_size} bytes"
                )
                return ToolResult.error_result(
                    f"Cannot read binary file: {path.name} ({size_str}) "
                    f"This tool only reads text files."
                )
            try:
                content = path.read_text(encoding="utf-8")
            
            except UnicodeDecodeError:
                content = path.read_text(encoding="latin-1")

            lines = content.splitlines() # 0 based index
            total_lines = len(lines)

            if total_lines==0:
                return ToolResult.success_result("File is empty.",metadata={"total_lines":0})
            
            start_index = max(params.offset - 1, 0)
            if params.limit is not None:
                end_index = min(start_index + params.limit, total_lines)
            
            else:
                end_index = total_lines

            selected_lines = lines[start_index:end_index]

            formatted_lines =[]

            for i, line in enumerate(selected_lines, start=start_index + 1):
                formatted_lines.append(f"{i:6}:{line}")
            
            output = "\n".join(formatted_lines)

            tokens_count = count_tokens(output)  
            truncated = False
            if tokens_count > self.MAX_OUTPUT_TOKENS:
                output = truncate_text(
                        output,
                        self.MAX_OUTPUT_TOKENS,
                        suffix=f"\n... [truncated {total_lines} total lines]",
                    )
                truncated = True
            
            metadata_lines=[]

            if start_index > 0 or end_index < total_lines:
                    metadata_lines.append(
                        f"Showing lines {start_index+1}-{end_index} of {total_lines}"
                    )
            
            if metadata_lines:
                    header = " | ".join(metadata_lines) + "\n\n"
                    output = header + output

            return ToolResult.success_result(
                    output=output,
                    truncated=truncated,
                    metadata={
                        "path": str(path),
                        "total_lines": total_lines,
                        "shown_start": start_index + 1,
                        "shown_end": end_index,
                    },
                )
        except Exception as e:
            return ToolResult.error_result(f"Error reading file: {str(e)}")