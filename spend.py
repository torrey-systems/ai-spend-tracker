#!/usr/bin/env python3
"""
AI Spend Tracker - Fetches spend from multiple AI API providers.
"""

import os
import json
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, Optional
from functools import wraps

# Import config module for file-based configuration
from config import load_config, get_api_key, get_provider_config, get_cache_config, get_settings
from errors import retry_on_exception

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load configuration at module level
_config = None

def _get_config():
    """Get or load configuration."""
    global _config
    if _config is None:
        _config = load_config()
    return _config

# Configuration
OPENAI_ORG_ID = os.getenv("OPENAI_ORG_ID")
CACHE_FILE = "/tmp/ai-spend-cache.json"  # Can be overridden via config
CACHE_TTL_SECONDS = 300  # 5 minutes


def handle_provider_errors(provider_name: str):
    """Decorator to handle provider errors consistently."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except requests.exceptions.Timeout as e:
                logger.error(f"{provider_name} API timeout: {e}")
                return {"provider": provider_name, "error": f"Request timeout: {str(e)}"}
            except requests.exceptions.ConnectionError as e:
                logger.error(f"{provider_name} API connection error: {e}")
                return {"provider": provider_name, "error": f"Connection error: {str(e)}"}
            except requests.exceptions.HTTPError as e:
                status_code = e.response.status_code if e.response is not None else None
                logger.error(f"{provider_name} API HTTP error: {e} (status: {status_code})")
                return {"provider": provider_name, "error": f"HTTP {status_code}: {str(e)}"}
            except Exception as e:
                logger.error(f"{provider_name} API unexpected error: {e}")
                return {"provider": provider_name, "error": str(e)}
        return wrapper
    return decorator


@handle_provider_errors("OpenAI")
@retry_on_exception(max_retries=3, delay=1.0, backoff=2.0, exceptions=(requests.exceptions.RequestException,))
def get_openai_spend(api_key: str, days: int = 30) -> Optional[Dict]:
    """Fetch OpenAI usage from the API."""
    if not api_key:
        logger.warning("OpenAI API key not provided")
        return None
    
    config = _get_config()
    provider_config = get_provider_config(config, "openai")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
    }
    
    # Check for org_id in config first, then env var
    org_id = provider_config.get("org_id") or os.getenv("OPENAI_ORG_ID") or OPENAI_ORG_ID
    if org_id:
        headers["OpenAI-Organization"] = org_id
    
    # Get usage for last N days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    url = f"https://api.openai.com/v1/usage?start_date={start_date.strftime('%Y-%m-%d')}&end_date={end_date.strftime('%Y-%m-%d')}&granularity=daily"
    
    logger.info(f"Fetching OpenAI usage for {days} days")
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    data = response.json()
    
    total_spend = 0
    for day in data.get("data", []):
        total_spend += day.get("cost", 0)
    
    result = {
        "provider": "OpenAI",
        "total": round(total_spend, 4),
        "currency": "USD",
        "days": days
    }
    logger.info(f"OpenAI spend: {result['total']}")
    return result


@handle_provider_errors("Anthropic")
@retry_on_exception(max_retries=3, delay=1.0, backoff=2.0, exceptions=(requests.exceptions.RequestException,))
def get_anthropic_spend(api_key: str, days: int = 30) -> Optional[Dict]:
    """Fetch Anthropic usage from the API."""
    if not api_key:
        logger.warning("Anthropic API key not provided")
        return None
    
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01"
    }
    
    url = "https://api.anthropic.com/v1/organizations/self/usage"
    
    logger.info(f"Fetching Anthropic usage for {days} days")
    response = requests.get(url, headers=headers, timeout=10)
    
    if response.status_code == 404:
        logger.warning("Anthropic API endpoint not found - may need org ID")
        return {"provider": "Anthropic", "error": "API endpoint not found - may need org ID"}
    
    response.raise_for_status()
    
    # Anthropic billing API is limited
    result = {
        "provider": "Anthropic",
        "total": 0,
        "currency": "USD",
        "note": "API access limited",
        "days": days
    }
    logger.info(f"Anthropic spend: {result['total']}")
    return result


@handle_provider_errors("OpenRouter")
@retry_on_exception(max_retries=3, delay=1.0, backoff=2.0, exceptions=(requests.exceptions.RequestException,))
def get_openrouter_spend(api_key: str, days: int = 30) -> Optional[Dict]:
    """Fetch OpenRouter usage from the API."""
    if not api_key:
        logger.warning("OpenRouter API key not provided")
        return None
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://openrouter.ai",
    }
    
    url = "https://openrouter.ai/api/v1/credits"
    
    logger.info(f"Fetching OpenRouter usage for {days} days")
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    data = response.json()
    
    total_spend = data.get("data", {}).get("total_usage", 0)
    
    result = {
        "provider": "OpenRouter",
        "total": round(total_spend, 4),
        "currency": "USD",
        "days": days
    }
    logger.info(f"OpenRouter spend: {result['total']}")
    return result


def get_cursor_spend() -> Optional[Dict]:
    """Cursor doesn't have a public API."""
    return {
        "provider": "Cursor",
        "total": 0,
        "currency": "USD",
        "note": "No public API - manual entry required"
    }


