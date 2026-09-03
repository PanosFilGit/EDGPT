# EDGPT 0.2.0 Beta

**A universal Elite Dangerous → AI bridge.**

EDGPT does not provide an AI chat UI. It reads Elite Dangerous data on your Windows PC and exposes that data to AI clients through **MCP** or an optional **GitHub Relay**.

```text
Elite Dangerous
      ↓
    EDGPT
   ↙     ↘
 MCP   GitHub Relay
  ↓         ↓
Any compatible AI client
```

## What it exposes

EDGPT can make the following available to an AI client:

- current system/location and route
- current ship and complete `Loadout` data
- module engineering data
- Elite live JSON sidecars such as `Status.json`, `NavRoute.json`, `Cargo.json`, `Backpack.json`, `ShipLocker.json`, `ModulesInfo.json`, `Market.json`, `Outfitting.json`, and `Shipyard.json`
- recent raw Journal events
- **all historical `Journal.*.log` files** through a local SQLite history index
- raw historical search and pagination
- optional Full Context GitHub mirror for AI clients that cannot reach local MCP

EDGPT preserves raw Frontier journal events so useful event types remain accessible even when EDGPT does not yet have a special parser for them.

## Fastest setup

### 1. Install

Download and run `EDGPT-Setup-0.2.0-beta.exe` from Releases.

No Python installation is required for the packaged Windows build.

EDGPT automatically looks for Elite data at:

```text
%USERPROFILE%\Saved Games\Frontier Developments\Elite Dangerous
```

For a standard installation, open EDGPT and the core bridge starts automatically.

### 2. Connect an AI

EDGPT runs a local Streamable HTTP MCP endpoint at:

```text
http://127.0.0.1:8000/mcp
```

If your AI client supports **local MCP directly**, it can connect to that endpoint.

If you are using a **hosted/cloud AI client that cannot directly access `localhost`**, a secure tunnel or another supported MCP transport is required between EDGPT and the AI service.

For **ChatGPT/OpenAI**, use OpenAI's official **Secure MCP Tunnel** with `tunnel-client` (`tunnel-client.exe` on Windows):

```text
Elite Dangerous
      ↓
    EDGPT
      ↓
Local MCP (127.0.0.1:8000/mcp)
      ↓
OpenAI Secure MCP Tunnel
(tunnel-client.exe)
      ↓
ChatGPT / supported OpenAI client
```

`tunnel-client.exe` is an OpenAI component and is **not bundled with the public EDGPT release**. Download/install the official OpenAI tunnel client separately and configure it to forward EDGPT's local MCP endpoint.

MCP itself is **not OpenAI-only**. Other compatible AI clients may support local MCP directly or provide their own secure/remote MCP transport. Check the connection requirements of the AI client you want to use.

If your AI cannot use EDGPT through MCP but can access GitHub, use **GitHub Relay** instead. See `QUICKSTART.md`.

### 3. Click CHECK

A healthy core installation should report:

```text
OK  Elite journal folder
OK  State server
OK  MCP server
```

Current state is also visible locally at:

```text
http://127.0.0.1:8080/state
```

## MCP tools

```text
get_elite_state
get_full_loadout
get_navroute
get_status
list_elite_live_files
get_elite_live_file
get_recent_events
search_journal
get_latest_journal_event
get_history_summary
get_raw_history_page
```

## Full Context history

On startup, EDGPT indexes historical Elite journals into a local SQLite database. The first run may take longer; later runs only add new events.

The AI does **not** receive every historical event in every prompt. MCP tools retrieve only the relevant history when needed, while raw events remain available.

## GitHub Relay

GitHub Relay is optional and **disabled by default**.

When enabled, EDGPT can publish:

```text
elite_state.json
edgpt_manifest.json
edgpt_raw/journals/...
edgpt_raw/live/...
```

to a repository you control.

**Use a private repository.** Full Context journals can contain detailed commander location and activity history.

## OpenAI Secure MCP Tunnel

EDGPT's MCP server is vendor-neutral. The OpenAI Secure MCP Tunnel is an optional transport specifically for connecting a local/private MCP server to supported OpenAI clients.

For ChatGPT/OpenAI setups that cannot access EDGPT's localhost endpoint directly, the official OpenAI `tunnel-client` (`tunnel-client.exe` on Windows) is required. EDGPT does not redistribute this third-party executable; obtain it from OpenAI and configure it separately.

Availability and account-side setup are controlled by the relevant provider and can change independently of EDGPT.

## Privacy and security

- EDGPT does not need your Frontier password.
- Core local MCP runs on `127.0.0.1` only.
- GitHub Relay is opt-in.
- Credentials entered through EDGPT are protected locally with Windows DPAPI.
- `data/`, secret `*.bin` files, and history databases must never be committed or packaged.
- Public release builds intentionally exclude third-party tunnel executables unless redistribution rights are separately verified.

Read `SECURITY.md` before publishing logs or enabling Full Context GitHub Relay.

## Building from source

Developer requirements:

- Windows 10/11 x64
- Python
- Inno Setup 6 or 7 for the installer

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\build-release.ps1
```

The release builder produces:

```text
release/installer/EDGPT-Setup-0.2.0-beta.exe
release/EDGPT-Portable.zip
release/SHA256SUMS.txt
```

It also fails the build if runtime secrets/data are found in the staged release.

## Release status

0.2.0 is a **beta**. The bridge and Full Context path are functional, but stable `1.0` should wait until the installer and bridge modes have been tested on several independent Windows PCs.

See `RELEASE_CHECKLIST.md`.

## Disclaimer

EDGPT is an unofficial community project and is not affiliated with, endorsed by, or sponsored by Frontier Developments or OpenAI.

Elite Dangerous is a trademark of Frontier Developments. Third-party services and components are subject to their own licenses and terms.

## License

See `LICENSE`.
