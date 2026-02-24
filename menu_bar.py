#!/usr/bin/env python3
"""
AI Spend Tracker - Menu Bar App
A macOS menu bar application to track spending across AI providers.

Requires: pip install rumps keyring
"""

import os
import sys
import threading
import json
import rumps
from datetime import datetime
import subprocess
from typing import Optional, Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from spend import get_all_spend

# App metadata
APP_NAME = "AI Spend Tracker"
APP_VERSION = "1.1.0"
APP_ICON = None

# Config file path
CONFIG_PATH = os.path.expanduser("~/.ai-spend-tracker.json")

# Keyring service name
KEYRING_SERVICE = "ai-spend-tracker"


def load_json_config(path: str) -> Dict[str, Any]:
    """Load JSON config file."""
    if not os.path.exists(path):
        return {}
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception:
        return {}


def save_json_config(path: str, config: Dict[str, Any]) -> None:
    """Save config to JSON file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(config, f, indent=2)


def get_key_from_keyring(key_name: str) -> Optional[str]:
    """Get a key from macOS Keychain."""
    try:
        import keyring
        return keyring.get_password(KEYRING_SERVICE, key_name)
    except Exception:
        return None


def save_key_to_keyring(key_name: str, value: str) -> None:
    """Save a key to macOS Keychain."""
    try:
        import keyring
        keyring.set_password(KEYRING_SERVICE, key_name, value)
    except Exception as e:
        print(f"Warning: Could not save to Keychain: {e}")


def delete_key_from_keyring(key_name: str) -> None:
    """Delete a key from macOS Keychain."""
    try:
        import keyring
        keyring.delete_password(KEYRING_SERVICE, key_name)
    except Exception:
        pass


def get_all_api_keys() -> Dict[str, str]:
    """Get all API keys from config file and Keychain."""
    keys = {}
    config = load_json_config(CONFIG_PATH)
    providers = config.get("providers", {})
    
    # Map provider names to keyring key names
    keyring_keys = {
        "openai": "openai_api_key",
        "anthropic": "anthropic_api_key", 
        "openrouter": "openrouter_api_key",
        "perplexity": "perplexity_api_key",
        "mistral": "mistral_api_key",
        "cohere": "cohere_api_key",
        "xai": "xai_api_key",
        "azure_openai": "azure_openai_api_key",
        "gemini": "gemini_api_key",
    }
    
    for provider, keyring_name in keyring_keys.items():
        # First check Keychain
        keychain_value = get_key_from_keyring(keyring_name)
        if keychain_value:
            keys[provider] = keychain_value
        # Then check config file (legacy support)
        elif providers.get(provider, {}).get("api_key"):
            api_key = providers[provider]["api_key"]
            # Don't use placeholder values
            if api_key and "your-" not in api_key and api_key != "sk-your-openai-key-here":
                keys[provider] = api_key
    
    # Also check environment variables
    env_mappings = {
        "OPENAI_API_KEY": "openai",
        "ANTHROPIC_API_KEY": "anthropic",
        "OPENROUTER_API_KEY": "openrouter",
        "PERPLEXITY_API_KEY": "perplexity",
        "MISTRAL_API_KEY": "mistral",
        "COHERE_API_KEY": "cohere",
        "XAI_API_KEY": "xai",
        "AZURE_OPENAI_API_KEY": "azure_openai",
        "GEMINI_API_KEY": "gemini",
    }
    for env_var, provider in env_mappings.items():
        env_value = os.getenv(env_var)
        if env_value:
            keys[provider] = env_value
    
    return keys


def check_api_keys_configured() -> bool:
    """Check if any API keys are configured."""
    return bool(get_all_api_keys())


def set_env_from_keys(keys: Dict[str, str]) -> None:
    """Set environment variables from keys for spend.py to use."""
    env_mappings = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
        "perplexity": "PERPLEXITY_API_KEY",
        "mistral": "MISTRAL_API_KEY",
        "cohere": "COHERE_API_KEY",
        "xai": "XAI_API_KEY",
        "gemini": "GEMINI_API_KEY",
    }
    for provider, env_var in env_mappings.items():
        if keys.get(provider):
            os.environ[env_var] = keys[provider]


class SettingsWindow:
    """Modal settings window using rumps.Window."""
    
    def __init__(self, current_keys: Dict[str, str]):
        self.current_keys = current_keys
        self.saved = False
        
    def show(self) -> Optional[Dict[str, str]]:
        """Show the settings modal and return new keys if saved."""
        
        # Build the message with current values
        openai_val = self.current_keys.get("openai", "")
        anthropic_val = self.current_keys.get("anthropic", "")
        openrouter_val = self.current_keys.get("openrouter", "")
        perplexity_val = self.current_keys.get("perplexity", "")
        gemini_val = self.current_keys.get("gemini", "")
        
        # Show the settings window with input fields
        # Note: rumps.Window has limited input support, so we use a multi-line approach
        # but we'll construct a clean input string
        
        message = """🔑 Enter your API keys below. Leave blank to keep existing value.

