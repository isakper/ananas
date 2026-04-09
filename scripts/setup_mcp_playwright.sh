#!/usr/bin/env bash
set -euo pipefail

CONFIG_FILE="$HOME/.codex/config.toml"

mkdir -p "$(dirname "$CONFIG_FILE")"

if grep -q "\[mcp_servers\.playwright\]" "$CONFIG_FILE" 2>/dev/null; then
  echo "Playwright MCP already configured in $CONFIG_FILE"
  exit 0
fi

cat >> "$CONFIG_FILE" <<'TOML'

[mcp_servers.playwright]
command = "npx"
args = ["@playwright/mcp@latest"]
TOML

echo "Added Playwright MCP config to $CONFIG_FILE"
