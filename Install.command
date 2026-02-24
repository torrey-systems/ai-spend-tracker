#!/bin/bash
# AI Spend Tracker Installer
# Double-click this file to install and launch the app
# Created for non-technical users

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================"
echo "  AI Spend Tracker - Setup"
echo "========================================"
echo ""

# Check for Python 3
echo "Checking for Python 3..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed${NC}"
    echo ""
    echo "Please install Python 3 from https://www.python.org/downloads/"
    echo "Or use Homebrew: brew install python3"
    echo ""
    echo "Press Enter to exit..."
    read
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo -e "${GREEN}✓${NC} Found Python $PYTHON_VERSION"

# Check if we're in the right directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Install dependencies
echo ""
echo "Installing dependencies..."
python3 -m pip install --quiet requests pyyaml rumps 2>/dev/null || python3 -m pip install requests pyyaml rumps

# Check if installation succeeded
if python3 -c "import rumps" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Dependencies installed successfully"
else
    echo -e "${RED}Error: Failed to install dependencies${NC}"
    echo "Please try running: pip3 install requests pyyaml rumps"
    echo ""
    echo "Press Enter to exit..."
    read
    exit 1
fi

# Check for config file
CONFIG_FILE="$HOME/.ai-spend-tracker.json"
if [ ! -f "$CONFIG_FILE" ]; then
    echo ""
    echo -e "${YELLOW}Setting up configuration...${NC}"
    
    # Copy example config
    if [ -f "config.example.json" ]; then
        cp config.example.json "$CONFIG_FILE"
        echo -e "${GREEN}✓${NC} Created config file at ~/.ai-spend-tracker.json"
        echo ""
        echo "IMPORTANT: You need to add your API keys to the config file!"
        echo ""
        echo "How to get API keys:"
        echo "  - OpenAI: https://platform.openai.com/api-keys"
        echo "  - Anthropic: https://console.anthropic.com/settings/keys"
        echo "  - OpenRouter: https://openrouter.ai/settings"
        echo ""
        echo "Edit your config file now? (y/n)"
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            open -e "$CONFIG_FILE"
        fi
    fi
else
    echo -e "${GREEN}✓${NC} Config file already exists"
fi

# Create the launcher script
LAUNCHER_SCRIPT="$SCRIPT_DIR/run_tracker.command"
cat > "$LAUNCHER_SCRIPT" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
python3 menu_bar.py
EOF

chmod +x "$LAUNCHER_SCRIPT"

echo ""
echo "========================================"
echo -e "${GREEN}Setup Complete!${NC}"
echo "========================================"
echo ""
echo "Starting AI Spend Tracker..."
echo ""

# Small delay before launching
sleep 1

# Launch the app
python3 menu_bar.py &