Supported Providers:
• OpenAI (platform.openai.com)
• Anthropic (console.anthropic.com)  
• OpenRouter (openrouter.ai)
• Perplexity (perplexity.ai)
• Google Gemini (aistudio.google.com)

Your keys are stored securely in macOS Keychain.
"""
        
        # Use a single window with all fields concatenated
        input_fields = (
            f"OpenAI API Key: [{openai_val}]\n"
            f"Anthropic API Key: [{anthropic_val}]\n"
            f"OpenRouter API Key: [{openrouter_val}]\n"
            f"Perplexity API Key: [{perplexity_val}]\n"
            f"Google Gemini API Key: [{gemini_val}]"
        )
        
        # Since rumps.Window is limited, let's use osascript for a proper modal
        # This gives us native macOS look and better input handling
        
        script = '''
        set theText to text returned of (display dialog "🔑 API Keys Configuration

Enter your API keys. Leave a field empty to keep its current value.

Providers supported:
• OpenAI • Anthropic • OpenRouter • Perplexity • Gemini

Your keys will be stored securely in macOS Keychain." & return & return default answer "" with title "AI Spend Tracker - Settings" hidden answer false buttons {"Cancel", "Save"} default button "Save")
        '''
        
        # Actually, osascript doesn't support multi-field input well
        # Let's use a different approach - create a simple app with dialogs
        # For now, we'll use the environment variables approach
        
        # Use the simple approach: ask for keys one by one
        return self._show_step_by_step()
    
    def _show_step_by_step(self) -> Optional[Dict[str, str]]:
        """Show settings using sequential dialogs (more reliable)."""
        
        # First, check if user wants to configure or cancel
        response = subprocess.run([
            "osascript", "-e",
            '''display dialog "⚙️ AI Spend Tracker Settings

Would you like to:
• Add or update API keys
• Clear all stored keys
• Cancel" with title "Settings" buttons {"Add Keys", "Clear Keys", "Cancel"} default button "Add Keys"'''
        ], capture_output=True, text=True)
        
        button = response.stdout.strip()
        
        if "Cancel" in button or not button:
            return None
        
        if "Clear" in button:
            # Confirm clearing
            confirm = subprocess.run([
                "osascript", "-e",
                '''display dialog "Are you sure you want to clear all stored API keys?" with title "Confirm Clear" buttons {"Cancel", "Clear All"} default button "Cancel"'''
            ], capture_output=True, text=True)
            
            if "Clear All" in confirm.stdout:
                # Clear from keyring
                for key_name in ["openai_api_key", "anthropic_api_key", "openrouter_api_key",
                                "perplexity_api_key", "mistral_api_key", "cohere_api_key",
                                "xai_api_key", "azure_openai_api_key", "gemini_api_key"]:
                    delete_key_from_keyring(key_name)
                
                # Clear from config file if exists
                if os.path.exists(CONFIG_PATH):
                    save_json_config(CONFIG_PATH, {"providers": {}})
                
                subprocess.run([
                    "osascript", "-e",
                    'display notification "All API keys have been cleared" with title "AI Spend Tracker"'
                ], capture_output=True)
            
            return None
        
        # User wants to add keys - show help text and then ask
        new_keys = {}
        
        # Define the providers to query (matching spend.py supported providers)
        providers = [
            ("openai", "OpenAI API Key", "https://platform.openai.com/api-keys"),
            ("anthropic", "Anthropic API Key", "https://console.anthropic.com/settings/keys"),
            ("openrouter", "OpenRouter API Key", "https://openrouter.ai/settings"),
            ("perplexity", "Perplexity API Key", "https://perplexity.ai/settings"),
            ("mistral", "Mistral API Key", "https://console.mistral.ai/"),
            ("cohere", "Cohere API Key", "https://dashboard.cohere.ai/api-keys"),
            ("xai", "xAI API Key", "https://console.x.ai/"),
        ]
        
        for provider_id, provider_name, provider_url in providers:
            # Show input dialog for each key
            current = self.current_keys.get(provider_id, "")
            placeholder = "sk-..." if provider_id != "openrouter" else "..."
            
            # Use a dialog to ask for the key
            script = f'''display dialog "Enter your {provider_name}

Get your key at: {provider_url}

Leave empty to skip this provider." default answer "{current}" with title "API Key - {provider_name}" hidden answer false buttons {"Skip", "Save"} default button "Save"'''
            
            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
            
            if result.returncode == 0 and "Save" in result.stdout:
                # Extract the entered key
                # osascript returns button clicked, we need to parse better
                # Let's use a different approach
                pass
        
        # Better approach: use a single dialog with all fields
        return self._show_unified_dialog(providers)
    
    def _show_unified_dialog(self, providers) -> Optional[Dict[str, str]]:
        """Show a unified settings dialog."""
        
        # Build the AppleScript with all fields
        # We'll create a nice help message first
        help_msg = """API Keys Setup

