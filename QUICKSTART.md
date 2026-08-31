# EDGPT Quick Start

EDGPT is a bridge. It does not contain an AI chat interface.

## 1. Install

Run `EDGPT-Setup-0.2.0-beta.exe`, then open EDGPT.

For a normal Elite Dangerous install, EDGPT automatically detects `%USERPROFILE%\Saved Games\Frontier Developments\Elite Dangerous` and starts the core bridge automatically.

## 2. Local MCP

Connect a compatible AI client to `http://127.0.0.1:8000/mcp`.

No GitHub account, API key, or cloud tunnel is needed if the AI client can reach local MCP directly.

## 3. GitHub Relay

Use this when your AI cannot reach local MCP but can read GitHub repositories.

1. Create a private repository such as `yourname/EDGPT-State`.
2. Create a fine-grained GitHub token restricted to that repository with `Contents: Read and write`.
3. EDGPT → Settings → enable GitHub Relay.
4. Enter repository, branch (`main`), and token.
5. Start the bridge.
6. Connect your AI's own GitHub integration to the state repository.

EDGPT writes current state plus historical/raw Elite data. A private repository is strongly recommended.

## 4. Check it

Click CHECK in EDGPT. A healthy core install should show `OK Elite journal folder`, `OK State server`, and `OK MCP server`.

Local state: `http://127.0.0.1:8080/state`

## OpenAI Secure MCP Tunnel

OpenAI tunnel support is optional/advanced and disabled by default. It requires separately obtained tunnel-client software and account-side tunnel configuration. EDGPT's local MCP server works independently of it.
