# AI Spend Tracker - Development Guide

This project is being developed autonomously using a 20-minute heartbeat sprint cycle.

## Development Process

### Heartbeat Sprint (20 min)
Every 20 minutes, a sub-agent is spawned to:
1. Pick an incomplete Trello card from "To Do Today"
2. Move it to "In Progress" 
3. Do the work
4. Move it to "Done"
5. Commit to GitHub
6. Report back to the user

### Trello Board
- **Board:** https://trello.com/b/DkjNHLJH/spiny-x-ford-tasks
- **Lists:**
  - To Do Today (699be750b961e23002dc266c)
  - In Progress (699be7595a15695de7184791) 
  - Done (699be74680e424f48855e524)

### Current Tasks
- #12: Add config file support (JSON/YAML) - IN PROGRESS
- #13: Improve error handling and logging
- #14: Add unit tests
- #15: Make pip-installable
- #16: Add more providers
- #17: Add web dashboard

## Configuration

### Config File Support
The app supports JSON and YAML config files:
- `~/.ai-spend-tracker.json` or `~/.ai-spend-tracker.yaml`
- Local: `config.json`, `.ai-spend-tracker.json`, etc.
- System-wide: `/etc/ai-spend-tracker.json`

Environment variables take precedence over config file values.

### Example Config (JSON)
```json
{
  "providers": {
    "openai": {
      "api_key": "sk-...",
      "org_id": "org-..."
    },
    "anthropic": {
      "api_key": "sk-ant-..."
    }
  },
  "cache": {
    "enabled": true,
    "file": "/tmp/ai-spend-cache.json",
    "ttl_seconds": 300
  },
  "settings": {
    "default_days": 30,
    "currency": "USD"
  }
}
```

## Running

```bash
# Install dependencies
pip install requests keyring pyyaml

# Run the tracker
python spend.py

# Or run menu bar app (macOS)
python menu_bar.py
```