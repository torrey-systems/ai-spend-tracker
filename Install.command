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

# Create virtual environment if needed
VENV_DIR="$SCRIPT_DIR/venv"
if [ ! -d "$VENV_DIR" ]; then
    echo ""
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
    echo -e "${GREEN}✓${NC} Virtual environment created"
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Upgrade pip
echo ""
echo "Installing dependencies..."
pip install --upgrade pip --quiet

# Install the app dependencies
pip install requests pyyaml rumps keyring --quiet
pip install keyrings.alt --quiet 2>/dev/null || true

# Check if installation succeeded
if python -c "import rumps" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Dependencies installed successfully"
else
    echo -e "${RED}Error: Failed to install dependencies${NC}"
    echo "Please try manually: python3 -m venv venv && source venv/bin/activate && pip install requests pyyaml rumps"
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

# Create the launcher script that uses the venv
LAUNCHER_SCRIPT="$SCRIPT_DIR/run_tracker.command"
cat > "$LAUNCHER_SCRIPT" << 'LAUNCHER_EOF'
#!/bin/bash
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"
source "$SCRIPT_DIR/venv/bin/activate"
python menu_bar.py
LAUNCHER_EOF

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

# Launch the app using the virtual environment
python menu_bar.py &