def load_cache(config: Dict = None) -> Optional[Dict]:
    """Load cached results if still valid."""
    if config is None:
        config = _get_config()
    
    cache_cfg = get_cache_config(config)
    cache_file = cache_cfg.get("file", CACHE_FILE)
    cache_ttl = cache_cfg.get("ttl_seconds", CACHE_TTL_SECONDS)
    
    if not cache_cfg.get("enabled", True):
        logger.debug("Cache disabled")
        return None
    
    if not os.path.exists(cache_file):
        logger.debug(f"Cache file {cache_file} does not exist")
        return None
    
    try:
        with open(cache_file, 'r') as f:
            cached = json.load(f)
        
        cached_time = cached.get("timestamp", 0)
        age = datetime.now().timestamp() - cached_time
        if age < cache_ttl:
            logger.info(f"Using cached data (age: {age:.0f}s)")
            return cached.get("data")
        else:
            logger.debug(f"Cache expired (age: {age:.0f}s)")
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in cache file: {e}")
    except Exception as e:
        logger.error(f"Error reading cache: {e}")
    
    return None


def save_cache(data: Dict, config: Dict = None):
    """Save results to cache."""
    if config is None:
        config = _get_config()
    
    cache_cfg = get_cache_config(config)
    cache_file = cache_cfg.get("file", CACHE_FILE)
    
    if not cache_cfg.get("enabled", True):
        logger.debug("Cache disabled, not saving")
        return
    
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)
        with open(cache_file, 'w') as f:
            json.dump({
                "timestamp": datetime.now().timestamp(),
                "data": data
            }, f)
        logger.info(f"Cached results to {cache_file}")
    except Exception as e:
        logger.error(f"Error saving cache: {e}")


def get_all_spend(force_refresh: bool = False) -> Dict:
    """Fetch spend from all configured providers."""
    logger.info("Fetching spend from all providers")
    config = _get_config()
    
    # Check cache first
    if not force_refresh:
        cached = load_cache()
        if cached:
            return cached
    
    # Get API keys from config or environment (env vars take precedence)
    api_keys = {
        "openai": get_api_key(config, "openai", "OPENAI_API_KEY"),
        "anthropic": get_api_key(config, "anthropic", "ANTHROPIC_API_KEY"),
        "openrouter": get_api_key(config, "openrouter", "OPENROUTER_API_KEY"),
    }
    
    # Get settings
    settings = get_settings(config)
    days = settings.get("default_days", 30)
    
    results = {}
    
    # Fetch from each provider
    if api_keys.get("openai"):
        results["openai"] = get_openai_spend(api_keys["openai"], days)
    
    if api_keys.get("anthropic"):
        results["anthropic"] = get_anthropic_spend(api_keys["anthropic"], days)
    
    if api_keys.get("openrouter"):
        results["openrouter"] = get_openrouter_spend(api_keys["openrouter"], days)
    
    # Cursor (placeholder)
    results["cursor"] = get_cursor_spend()
    
    # Calculate total
    total = 0
    for provider, data in results.items():
        if data and "total" in data and "error" not in data:
            total += data.get("total", 0)
    
    results["_total"] = round(total, 2)
    results["_currency"] = "USD"
    results["_date"] = datetime.now().strftime("%Y-%m-%d")
    
    # Cache results
    save_cache(results, config)
    
    logger.info(f"Total spend: {results['_total']}")
    return results


def format_spend(results: Dict) -> str:
    """Format spend data as a readable string."""
    lines = [
        f"AI Spend ({results.get('_date', 'N/A')})",
        f"Total: ${results.get('_total', 0):.2f} {results.get('_currency', 'USD')}",
        ""
    ]
    
    providers = {
        "openai": "OpenAI",
        "anthropic": "Anthropic", 
        "openrouter": "OpenRouter",
        "cursor": "Cursor"
    }
    
    for key, name in providers.items():
        data = results.get(key, {})
        if "error" in data:
            lines.append(f"{name}: Error - {data['error']}")
        else:
            total = data.get("total", 0)
            note = data.get("note", "")
            note_str = f" ({note})" if note else ""
            lines.append(f"{name}: ${total:.2f}{note_str}")
    
    return "\n".join(lines)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="AI Spend Tracker")
    parser.add_argument("--refresh", action="store_true", help="Force refresh cache")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    results = get_all_spend(force_refresh=args.refresh)
    
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(format_spend(results))


if __name__ == "__main__":
    main()
