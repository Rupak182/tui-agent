# AI Coding Agent

A powerful, interactive AI-powered coding assistant built with Python. Designed to help with code analysis, generation, and execution tasks directly from your terminal.

## Overview

This project implements an intelligent AI agent that can assist developers with various coding workflows. It leverages large language models and integrates with an array of tools (including the Model Context Protocol) to seamlessly access file systems, web resources, and more.

## Key Features

- **Interactive TUI**: A rich terminal interface for chatting with the AI.
- **Session Persistence**: Save, checkpoint, and resume your sessions so you never lose context.
- **Model Context Protocol (MCP)**: Native support for connecting to external MCP servers to expand the agent's capabilities.
- **Tool Ecosystem**: Built-in tools for file searching (grep), web fetching, memory management, and file editing.
- **Safety & Approvals**: Configurable approval policies to prevent the agent from running destructive actions without your explicit consent.

## Interactive Commands

While in the interactive console, you can use the following commands to manage your session:

- `/help` - Show available commands.
- `/config` - View the current configuration.
- `/model [name]` - View or change the active LLM.
- `/approval [policy]` - View or change the approval policy (e.g., `require_all`, `auto`).
- `/tools` - List all available tools.
- `/mcp` - List connected MCP servers and their statuses.
- `/stats` - View session statistics (token usage, message count, etc.).
- `/clear` - Clear the current conversation context.
- `/save` - Save the current session so it can be resumed later.
- `/checkpoint` - Create a checkpoint for the current session.
- `/sessions` - List all saved sessions and checkpoints.
- `/resume <session_id>` - Resume a previously saved session.
- `/restore <checkpoint_id>` - Restore a specific checkpoint.
- `/exit` or `/quit` - Exit the application.


## Getting Started

### Prerequisites

- **Python**: version 3.12 or higher.
- **uv**: A fast Python package installer and resolver.

---

### Installation

1. **Clone the repository**:

2. **Install dependencies**:
   Run `uv sync` to set up the virtual environment and install all dependencies:
   ```bash
   uv sync
   ```

---

### Environment Variables

Before starting the agent, you must set the environment variables to configure your LLM provider:

```bash
# Set your API Key and the API Base URL
export API_KEY="your-api-key"
export BASE_URL="https://api.groq.com/openai/v1" # Or your provider's endpoint
```

---

### Configuration

The application loads configuration in a layered manner:
1. **System Config**: Looks for a configuration file at `~/.config/ai-agent/config.toml` (on Linux/macOS).
2. **Project Config**: Looks for a `.ai-agent/config.toml` in the current working directory (CWD) to override system settings.
3. **Developer Instructions (`AGENT.md`)**: If an `AGENT.md` file is present in the current working directory, its contents are loaded as developer instructions for the agent.


### Running the Agent

You can start the agent in two modes:

#### 1. Interactive Mode (TUI)
Start an interactive terminal chat session with the agent:
```bash
uv run main.py
```

#### 2. Single Prompt Mode
Run the agent directly with a single prompt and exit after completion:
```bash
uv run main.py "Analyze the files in the current directory and list all python scripts"
```

#### Command-Line Arguments
- `--cwd` or `-c`: Specify the working directory for the agent (defaults to the current directory).
  ```bash
  uv run main.py -c /path/to/project
  ```

## Inspiration

This implementation is based on learning from [RivaanRanawat's ai-coding-agent](https://github.com/RivaanRanawat/ai-coding-agent).

