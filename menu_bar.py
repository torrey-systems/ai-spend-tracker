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
APP_VERSION = "1.2.0"
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
    except Exception as e:
        print(f"Error getting key from keyring: {e}")
        return None


def save_key_to_keyring(key_name: str, value: str) -> bool:
    """Save a key to macOS Keychain. Returns True on success."""
    try:
        import keyring
        keyring.set_password(KEYRING_SERVICE, key_name, value)
        return True
    except Exception as e:
        print(f"Warning: Could not save to Keychain: {e}")
        return False


def delete_key_from_keyring(key_name: str) -> None:
    """Delete a key from macOS Keychain."""
    try:
        import keyring
        keyring.delete_password(KEYRING_SERVICE, key_name)
    except Exception:
        pass


def get_all_api_keys() -> Dict[str, str]:
    """Get all API keys from keychain only (simplified)."""
    keys = {}
    
    # Only check OpenAI keychain for now (simplified)
    keyring_name = "openai_api_key"
    keychain_value = get_key_from_keyring(keyring_name)
    if keychain_value:
        keys["openai"] = keychain_value
    
    # Also check environment variables as fallback
    env_value = os.getenv("OPENAI_API_KEY")
    if env_value and not keys.get("openai"):
        keys["openai"] = env_value
    
    return keys


def check_api_keys_configured() -> bool:
    """Check if any API keys are configured."""
    return bool(get_all_api_keys())


def set_env_from_keys(keys: Dict[str, str]) -> None:
    """Set environment variables from keys for spend.py to use."""
    if keys.get("openai"):
        os.environ["OPENAI_API_KEY"] = keys["openai"]


