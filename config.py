#!/usr/bin/env python3
"""
Configuration loader for AI Spend Tracker.
Supports JSON and YAML config files.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

logger = logging.getLogger(__name__)

# Config file locations (in order of priority - later ones override earlier)
CONFIG_LOCATIONS = [
    Path.home() / ".ai-spend-tracker.json",
    Path.home() / ".ai-spend-tracker.yaml",
    Path.home() / ".ai-spend-tracker.yml",
    Path("/etc/ai-spend-tracker.json"),
    Path("/etc/ai-spend-tracker.yaml"),
]

# Local config locations
LOCAL_CONFIG_LOCATIONS = [
    Path("ai-spend-tracker.json"),
    Path("ai-spend-tracker.yaml"),
    Path("ai-spend-tracker.yml"),
    Path(".ai-spend-tracker.json"),
    Path(".ai-spend-tracker.yaml"),
]


def load_yaml_config(config_path: Path) -> Optional[Dict[str, Any]]:
    """Load a YAML config file."""
    if not YAML_AVAILABLE:
        logger.warning(f"YAML not available, skipping {config_path}")
        return None
    
    try:
        with open(config_path, 'r') as f:
            data = yaml.safe_load(f)
            if data is None:
                return {}
            return data if isinstance(data, dict) else {}
    except Exception as e:
        logger.error(f"Failed to load YAML config from {config_path}: {e}")
        return None


def load_json_config(config_path: Path) -> Optional[Dict[str, Any]]:
    """Load a JSON config file."""
    try:
        with open(config_path, 'r') as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {config_path}: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to load JSON config from {config_path}: {e}")
        return None


def load_config_file(config_path: Path) -> Optional[Dict[str, Any]]:
    """Load a config file based on its extension."""
    suffix = config_path.suffix.lower()
    
    if suffix in ('.yaml', '.yml'):
        return load_yaml_config(config_path)
    elif suffix == '.json':
        return load_json_config(config_path)
    else:
        logger.warning(f"Unknown config file type: {config_path}")
        return None


def merge_configs(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge two config dictionaries. Override takes precedence."""
    result = base.copy()
    
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_configs(result[key], value)
        else:
            result[key] = value
    
    return result


def load_config(local_only: bool = False) -> Dict[str, Any]:
    """
    Load configuration from config files.
    
    Args:
        local_only: If True, only load local config files (not home dir or /etc)
    
    Returns:
        Merged configuration dictionary
    """
    config = {}
    
    # First, load system/global configs
    if not local_only:
        for config_path in CONFIG_LOCATIONS:
            if config_path.exists():
                logger.info(f"Loading config from {config_path}")
                file_config = load_config_file(config_path)
                if file_config:
                    config = merge_configs(config, file_config)
    
    # Then, load local configs (override previous)
    for config_path in LOCAL_CONFIG_LOCATIONS:
        if config_path.exists():
            logger.info(f"Loading local config from {config_path}")
            file_config = load_config_file(config_path)
            if file_config:
                config = merge_configs(config, file_config)
    
    return config


def get_api_key(config: Dict[str, Any], provider: str, env_var: str) -> Optional[str]:
    """
    Get API key from config or environment variable.
    Environment variables take precedence.
    """
    # First check environment variable (takes precedence)
    env_key = os.getenv(env_var)
    if env_key:
        return env_key
    
    # Then check config file
    provider_config = config.get("providers", {}).get(provider, {})
    return provider_config.get("api_key")


def get_provider_config(config: Dict[str, Any], provider: str) -> Dict[str, Any]:
    """Get configuration for a specific provider."""
    return config.get("providers", {}).get(provider, {})


def get_cache_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Get cache configuration."""
    default_cache = {
        "enabled": True,
        "file": "/tmp/ai-spend-cache.json",
        "ttl_seconds": 300
    }
    
    cache_config = config.get("cache", {})
    return {**default_cache, **cache_config}


def get_settings(config: Dict[str, Any]) -> Dict[str, Any]:
    """Get general settings."""
    default_settings = {
        "default_days": 30,
        "currency": "USD",
    }
    
    settings = config.get("settings", {})
    return {**default_settings, **settings}


# Example config structure (for documentation):
EXAMPLE_CONFIG = {
    "providers": {
        "openai": {
            "api_key": "sk-...",
            "org_id": "org-...",
        },
        "anthropic": {
            "api_key": "sk-ant-...",
        },
        "openrouter": {
            "api_key": "...",
        }
    },
    "cache": {
        "enabled": True,
        "file": "/tmp/ai-spend-cache.json",
        "ttl_seconds": 300
    },
    "settings": {
        "default_days": 30,
        "currency": "USD"
    }
}