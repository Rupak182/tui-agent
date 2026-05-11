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

## Inspiration

This implementation is based on learning from [RivaanRanawat's ai-coding-agent](https://github.com/RivaanRanawat/ai-coding-agent).
