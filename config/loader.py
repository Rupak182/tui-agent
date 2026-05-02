from pathlib import Path
from typing import Any
from tomli import TOMLDecodeError
from platformdirs import user_config_dir
from config.config import Config
import tomli
from utils.errors import ConfigError
import logging

logger = logging.getLogger(__name__)

CONFIG_FILE_NAME = "config.toml"
AGENT_MD_FILE= "AGENT.md"

def get_config_dir()->Path:
    return Path(user_config_dir('ai-agent'))

def _get_system_config_path()->Path:
    return get_config_dir() / CONFIG_FILE_NAME



def _get_agent_md_file(cwd:Path)->Path | None:
    current= cwd.resolve()


    if current.is_dir():
        md_file= current / AGENT_MD_FILE
        if md_file.is_file():
            try:
                content= md_file.read_text(encoding="utf-8")
                return content
            except (OSError, IOError) as e:
                logger.warning(f"Error reading AGENT.md from {md_file}: {e}")
    return None



def get_project_config(cwd:Path)->Path | None:
    agent_dir= cwd.resolve() / ".ai-agent"

    if agent_dir.is_dir():
        config_file= agent_dir / CONFIG_FILE_NAME
        if config_file.is_file():
            return config_file
    return None

def _merge_dicts(base:dict, override:dict[str,Any])->dict[str,Any]:
    result= base.copy()
    for key, value in override.items():
        if isinstance(value, dict) and key in result and isinstance(result[key], dict):
            result[key] = _merge_dicts(result[key], value)
        else:
            result[key] = value
    return result



def _parse_toml(path:Path):
    try:
        with path.open("rb") as f:
            return tomli.load(f)
    except TOMLDecodeError as e:
        raise ConfigError("Invalid TOML in {path}: {e}", config_file=str(path)) from e

    except (OSError, IOError) as e:
        raise ConfigError("Error reading config file {path}: {e}", config_file=str(path)) from e

def load_config(cwd: Path | None = None) -> Config:
    cwd = cwd or Path.cwd()
    system_path= _get_system_config_path()

    config_dict:dict[str,Any] = {}
    if system_path.is_file():
        try:
            config_dict= _parse_toml(system_path)
        except Exception as e:
            logger.warning(f"Failed to load system config from {system_path}: {e}")

    project_path=get_project_config(cwd)
    if project_path:
        try:
             project_config_dict= _parse_toml(project_path)
             config_dict=_merge_dicts(config_dict, project_config_dict)
        except Exception as e:
            logger.warning(f"Failed to load project config from {project_path}: {e}")

    if "cwd" not in config_dict:
        config_dict["cwd"]= str(cwd)

    
    if "developer_instructions" not in config_dict:
        agent_md_content= _get_agent_md_file(cwd)
        if agent_md_content:
            config_dict["developer_instructions"]= agent_md_content
    try:
        config= Config(**config_dict)
        return config
    except Exception as e:
        raise ConfigError(f"Invalid configuration: {e}") from e
