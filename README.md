# EDGPT v0.1 Alpha

Unofficial community bridge between Elite Dangerous journal/state files and AI/MCP tooling.

## Current platform
Windows only.

## Setup
1. Keep the project folder with `launcher.py`, `bin/`, and a Python virtual environment at `.venv`.
2. Install the required Python packages into `.venv`.
3. Place the supported Secure MCP tunnel client at `bin/tunnel-client.exe`.
4. Run `launcher.py`.
5. Open Settings and configure the Elite journal folder, OpenAI MCP details, and optional GitHub relay.

## Privacy / secrets
OpenAI and GitHub secrets are encrypted locally with Windows DPAPI and stored under `data/`.
Do not commit the `data/` folder.

## 🐙 GitHub Relay for ChatGPT or custom AI clients

EDGPT can optionally upload your current Elite Dangerous state to a GitHub repository you control.

This is useful for AI assistants that can read GitHub repositories but cannot connect directly to your local MCP server.

### 1. Create a state repository

On GitHub:

1. Click **New repository**
2. Give it a name such as:

   `EDGPT-State`

3. Choose **Private** if your AI integration can access private repositories.

   Public also works, but anyone could read your Elite state.

4. Enable **Add a README file** so the `main` branch exists.
5. Create the repository.

Your repository will look like:

```text
yourname/EDGPT-State

## Disclaimer
EDGPT is an unofficial community project and is not affiliated with Frontier Developments or OpenAI.
Third-party software included or downloaded separately remains subject to its own license.