class SettingsWindow:
    """Modal settings window using tkinter for proper input fields."""
    
    def __init__(self, current_keys: Dict[str, str]):
        self.current_keys = current_keys
        self.saved = False
        self.new_keys = {}
    
    def show(self) -> Optional[Dict[str, str]]:
        """Show the settings modal and return new keys if saved."""
        # Import tkinter here to avoid issues if not available
        try:
            import tkinter as tk
            from tkinter import ttk
        except ImportError:
            # Fallback to osascript if tkinter not available
            return self._show_osascript_dialog()
        
        # Create the modal window
        root = tk.Tk()
        root.title("AI Spend Tracker - Settings")
        root.geometry("500x250")
        root.resizable(False, False)
        
        # Center the window
        root.update_idletasks()
        x = (root.winfo_screenwidth() // 2) - (250)
        y = (root.winfo_screenheight() // 2) - (125)
        root.geometry(f"500x250+{x}+{y}")
        
        # Make it modal
        root.transient()
        root.grab_set()
        
        # Result variable
        result = {"saved": False, "openai_key": ""}
        
        # Create main frame
        main_frame = ttk.Frame(root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="🔑 OpenAI API Key", 
                               font=("Helvetica", 14, "bold"))
        title_label.pack(pady=(0, 10))
        
        # Description
        desc_label = ttk.Label(main_frame, 
            text="Enter your OpenAI API key to track spending.\n"
                 "Get your key at: https://platform.openai.com/api-keys\n"
                 "Your key is stored securely in macOS Keychain.",
            justify=tk.CENTER)
        desc_label.pack(pady=(0, 15))
        
        # Input frame
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(input_frame, text="OpenAI API Key:").pack(anchor=tk.W)
        
        # Entry field for API key
        api_key_var = tk.StringVar(value=self.current_keys.get("openai", ""))
        api_key_entry = ttk.Entry(input_frame, textvariable=api_key_var, 
                                   width=50, show="*")
        api_key_entry.pack(fill=tk.X, pady=(5, 0))
        api_key_entry.focus()
        
        # Show/hide toggle
        def toggle_show():
            if show_var.get():
                api_key_entry.config(show="")
            else:
                api_key_entry.config(show="*")
        
        show_var = tk.BooleanVar(value=False)
        show_check = ttk.Checkbutton(input_frame, text="Show key", 
                                      variable=show_var, command=toggle_show)
        show_check.pack(anchor=tk.W, pady=(5, 0))
        
        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(20, 0))
        
        def on_save():
            key = api_key_var.get().strip()
            if key:
                # Save to keychain
                if save_key_to_keyring("openai_api_key", key):
                    result["saved"] = True
                    result["openai_key"] = key
                    root.destroy()
                else:
                    tk.messagebox.showerror("Error", "Failed to save to Keychain")
            else:
                # User entered empty - clear the key
                delete_key_from_keyring("openai_api_key")
                result["saved"] = True
                result["openai_key"] = ""
                root.destroy()
        
        def on_cancel():
            root.destroy()
        
        # Buttons
        ttk.Button(button_frame, text="Cancel", command=on_cancel).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Save", command=on_save, 
                   default=tk.ACTIVE).pack(side=tk.RIGHT, padx=5)
        
        # Handle enter key
        def handle_return(event):
            on_save()
            return "break"
        
        api_key_entry.bind("<Return>", handle_return)
        
        # Run the modal
        root.mainloop()
        
        if result["saved"]:
            if result["openai_key"]:
                return {"openai": result["openai_key"]}
            else:
                return {}  # Empty means cleared
        return None
    
    def _show_osascript_dialog(self) -> Optional[Dict[str, str]]:
        """Fallback to osascript dialog if tkinter not available."""
        current_key = self.current_keys.get("openai", "")
        
        script = f'''display dialog "Enter your OpenAI API Key:

Get your key at: https://platform.openai.com/api-keys

Your key will be stored securely in macOS Keychain.

Leave empty to clear the stored key." default answer "{current_key}" with title "AI Spend Tracker - Settings" with icon note buttons {{"Cancel", "Save"}} default button "Save"'''
        
        result = subprocess.run(["osascript", "-e", script], 
                               capture_output=True, text=True)
        
        if result.returncode != 0:
            return None
        
        # Parse the response - osascript returns button name
        if "Save" not in result.stdout:
            return None
        
        # The default answer is returned, need to extract it
        # Use a different approach to get the input
        script2 = f'''set userInput to text returned of (display dialog "Enter your OpenAI API Key:" default answer "{current_key}" hidden answer true with title "API Key" buttons {{"Cancel", "Save"}} default button "Save")'''
        
        result2 = subprocess.run(["osascript", "-e", script2], 
                               capture_output=True, text=True)
        
        if result2.returncode == 0:
            key = result2.stdout.strip()
            if key:
                save_key_to_keyring("openai_api_key", key)
                return {"openai": key}
            else:
                # Empty input - clear
                delete_key_from_keyring("openai_api_key")
                return {}
        
        return None


