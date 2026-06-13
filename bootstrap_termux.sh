#!/usr/bin/env bash

# Cyberpunk Banner
echo -e "\e[1;36m========================================================\e[0m"
echo -e "\e[1;35m       RGAI SOVEREIGN SWARM NODE BOOTSTRAPPER           \e[0m"
echo -e "\e[1;36m========================================================\e[0m"
echo -e "\e[1;33m[Target Node] Initializing secure low-RAM parallel agent...\e[0m"

# Verify termux or standard bash environment
if [ -d "$HOME/.termux" ] || [ -f "/system/bin/app_process" ]; then
    echo "[Env Check] Android/Termux environment detected."
    IS_TERMUX=true
else
    echo "[Env Check] Standard Linux environment detected."
    IS_TERMUX=false
fi

# Step 1: Install Python if missing
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "[Provisioning] Python not found. Installing..."
    if [ "$IS_TERMUX" = true ]; then
        pkg update -y && pkg install python -y
    else
        sudo apt-get update && sudo apt-get install python3 -y
    fi
else
    echo "[Env Check] Python is already installed."
fi

# Determine python command
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
else
    PYTHON_CMD="python"
fi

# Step 2: Create directory for node runtime
mkdir -p "$HOME/rgai_swarm"
cd "$HOME/rgai_swarm" || exit

# Step 3: Fetch Node Files from Discovery Server URL
# Set default discovery URL or use argument
DISCOVERY_URL="${1:-https://polite-bees-tan.loca.lt}"
echo "[Sync] Downloading swarm components from $DISCOVERY_URL..."

# Helper curl command with bypass headers
curl_get() {
    curl -s -L -H "bypass-tunnel-reminder: true" -H "User-Agent: RGAIBootstrap/1.0" "$1"
}

curl_get "$DISCOVERY_URL/download/rgai_phone_node.py" > rgai_phone_node.py
curl_get "$DISCOVERY_URL/download/ternary_math_compressor.py" > ternary_math_compressor.py

if [ ! -s rgai_phone_node.py ] || [ ! -s ternary_math_compressor.py ]; then
    echo -e "\e[1;31m[Error] Failed to download swarm components. Check your internet connection or discovery URL.\e[0m"
    exit 1
fi

echo "[Sync] Successfully fetched components."

# Step 4: Run Node Engine
echo -e "\e[1;32m[Success] Swarm environment configured successfully.\e[0m"
echo "[Launch] Initializing low-RAM compute node..."
export DISCOVERY_SERVER_URL="$DISCOVERY_URL"
export RGAI_NODE_ID="RGAI_MOBILE_NODE_$(od -An -N2 -i /dev/urandom | tr -d ' ')"
$PYTHON_CMD -u rgai_phone_node.py
