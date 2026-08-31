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

## GitHub Relay
Optional. If enabled, live Elite state is uploaded to a repository chosen by the user.

## Disclaimer
EDGPT is an unofficial community project and is not affiliated with Frontier Developments or OpenAI.
Third-party software included or downloaded separately remains subject to its own license.