class AISpendTracker(rumps.App):
    """Main menu bar application for AI Spend Tracker."""
    
    def __init__(self):
        # Load existing keys first
        self.keys_configured = check_api_keys_configured()
        
        # Set environment variables from existing keys
        if self.keys_configured:
            existing_keys = get_all_api_keys()
            set_env_from_keys(existing_keys)
        
        # Show status based on configuration
        if self.keys_configured:
            title = "AI: $0.00"
        else:
            title = "⚙️ Setup"
        
        super(AISpendTracker, self).__init__(
            title,
            icon=None,
            template=True
        )
        
        self.refresh_timer = None
        self.refresh_interval = 300  # 5 minutes
        
        # Build the menu
        self._build_menu()
        
        # Initial data fetch
        if self.keys_configured:
            self.update_spend()
            self.start_auto_refresh()
    
    def _build_menu(self):
        """Build the dropdown menu."""
        # Get current keys to determine what to show
        keys = get_all_api_keys()
        
        # Build menu as a list
        menu_items = [
            rumps.MenuItem("Refresh Now", callback=self.refresh),
            None,
        ]
        
        # Only show OpenAI if configured
        if keys.get("openai"):
            menu_items.append(rumps.MenuItem("OpenAI: --", callback=None))
        else:
            menu_items.append(rumps.MenuItem("OpenAI: Not configured", callback=None))
        
        menu_items.extend([
            None,
            rumps.MenuItem("Last updated: --", callback=None),
            None,
            rumps.MenuItem("⚙️ Settings...", callback=self.open_settings),
            None,
            rumps.MenuItem("About", callback=self.show_about),
            None,
            rumps.MenuItem("Quit", callback=lambda _: self.terminate())
        ])
        
        # Set the menu
        self.menu = menu_items
    
    def update_spend(self):
        """Fetch and display current spend from all providers."""
        try:
            results = get_all_spend()
            
            total = results.get("_total", 0)
            
            # Only show spend if we have data
            if total and total > 0:
                self.title = f"AI: ${total:.2f}"
            else:
                self.title = "AI: $0.00"
            
            # Update menu items
            for item in self.menu:
                if hasattr(item, 'title') and item.title and item.title.startswith("OpenAI:"):
                    if "error" in results.get("openai", {}):
                        error_msg = results["openai"].get("error", "")
                        if "401" in error_msg or "unauthorized" in error_msg.lower():
                            item.title = "OpenAI: 🔑 Invalid key"
                        else:
                            item.title = "OpenAI: ⚠️ Error"
                    else:
                        openai_total = results.get("openai", {}).get("total", 0)
                        item.title = f"OpenAI: ${openai_total:.2f}"
                    break
            
            # Update timestamp
            for item in self.menu:
                if hasattr(item, 'title') and item.title and item.title.startswith("Last updated:"):
                    now = datetime.now().strftime("%H:%M:%S")
                    item.title = f"Last updated: {now}"
                    break
                    
        except Exception as e:
            error_str = str(e).lower()
            if "connection" in error_str or "timeout" in error_str:
                self.title = "AI: ⚠️"
            elif "unauthorized" in error_str or "401" in error_str or "api key" in error_str:
                self.title = "AI: 🔑"
            else:
                self.title = "AI: ⚠️"
            
            print(f"Error updating spend: {e}")
    
    @rumps.clicked("Refresh Now")
    def refresh(self, _):
        """Manually refresh spend data."""
        self.update_spend()
    
    @rumps.clicked("⚙️ Settings...")
    def open_settings(self, _):
        """Open settings modal."""
        current_keys = get_all_api_keys()
        
        settings_window = SettingsWindow(current_keys)
        new_keys = settings_window.show()
        
        if new_keys is not None:
            # Keys were saved or cleared - set environment variables
            if new_keys:
                set_env_from_keys(new_keys)
                self.keys_configured = True
            else:
                # Keys were cleared
                self.keys_configured = False
                # Clear env var
                os.environ.pop("OPENAI_API_KEY", None)
            
            # Rebuild menu with new state
            self._build_menu()
            
            # Refresh data if we have keys
            if self.keys_configured:
                self.update_spend()
                self.start_auto_refresh()
    
    @rumps.clicked("About")
    def show_about(self, _):
        """Show about dialog."""
        about_text = f"""AI Spend Tracker v{APP_VERSION}

Track your OpenAI API spending.

🔐 SECURITY: Your API key is stored securely in macOS Keychain.

⏱️ Auto-refreshes every 5 minutes."""
        
        subprocess.run([
            "osascript", "-e",
            f'display dialog "{about_text}" with title "About AI Spend Tracker" with icon note buttons {{"OK"}}'
        ])
    
    def start_auto_refresh(self):
        """Start background thread for auto-refresh."""
        # Stop existing timer if any
        if hasattr(self, 'refresh_timer') and self.refresh_timer:
            self.refresh_timer.cancel()
        
        def run():
            import time
            while True:
                time.sleep(self.refresh_interval)
                rumps.do(self.update_spend)
        
        thread = threading.Thread(target=run, daemon=True)
        thread.start()


def check_api_keys():
    """Check for required API keys and warn if missing."""
    keys = get_all_api_keys()
    if not keys:
        print("No API keys configured.")
        print("Run the app and click 'Settings...' to add your API key.")
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
