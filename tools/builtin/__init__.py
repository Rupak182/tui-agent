from tools.builtin.read_file import ReadFileTool
from tools.builtin.write_file import WriteFileTool
from tools.builtin.edit_file import EditTool
from tools.builtin.shell import ShellTool
from tools.builtin.list_dir import ListDirTool
__all__ = [
    "ReadFileTool",
    "WriteFileTool",
    "EditTool",
    "ShellTool",
]

def get_all_builtin_tools()->list[ReadFileTool | WriteFileTool | EditTool | ShellTool | ListDirTool]:
    return [ReadFileTool, WriteFileTool, EditTool, ShellTool, ListDirTool]