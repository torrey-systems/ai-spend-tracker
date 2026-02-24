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

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from spend import get_all_spend, format_spend

# App metadata
APP_NAME = "AI Spend Tracker"
APP_VERSION = "1.0.0"
APP_ICON = None  # Uses default icon; set to an .icns file path for custom icon


class AISpendTracker(rumps.App):
    """Main menu bar application for AI Spend Tracker."""
    
    def __init__(self):
        super(AISpendTracker, self).__init__(
            "AI: $0.00",
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
        self.update_spend()
        
        # Start auto-refresh
        self.start_auto_refresh()
    
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
            self.title = "AI: Error"
            self._show_error_notification(f"Failed to fetch spend: {str(e)}")
            print(f"Error updating spend: {e}")
    
    def _format_provider(self, name: str, data: dict) -> str:
        """Format a provider's spend for display."""
        if "error" in data:
            return f"{name}: Error"
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