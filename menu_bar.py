#!/usr/bin/env python3
"""
AI Spend Tracker - Menu Bar App
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


class AISpendTracker(rumps.App):
    def __init__(self):
        super(AISpendTracker, self).__init__("AI Spend")
        
        self.menu_title = "AI: $0.00"
        self.refresh_timer = None
        self.refresh_interval = 300  # 5 minutes
        
        # Build menu
        self.menu = [
            rumps.MenuItem("Refresh Now", callback=self.refresh),
            rumps.MenuItem("OpenAI: --"),
            rumps.MenuItem("Anthropic: --"),
            rumps.MenuItem("OpenRouter: --"),
            rumps.MenuItem("Cursor: --"),
            None,
            rumps.MenuItem("Last updated: --", callback=None),
            None,
            rumps.MenuItem("Quit", callback=lambda _: self.terminate())
        ]
        
        # Initial fetch
        self.update_spend()
        
        # Start auto-refresh
        self.start_auto_refresh()
    
    def update_spend(self):
        """Fetch and display current spend."""
        try:
            results = get_all_spend()
            
            total = results.get("_total", 0)
            self.menu_title = f"AI: ${total:.2f}"
            self.title = self.menu_title
            
            # Update menu items
            menu_items = self.menu
            menu_items[1].title = f"OpenAI: ${results.get('openai', {}).get('total', 0):.2f}"
            menu_items[2].title = f"Anthropic: ${results.get('anthropic', {}).get('total', 0):.2f}"
            menu_items[3].title = f"OpenRouter: ${results.get('openrouter', {}).get('total', 0):.2f}"
            menu_items[4].title = f"Cursor: ${results.get('cursor', {}).get('total', 0):.2f}"
            
            # Update timestamp
            now = datetime.now().strftime("%H:%M")
            menu_items[6].title = f"Last updated: {now}"
            
        except Exception as e:
            self.menu_title = "AI: Error"
            self.title = self.menu_title
            print(f"Error updating spend: {e}")
    
    @rumps.clicked("Refresh Now")
    def refresh(self, _):
        """Manually refresh spend data."""
        self.update_spend()
    
    def start_auto_refresh(self):
        """Start background thread for auto-refresh."""
        def run():
            import time
            while True:
                time.sleep(self.refresh_interval)
                rumps.do(self.update_spend)
        
        thread = threading.Thread(target=run, daemon=True)
        thread.start()


def main():
    # Check for API keys
    missing = []
    for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OPENROUTER_API_KEY"]:
        if not os.getenv(key):
            missing.append(key)
    
    if missing:
        print(f"Warning: Missing API keys: {', '.join(missing)}")
        print("Set them as environment variables or the app will show $0.00")
    
    app = AISpendTracker()
    app.run()


if __name__ == "__main__":
    main()
