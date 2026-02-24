#!/usr/bin/env python3
"""
AI Spend Tracker - Menu Bar App
A macOS menu bar application to track spending across AI providers.

Requires: pip install rumps
"""

import os
import sys
import threading
import rumps
from datetime import datetime
import subprocess

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from spend import get_all_spend, format_spend

# App metadata
APP_NAME = "AI Spend Tracker"
APP_VERSION = "1.0.0"
APP_ICON = None  # Uses default icon; set to an .icns file path for custom icon

# Config file path
CONFIG_PATH = os.path.expanduser("~/.ai-spend-tracker.json")


def check_api_keys_configured():
    """Check if any API keys are configured in config file or environment."""
    # Check environment variables first
    env_keys = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OPENROUTER_API_KEY"]
    for key in env_keys:
        if os.getenv(key):
            return True
    
    # Check config file
    if os.path.exists(CONFIG_PATH):
        try:
            import json
            with open(CONFIG_PATH, 'r') as f:
                config = json.load(f)
            providers = config.get("providers", {})
            for provider in providers.values():
                if provider.get("api_key") and provider["api_key"] != "sk-your-openai-key-here":
                    return True
        except Exception:
            pass
    
    return False


class AISpendTracker(rumps.App):
    """Main menu bar application for AI Spend Tracker."""
    
    def __init__(self):
        self.keys_configured = check_api_keys_configured()
        
        # Show friendly message if no keys configured
        title = "⚙️ Setup Required" if not self.keys_configured else "AI: $0.00"
        
        super(AISpendTracker, self).__init__(
            title,
            icon=None,  # Uses system menu bar icon
            template=True  # Enables proper menu bar template icon
        )
        
        self.refresh_timer = None
        self.refresh_interval = 300  # 5 minutes
        
        # Build the menu
        self._build_menu()
        
        # Set up keyboard shortcut for quit (Cmd+Q is automatic with rumps)
        self.setup_quit_shortcut()
        
        # Initial data fetch
        if self.keys_configured:
            self.update_spend()
            # Start auto-refresh
            self.start_auto_refresh()
        else:
            self._show_setup_message()
    
    def _show_setup_message(self):
        """Show setup instructions when no keys are configured."""
        self.menu[2].title = "OpenAI: ⚙️ Needs Setup"
        self.menu[3].title = "Anthropic: ⚙️ Needs Setup"  
        self.menu[4].title = "OpenRouter: ⚙️ Needs Setup"
        self.menu[5].title = "Cursor: ⚙️ Needs Setup"
        self.menu[7].title = "Please configure API keys"
    
    def _build_menu(self):
        """Build the dropdown menu."""
        self.menu = [
            rumps.MenuItem("Refresh Now", callback=self.refresh),
            None,
            rumps.MenuItem("OpenAI: --", callback=None),
            rumps.MenuItem("Anthropic: --", callback=None),
            rumps.MenuItem("OpenRouter: --", callback=None),
            rumps.MenuItem("Cursor: --", callback=None),
            None,
            rumps.MenuItem("Last updated: --", callback=None),
            None,
            rumps.MenuItem("Setup Instructions", callback=self.show_setup_instructions),
            rumps.MenuItem("Open Config File", callback=self.open_config_file),
            None,
            rumps.MenuItem("Settings", callback=self.open_settings),
            None,
            rumps.MenuItem("About", callback=self.show_about),
            None,
            rumps.MenuItem("Quit", callback=lambda _: self.terminate())
        ]
    
    def setup_quit_shortcut(self):
        """Set up keyboard shortcut for quitting."""
        # Cmd+Q is built into the menu item automatically
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
            menu_items[5].title = self._format_provider("Cursor", results.get("cursor", {}))
            
            # Update timestamp
            now = datetime.now().strftime("%H:%M:%S")
            menu_items[7].title = f"Last updated: {now}"
            
        except Exception as e:
            # Show friendly error message instead of raw error
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
            # Make error messages more user-friendly
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
            import subprocess
            subprocess.run([
                "osascript", "-e",
                f'display notification "{message}" with title "AI Spend Tracker"'
            ], capture_output=True)
        except Exception:
            pass  # Notifications may not be available
    
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
   Note: Need usage API access

2️⃣  ANTHROPIC  
   Get key at: https://console.anthropic.com/settings/keys

3️⃣  OPENROUTER
   Get key at: https://openrouter.ai/settings

📁 WHERE TO PUT KEYS:

Option A - Config File (recommended):
   Click "Open Config File" to edit ~/.ai-spend-tracker.json

Option B - Environment Variables:
   OPENAI_API_KEY=sk-...
   ANTHROPIC_API_KEY=sk-ant-...
   OPENROUTER_API_KEY=...

💡 TIP: You don't need all three - just add the ones you use!

After adding keys, click "Refresh Now" to update."""
        
        subprocess.run([
            "osascript", "-e",
            f'display dialog "{instructions}" with title "Setup Instructions" with icon note buttons {{"OK", "Open Config"}} default button "OK"'
        ], capture_output=True)
    
    @rumps.clicked("Open Config File")
    def open_config_file(self, _):
        """Open the config file in the default text editor."""
        config_path = os.path.expanduser("~/.ai-spend-tracker.json")
        
        # Check if config exists, if not create from example
        if not os.path.exists(config_path):
            example_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "config.example.json"
            )
            if os.path.exists(example_path):
                import shutil
                shutil.copy(example_path, config_path)
        
        # Open in default editor
        subprocess.run(["open", "-e", config_path])
    
    @rumps.clicked("Settings")
    def open_settings(self, _):
        """Open settings file location."""
        import subprocess
        config_path = os.path.expanduser("~/.ai-spend-tracker.json")
        
        # Check if config exists
        if not os.path.exists(config_path):
            # Create example config
            example_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "config.example.json"
            )
            if os.path.exists(example_path):
                import shutil
                shutil.copy(example_path, config_path)
                print(f"Created config at {config_path}")
        
        # Open in default editor
        subprocess.run(["open", "-e", config_path])
    
    @rumps.clicked("About")
    def show_about(self, _):
        """Show about dialog."""
        import subprocess
        about_text = f"""AI Spend Tracker v{APP_VERSION}

Track your AI API spending across OpenAI, Anthropic, OpenRouter, and Cursor.

Configuration:
- Edit ~/.ai-spend-tracker.json to add your API keys
- Or set environment variables: OPENAI_API_KEY, ANTHROPIC_API_KEY, OPENROUTER_API_KEY

Auto-refreshes every 5 minutes."""
        
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
                # Use rumps.do to run on main thread
                rumps.do(self.update_spend)
        
        thread = threading.Thread(target=run, daemon=True)
        thread.start()
    
    def update(self):
        """Alias for update_spend for auto-refresh callback."""
        self.update_spend()


def check_api_keys():
    """Check for required API keys and warn if missing."""
    missing = []
    for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OPENROUTER_API_KEY"]:
        if not os.getenv(key):
            missing.append(key)
    
    if missing:
        print(f"Warning: Missing API keys: {', '.join(missing)}")
        print("Set them as environment variables or add to ~/.ai-spend-tracker.json")
        print("The app will show $0.00 for missing providers.")
        return False
    return True


def main():
    """Main entry point."""
    # Check for API keys
    check_api_keys()
    
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