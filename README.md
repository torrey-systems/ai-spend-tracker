# AI Spend Tracker

<p align="center">
  <img src="https://img.shields.io/pypi/v/ai-spend-tracker" alt="PyPI Version">
  <img src="https://img.shields.io/pypi/l/ai-spend-tracker" alt="License">
  <img src="https://img.shields.io/pypi/pyversions/ai-spend-tracker" alt="Python Versions">
</p>

A macOS menu bar application to track your AI API spending across OpenAI, Anthropic, OpenRouter, and Cursor — all in one glance.

## Features

- 📊 **Real-time tracking** - See your total AI spend at a glance in the menu bar
- 🔄 **Auto-refresh** - Automatically updates every 5 minutes
- 🎯 **Per-provider breakdown** - See exactly how much you're spending on each provider
- ⚙️ **Easy configuration** - Use environment variables or a config file
- 🔔 **Error notifications** - Get notified when something goes wrong
- 📝 **CLI also available** - Run from the command line if you prefer

## Installation

### Quick Install (pip)

```bash
pip install ai-spend-tracker
```

### Development Install

```bash
# Clone the repository
git clone https://github.com/yourusername/ai-spend-tracker.git
cd ai-spend-tracker

# Install in development mode
pip install -e .
```

## Configuration

### Option 1: Environment Variables

Set your API keys as environment variables:

```bash
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENROUTER_API_KEY="sk-or-..."
```

### Option 2: Config File

Create a `~/.ai-spend-tracker.json` file:

```json
{
  "providers": {
    "openai": {
      "api_key": "sk-...",
      "org_id": "org-..."  // optional
    },
    "anthropic": {
      "api_key": "sk-ant-..."
    },
    "openrouter": {
      "api_key": "sk-or-..."
    }
  },
  "cache": {
    "enabled": true,
    "ttl_seconds": 300
  },
  "settings": {
    "default_days": 30
  }
}
```

You can also copy the example config:

```bash
cp config.example.json ~/.ai-spend-tracker.json
```

## Usage

### Menu Bar App (Recommended)

```bash
ai-spend-tracker
```

Or run directly:

```bash
python menu_bar.py
```

This will add an icon to your menu bar showing your total AI spend. Click to see a breakdown by provider.

### Command Line

```bash
# See spend for all providers
ai-spend-tracker-cli

# Or use Python directly
python spend.py

# Force refresh cache
python spend.py --refresh

# Output as JSON
python spend.py --json

# Enable debug logging
python spend.py --debug
```

## Menu Bar Interface

```
┌─────────────────────────────┐
│ AI: $127.50                 │  ← Total in menu bar
├─────────────────────────────┤
│ 🔄 Refresh Now              │
├─────────────────────────────┤
│ OpenAI: $45.20              │
│ Anthropic: $62.30           │
│ OpenRouter: $20.00          │
│ Cursor: --                  │
├─────────────────────────────┤
│ Last updated: 14:32:05      │
├─────────────────────────────┤
│ ⚙️ Settings                 │
│ ❓ About                    │
├─────────────────────────────┤
│ Quit                        │
└─────────────────────────────┘
```

## Keyboard Shortcuts

- **Cmd+Q** - Quit the application
- **Click menu bar icon** - View detailed breakdown

## Supported Providers

| Provider | API Support | Notes |
|----------|-------------|-------|
| OpenAI | ✅ Full | Requires API key |
| Anthropic | ⚠️ Limited | API access limited |
| OpenRouter | ✅ Full | Requires API key |
| Cursor | ❌ None | No public API available |

## Troubleshooting

### "AI: Error" displayed
- Check that your API keys are set correctly
- Run with `--debug` to see detailed error messages
- Check the macOS Notification Center for error alerts

### No data showing
- Verify API keys are set (environment or config file)
- Ensure you have API access for the providers
- Check console output for errors

### Menu bar icon missing
- Ensure you're running on macOS
- Check that `rumps` is installed correctly

## Development

### Running Tests

```bash
pytest tests/
```

### Project Structure

```
ai-spend-tracker/
├── menu_bar.py       # Menu bar application
├── spend.py          # Core spend tracking logic
├── config.py         # Configuration loader
├── errors.py         # Error handling
├── config.example.json  # Example configuration
├── pyproject.toml    # Package configuration
└── README.md         # This file
```

## License

MIT License - See LICENSE file for details.

## Acknowledgments

- Built with [rumps](https://github.com/jaredks/rumps) for macOS menu bar
- Inspired by similar projects like [OpenAIBar](https://github.com/IntrinsicLabsAI/OpenAIBar) and [OpenUsage](https://www.openusage.ai/)