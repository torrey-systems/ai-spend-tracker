"""Tests for the config module."""

import os
import json
import tempfile
import pytest
from pathlib import Path

import config


def test_load_json_config():
    """Test loading JSON config files."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump({"test": "value"}, f)
        temp_file = f.name
    
    try:
        result = config.load_json_config(Path(temp_file))
        assert result == {"test": "value"}
    finally:
        os.unlink(temp_file)


def test_load_json_config_invalid():
    """Test loading invalid JSON config."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write("invalid json{{")
        temp_file = f.name
    
    try:
        result = config.load_json_config(Path(temp_file))
        assert result is None
    finally:
        os.unlink(temp_file)


def test_merge_configs():
    """Test config merging."""
    base = {"a": 1, "b": {"c": 2}}
    override = {"b": {"d": 3}, "e": 4}
    
    result = config.merge_configs(base, override)
    
    assert result == {"a": 1, "b": {"c": 2, "d": 3}, "e": 4}


def test_get_api_key_from_env():
    """Test getting API key from environment variable."""
    os.environ["TEST_API_KEY"] = "env-key"
    
    config_dict = {"providers": {"test": {"api_key": "config-key"}}}
    
    result = config.get_api_key(config_dict, "test", "TEST_API_KEY")
    
    assert result == "env-key"
    
    del os.environ["TEST_API_KEY"]


def test_get_api_key_from_config():
    """Test getting API key from config when env var not set."""
    if "TEST_API_KEY2" in os.environ:
        del os.environ["TEST_API_KEY2"]
    
    config_dict = {"providers": {"test": {"api_key": "config-key"}}}
    
    result = config.get_api_key(config_dict, "test", "TEST_API_KEY2")
    
    assert result == "config-key"


def test_get_cache_config():
    """Test getting cache configuration."""
    config_dict = {"cache": {"enabled": False, "ttl_seconds": 600}}
    
    result = config.get_cache_config(config_dict)
    
    assert result["enabled"] == False
    assert result["ttl_seconds"] == 600
    assert result["file"] == "/tmp/ai-spend-cache.json"  # default


def test_get_cache_config_defaults():
    """Test cache config defaults."""
    result = config.get_cache_config({})
    
    assert result["enabled"] == True
    assert result["ttl_seconds"] == 300
    assert result["file"] == "/tmp/ai-spend-cache.json"


def test_get_settings():
    """Test getting settings."""
    config_dict = {"settings": {"default_days": 60}}
    
    result = config.get_settings(config_dict)
    
    assert result["default_days"] == 60
    assert result["currency"] == "USD"  # default


def test_get_settings_defaults():
    """Test settings defaults."""
    result = config.get_settings({})
    
    assert result["default_days"] == 30
    assert result["currency"] == "USD"