Enter your API keys below. Keys are stored securely in macOS Keychain.

Providers:
• OpenAI - platform.openai.com
• Anthropic - console.anthropic.com
• OpenRouter - openrouter.ai  
• Perplexity - perplexity.ai
• Mistral - console.mistral.ai
• Cohere - dashboard.cohere.ai
• xAI - console.x.ai

Click 'Save' when done, or 'Cancel' to exit."""
        
        # Since we can't do multi-field input easily, let's use a shell script approach
        # that creates a temporary Python tkinter window - but tkinter isn't available
        
        # Alternative: Use the simpler approach - just show the config file location
        # and ask user to edit it, but that's what we're trying to avoid
        
        # Let's create a proper solution using the macOS system prompt
        # Actually, the best UX is to open a configuration file with all fields pre-filled
        
        # Create a temp config with current values for editing
        temp_config = {
            "providers": {
                "openai": {"api_key": self.current_keys.get("openai", "")},
                "anthropic": {"api_key": self.current_keys.get("anthropic", "")},
                "openrouter": {"api_key": self.current_keys.get("openrouter", "")},
                "perplexity": {"api_key": self.current_keys.get("perplexity", "")},
                "mistral": {"api_key": self.current_keys.get("mistral", "")},
                "cohere": {"api_key": self.current_keys.get("cohere", "")},
                "xai": {"api_key": self.current_keys.get("xai", "")},
            }
        }
        
        temp_path = "/tmp/ai-spend-tracker-temp-config.json"
        save_json_config(temp_path, temp_config)
        
        # Show the user the help and offer to open config file
        subprocess.run([
            "osascript", "-e",
            f'''display dialog "{help_msg}" with title "AI Spend Tracker - Setup" buttons {{"Open Config File", "Cancel"}} default button "Open Config File"'''
        ], capture_output=True)
        
        # Open the config file in the default editor
        subprocess.run(["open", "-e", temp_path])
        
        # Wait and ask user to copy keys to keychain
        subprocess.run([
            "osascript", "-e",
            '''display dialog "1. Edit the config file that opened
2. Copy your API keys
3. Click OK when done to save to Keychain

Or click 'Save to Keychain' to continue." with title "Instructions" buttons {"Save to Keychain", "Cancel"} default button "Save to Keychain"'''
        ], capture_output=True)
        
        # Now load the temp config and save to keychain
        temp_config = load_json_config(temp_path)
        
        new_keys = {}
        for provider, data in temp_config.get("providers", {}).items():
            api_key = data.get("api_key", "")
            if api_key and "your-" not in api_key:
                keyring_name = f"{provider}_api_key"
                save_key_to_keyring(keyring_name, api_key)
                new_keys[provider] = api_key
        
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        if new_keys:
            subprocess.run([
                "osascript", "-e",
                f'display notification "Saved {len(new_keys)} API key(s) to Keychain" with title "AI Spend Tracker"'
            ], capture_output=True)
        
        return new_keys if new_keys else None


class AISpendTracker(rumps.App):
    """Main menu bar application for AI Spend Tracker."""
    
    def __init__(self):
        self.keys_configured = check_api_keys_configured()
        
        # Set environment variables from existing keys so spend.py can use them
        if self.keys_configured:
            existing_keys = get_all_api_keys()
            set_env_from_keys(existing_keys)
        
        # Show friendly message if no keys configured
        title = "⚙️ Setup Required" if not self.keys_configured else "AI: $0.00"
        
        super(AISpendTracker, self).__init__(
            title,
            icon=None,
            template=True
        )
        
        self.refresh_timer = None
        self.refresh_interval = 300  # 5 minutes
        
        # Build the menu
        self._build_menu()
        
        # Set up keyboard shortcut for quit
        self.setup_quit_shortcut()
        
        # Initial data fetch
        if self.keys_configured:
            self.update_spend()
            self.start_auto_refresh()
        else:
            self._show_setup_message()
    
    def _show_setup_message(self):
        """Show setup instructions when no keys are configured."""
        # Update menu title to show needs setup
        self.title = "⚙️ AI Spend"
        # Show alert for setup
        self._show_setup_alert()
    
    def _show_setup_alert(self):
        """Show setup alert dialog."""
        import rumps
        rumps.alert(title="AI Spend Tracker Setup", 
                   message="No API keys configured. Click Settings to add your API keys.",
                   ok="Open Settings",
                   cancel="Later")
    
    def _build_menu(self):
        """Build the dropdown menu."""
        self.menu = [
            rumps.MenuItem("Refresh Now", callback=self.refresh),
            None,
            rumps.MenuItem("OpenAI: --", callback=None),
            rumps.MenuItem("Anthropic: --", callback=None),
            rumps.MenuItem("OpenRouter: --", callback=None),
            rumps.MenuItem("Perplexity: --", callback=None),
            rumps.MenuItem("Mistral: --", callback=None),
            rumps.MenuItem("Cohere: --", callback=None),
            rumps.MenuItem("xAI: --", callback=None),
            rumps.MenuItem("Cursor: --", callback=None),
            None,
            rumps.MenuItem("Last updated: --", callback=None),
            None,
            rumps.MenuItem("Setup Instructions", callback=self.show_setup_instructions),
            None,
            rumps.MenuItem("⚙️ Settings...", callback=self.open_settings),
            None,
            rumps.MenuItem("About", callback=self.show_about),
            None,
            rumps.MenuItem("Quit", callback=lambda _: self.terminate())
        ]
    
    def setup_quit_shortcut(self):
        """Set up keyboard shortcut for quitting."""
        pass
    
    def update_spend(self):
        """Fetch and display current spend from all providers."""
        try:
            results = get_all_spend()
            
            total = results.get("_total", 0)
            self.title = f"AI: ${total:.2f}"
            
            # Update individual provider items
            menu_items = self.menu
            menu_items[2].title = self._format_provider("OpenAI", results.get("openai", {}))
            menu_items[3].title = self._format_provider("Anthropic", results.get("anthropic", {}))
            menu_items[4].title = self._format_provider("OpenRouter", results.get("openrouter", {}))
            menu_items[5].title = self._format_provider("Perplexity", results.get("perplexity", {}))
            menu_items[6].title = self._format_provider("Mistral", results.get("mistral", {}))
            menu_items[7].title = self._format_provider("Cohere", results.get("cohere", {}))
            menu_items[8].title = self._format_provider("xAI", results.get("xai", {}))
            menu_items[9].title = self._format_provider("Cursor", results.get("cursor", {}))
            
            # Update timestamp
            now = datetime.now().strftime("%H:%M:%S")
            menu_items[11].title = f"Last updated: {now}"
            
            # Reset the title if it was showing "Setup Required"
            if not self.keys_configured:
                self.keys_configured = True
                self.title = f"AI: ${total:.2f}"
                
        except Exception as e:
            error_str = str(e).lower()
            if "connection" in error_str or "timeout" in error_str:
                friendly_message = "Network issue - will retry automatically"
            elif "unauthorized" in error_str or "401" in error_str or "api key" in error_str:
                friendly_message = "Check your API keys in Settings"
            elif "json" in error_str:
                friendly_message = "Config file issue - check Settings"
            else:
                friendly_message = "Something went wrong - will retry"
            
            self.title = "AI: ⚠️"
            self._show_error_notification(friendly_message)
            print(f"Error updating spend: {e}")
    
    def _format_provider(self, name: str, data: dict) -> str:
        """Format a provider's spend for display."""
        if "error" in data:
            error_msg = data.get("error", "Unknown error")
            if "timeout" in error_msg.lower():
                return f"{name}: ⏳ Timeout"
            elif "connection" in error_msg.lower():
                return f"{name}: 🔌 Connection Issue"
            elif "401" in error_msg or "unauthorized" in error_msg.lower():
                return f"{name}: 🔑 Invalid API Key"
            elif "403" in error_msg or "forbidden" in error_msg.lower():
                return f"{name}: 🚫 Access Denied"
            else:
                return f"{name}: ⚠️ Check Settings"
        total = data.get("total", 0)
        return f"{name}: ${total:.2f}"
    
    def _show_error_notification(self, message: str):
        """Show a notification for errors."""
        try:
            subprocess.run([
                "osascript", "-e",
                f'display notification "{message}" with title "AI Spend Tracker"'
            ], capture_output=True)
        except Exception:
            pass
    
    @rumps.clicked("Refresh Now")
    def refresh(self, _):
        """Manually refresh spend data."""
        self.update_spend()
    
    @rumps.clicked("Setup Instructions")
    def show_setup_instructions(self, _):
        """Show setup instructions dialog."""
        instructions = """📋 SETUP INSTRUCTIONS

To track your AI spending, you need to add API keys:

1️⃣  OPENAI
   Get key at: https://platform.openai.com/api-keys

2️⃣  ANTHROPIC  
   Get key at: https://console.anthropic.com/settings/keys

3️⃣  OPENROUTER
   Get key at: https://openrouter.ai/settings

4️⃣  PERPLEXITY
   Get key at: https://perplexity.ai/settings

5️⃣  GEMINI
   Get key at: https://aistudio.google.com/app/apikey

💡 TIP: You don't need all five - just add the ones you use!

After adding keys via Settings, click "Refresh Now" to update."""
        
        subprocess.run([
            "osascript", "-e",
            f'display dialog "{instructions}" with title "Setup Instructions" with icon note buttons {{"OK", "Settings"}} default button "OK"'
        ], capture_output=True)
    
    @rumps.clicked("⚙️ Settings...")
    def open_settings(self, _):
        """Open settings modal."""
        current_keys = get_all_api_keys()
        
        settings_window = SettingsWindow(current_keys)
        new_keys = settings_window.show()
        
        if new_keys:
            # Keys were saved - set environment variables and refresh
            set_env_from_keys(new_keys)
            self.keys_configured = True
            self.update_spend()
            self.start_auto_refresh()
        else:
            # Check if there are existing keys and set them as env vars
            existing_keys = get_all_api_keys()
            if existing_keys:
                set_env_from_keys(existing_keys)
                self.keys_configured = True
                self.update_spend()
                self.start_auto_refresh()
    
    @rumps.clicked("About")
    def show_about(self, _):
        """Show about dialog."""
        about_text = f"""AI Spend Tracker v{APP_VERSION}

Track your AI API spending across OpenAI, Anthropic, OpenRouter, Perplexity, and Gemini.

🔐 SECURITY: Your API keys are stored securely in macOS Keychain.

⏱️ Auto-refreshes every 5 minutes."""
        
        subprocess.run([
            "osascript", "-e",
            f'display dialog "{about_text}" with title "About AI Spend Tracker" with icon note buttons {{"OK"}}'
        ])
    
    def start_auto_refresh(self):
        """Start background thread for auto-refresh."""
        def run():
            import time
            while True:
                time.sleep(self.refresh_interval)
                rumps.do(self.update_spend)
        
        thread = threading.Thread(target=run, daemon=True)
        thread.start()
    
    def update(self):
        """Alias for update_spend for auto-refresh callback."""
        self.update_spend()


def check_api_keys():
    """Check for required API keys and warn if missing."""
    keys = get_all_api_keys()
    if not keys:
        print("No API keys configured.")
        print("Run the app and click 'Settings...' to add your API keys.")
        return False
    return True


def main():
    """Main entry point."""
    # Check dependencies
    try:
        import rumps
    except ImportError:
        print("Error: 'rumps' package not found.")
        print("Install it with: pip install rumps")
        sys.exit(1)
    
    app = AISpendTracker()
    app.run()


if __name__ == "__main__":
    main()
