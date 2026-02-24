#!/usr/bin/env python3
"""
AI Spend Tracker - Fetches spend from multiple AI API providers.
"""

import os
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, Optional

# Import config module for file-based configuration
from config import load_config, get_api_key, get_provider_config, get_cache_config, get_settings

# Load config at module level
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


def get_openai_spend(api_key: str, days: int = 30) -> Optional[Dict]:
    """Fetch OpenAI usage from the API."""
    if not api_key:
        return None
    
    headers = {
        "Authorization": f"Bearer {api_key}",
    }
    if OPENAI_ORG_ID:
        headers["OpenAI-Organization"] = OPENAI_ORG_ID
    
    # Get usage for last N days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    url = f"https://api.openai.com/v1/usage?start_date={start_date.strftime('%Y-%m-%d')}&end_date={end_date.strftime('%Y-%m-%d')}&granularity=daily"
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        total_spend = 0
        for day in data.get("data", []):
            total_spend += day.get("cost", 0)
        
        return {
            "provider": "OpenAI",
            "total": round(total_spend, 4),
            "currency": "USD",
            "days": days
        }
    except Exception as e:
        return {"provider": "OpenAI", "error": str(e)}


def get_anthropic_spend(api_key: str, days: int = 30) -> Optional[Dict]:
    """Fetch Anthropic usage from the API."""
    if not api_key:
        return None
    
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01"
    }
    
    # Anthropic uses a different endpoint - might need org ID
    # This is a simplified version
    url = "https://api.anthropic.com/v1/organizations/self/usage"
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        # If we get 404, the endpoint might be different
        if response.status_code == 404:
            return {"provider": "Anthropic", "error": "API endpoint not found - may need org ID"}
        
        # Anthropic billing API is limited - we'll estimate based on credits
        # For now, return what we can
        return {
            "provider": "Anthropic",
            "total": 0,  # Would need proper billing API access
            "currency": "USD",
            "note": "API access limited",
            "days": days
        }
    except Exception as e:
        return {"provider": "Anthropic", "error": str(e)}


def get_openrouter_spend(api_key: str, days: int = 30) -> Optional[Dict]:
    """Fetch OpenRouter usage from the API."""
    if not api_key:
        return None
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://openrouter.ai",
    }
    
    # OpenRouter provides user-level usage
    url = "https://openrouter.ai/api/v1/credits"
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        total_spend = data.get("data", {}).get("total_usage", 0)
        
        return {
            "provider": "OpenRouter",
            "total": round(total_spend, 4),
            "currency": "USD",
            "days": days
        }
    except Exception as e:
        return {"provider": "OpenRouter", "error": str(e)}


def get_cursor_spend() -> Optional[Dict]:
    """Cursor doesn't have a public API. This is a placeholder."""
    # Would need to scrape or use unofficial methods
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
        return None
    
    if not os.path.exists(cache_file):
        return None
    
    try:
        with open(cache_file, 'r') as f:
            cached = json.load(f)
        
        # Check if cache is still valid
        cached_time = cached.get("timestamp", 0)
        if datetime.now().timestamp() - cached_time < cache_ttl:
            return cached.get("data")
    except:
        pass
    
    return None


def save_cache(data: Dict, config: Dict = None):
    """Save results to cache."""
    if config is None:
        config = _get_config()
    
    cache_cfg = get_cache_config(config)
    cache_file = cache_cfg.get("file", CACHE_FILE)
    
    if not cache_cfg.get("enabled", True):
        return
    
    try:
        with open(cache_file, 'w') as f:
            json.dump({
                "timestamp": datetime.now().timestamp(),
                "data": data
            }, f)
    except:
        pass


def get_all_spend(force_refresh: bool = False) -> Dict:
    """Fetch spend from all configured providers."""
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
    args = parser.parse_args()
    
    results = get_all_spend(force_refresh=args.refresh)
    
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(format_spend(results))


if __name__ == "__main__":
    main()
