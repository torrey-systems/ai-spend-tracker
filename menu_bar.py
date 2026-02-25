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
    """Get all API keys from keychain and env vars."""
    keys = {}
    
    # Check keychain for each provider
    providers = [
        ("openai", "openai_api_key"),
        ("anthropic", "anthropic_api_key"), 
        ("openrouter", "openrouter_api_key"),
    ]
    
    for provider, keyring_name in providers:
        # First try keychain
        keychain_value = get_key_from_keyring(keyring_name)
        if keychain_value:
            keys[provider] = keychain_value
        # Then try env var
        env_var = f"{provider.upper()}_API_KEY"
        env_value = os.getenv(env_var)
        if env_value and not keys.get(provider):
            keys[provider] = env_value
    
    return keys


def check_api_keys_configured() -> bool:
    """Check if any API keys are configured."""
    return bool(get_all_api_keys())


def set_env_from_keys(keys: Dict[str, str]) -> None:
    """Set environment variables from keys for spend.py to use."""
    # Clear existing
    for var in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OPENROUTER_API_KEY"]:
        os.environ.pop(var, None)
    # Set new keys
    if keys.get("openai"):
        os.environ["OPENAI_API_KEY"] = keys["openai"]
    if keys.get("anthropic"):
        os.environ["ANTHROPIC_API_KEY"] = keys["anthropic"]
    if keys.get("openrouter"):
        os.environ["OPENROUTER_API_KEY"] = keys["openrouter"]


class SettingsWindow:
    """Modal settings window using tkinter for proper input fields."""
    
    def __init__(self, current_keys: Dict[str, str]):
        self.current_keys = current_keys
        self.saved = False
        self.new_keys = {}
    
    def show(self) -> Optional[Dict[str, str]]:
        """Show the settings modal and return new keys if saved."""
        # Use osascript dialog - more reliable on macOS
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
        """Show settings dialog - user friendly sequential dialogs."""
        new_keys = {}
        
        # Helper to show dialog for a single key
        def ask_key(provider, name, url, current):
            prompt = f"Enter your {name} API key:\n\nGet it at: {url}\n\nLeave empty to remove."
            script = f'''
set userInput to display dialog "{prompt}" default answer "{current}" with title "AI Spend Tracker - {name}" with icon note buttons {{"Skip", "Save"}} default button "Save"
set buttonReturned to button returned of userInput
if buttonReturned is "Save" then
    return text returned of userInput
else
    return "SKIP"
end if
'''
            result = subprocess.run(["osascript", "-e", script], 
                                   capture_output=True, text=True)
            if result.returncode == 0:
                val = result.stdout.strip()
                if val and val != "SKIP":
                    return val
            return None
        
        # Ask for each provider one at a time
        openai_key = ask_key("openai", "OpenAI", "https://platform.openai.com/api-keys", 
                            self.current_keys.get("openai", ""))
        if openai_key:
            new_keys["openai"] = openai_key
            save_key_to_keyring("openai_api_key", openai_key)
        
        anthropic_key = ask_key("anthropic", "Anthropic", "https://console.anthropic.com/settings/keys",
                               self.current_keys.get("anthropic", ""))
        if anthropic_key:
            new_keys["anthropic"] = anthropic_key
            save_key_to_keyring("anthropic_api_key", anthropic_key)
        
        openrouter_key = ask_key("openrouter", "OpenRouter", "https://openrouter.ai/settings",
                                self.current_keys.get("openrouter", ""))
        if openrouter_key:
            new_keys["openrouter"] = openrouter_key
            save_key_to_keyring("openrouter_api_key", openrouter_key)
        
        return new_keys if new_keys else None


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
        
        # Initial data fetch (async)
        if self.keys_configured:
            def initial_load():
                import time
                time.sleep(0.5)
                self.update_spend()
            threading.Thread(target=initial_load, daemon=True).start()
    
    def _build_menu(self):
        """Build the dropdown menu."""
        # Get current keys to determine what to show
        keys = get_all_api_keys()
        
        # Build menu as a list
        menu_items = [
            rumps.MenuItem("Refresh Now", callback=self.refresh),
            None,
        ]
        
        # Show all providers with their status
        provider_display = {
            "openai": "OpenAI",
            "anthropic": "Anthropic", 
            "openrouter": "OpenRouter",
        }
        
        for key, name in provider_display.items():
            if keys.get(key):
                menu_items.append(rumps.MenuItem(f"{name}: --", callback=None))
            else:
                menu_items.append(rumps.MenuItem(f"{name}: Not configured", callback=None))
        
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
            
            # Update title - show total or error
            if total and total > 0:
                self.title = f"AI: ${total:.2f}"
            elif "error" in str(results.get("openai", {})).lower():
                self.title = "AI: 🔑"  # Auth error
            else:
                self.title = "AI: $0.00"
            
            # Update menu items (need to run on main thread)
            self._update_menu_items(results)
                    
        except Exception as e:
            self.title = "AI: ⚠️"
            print(f"Error updating spend: {e}")
    
    def _update_menu_items(self, results):
        """Update menu items with spend data."""
        try:
            # Use rumps.do to update menu on main thread
            def do_update():
                try:
                    # Get current menu items
                    menu_dict = {}
                    for item in self.menu:
                        if hasattr(item, 'title') and item.title:
                            for provider in ["OpenAI", "Anthropic", "OpenRouter"]:
                                if item.title.startswith(provider + ":"):
                                    menu_dict[provider] = item
                                    break
                    
                    # Update each provider
                    providers_map = {
                        "OpenAI": "openai",
                        "Anthropic": "anthropic", 
                        "OpenRouter": "openrouter",
                    }
                    
                    now = datetime.now().strftime("%H:%M")
                    
                    for menu_name, api_name in providers_map.items():
                        if menu_name in menu_dict:
                            item = menu_dict[menu_name]
                            data = results.get(api_name, {})
                            if "error" in data:
                                item.title = f"{menu_name}: ⚠️ Error"
                            else:
                                amt = data.get("total", 0)
                                item.title = f"{menu_name}: ${amt:.2f}"
                    
                    # Update timestamp
                    for item in self.menu:
                        if hasattr(item, 'title') and item.title and item.title.startswith("Last updated:"):
                            item.title = f"Last updated: {now}"
                            break
                            
                except Exception as e:
                    print(f"Menu update error: {e}")
            
            rumps.do(do_update)
            
        except Exception as e:
            print(f"Error in _update_menu_items: {e}")
            self.title = "AI: ⚠️"
            print(f"Error updating spend: {e}")
    
    @rumps.clicked("Refresh Now")
    def refresh(self, _):
        """Manually refresh spend data (async to avoid UI lock)."""
        def fetch_and_update():
            import time
            time.sleep(0.1)  # Small delay to let menu close
            self.update_spend()
        
        threading.Thread(target=fetch_and_update, daemon=True).start()
    
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
            
            # Rebuild menu with new state
            self._build_menu()
            
            # Refresh data if we have keys (async)
            if self.keys_configured:
                def do_refresh():
                    import time
                    time.sleep(0.3)
                    self.update_spend()
                    self.start_auto_refresh()
                threading.Thread(target=do_refresh, daemon=True).start()
    
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
