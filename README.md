# AI Spend Tracker

Menu bar app for tracking AI API spending across OpenAI, Anthropic, OpenRouter, and Cursor.

## Setup

```bash
# Install dependencies
pip install requests keyring

# Set API keys (or use environment variables)
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENROUTER_API_KEY="sk-or-..."
```

## Usage

```bash
# Run once to see spend
python spend.py

# Or run the menu bar app
python menu_bar.py
```

## API Keys

Keys are read from environment variables. For menu bar use, you can also use macOS Keychain.

Required env vars:
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `OPENROUTER_API_KEY`

## Features

- Fetches usage/spend from multiple AI providers
- Menu bar display with breakdown
- Local caching to reduce API calls
