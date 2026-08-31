# 🚀 EDGPT v0.1 Alpha

**Live Elite Dangerous context for AI assistants via MCP — including ChatGPT.**

EDGPT is an unofficial community tool that connects **Elite Dangerous** live game data with AI assistants.

It reads your local Elite Dangerous Journal, Status and NavRoute files and makes that information available through **MCP (Model Context Protocol)** and, optionally, a **GitHub Relay**.

> ⚠️ **Alpha software:** EDGPT is currently under active development. Expect bugs and changes.

---

## ✨ What can EDGPT do?

EDGPT can provide AI assistants with live Elite Dangerous context, including:

- 🌌 Current star system
- 🪐 Current body
- 🛰️ Current station and docking state
- 🚀 Current ship
- ⛽ Fuel and ship information
- 🗺️ Current plotted navigation route
- 📡 Elite Dangerous `Status.json`
- 📖 Recent Journal events

This allows an AI assistant to answer questions using your current game state.

For example:

> **"Where am I right now?"**

> **"What ship am I flying?"**

> **"Check my current route."**

> **"What did I just scan?"**

---

# 📦 Installation

## Option 1 — Windows Installer (Recommended)

Download:

`EDGPT-Setup.exe`

from the latest GitHub Release.

Run the installer, then launch **EDGPT**.

Normal users should not need to install Python or create a virtual environment.

---

## Option 2 — Portable

Download:

`EDGPT-Portable.zip`

Extract the **entire folder**, then run:

`EDGPT.exe`

Do not move only `EDGPT.exe` out of the folder because EDGPT requires the accompanying files.

---

# 🎮 Elite Dangerous Setup

By default, EDGPT automatically looks for Elite Dangerous data at:

```text
%USERPROFILE%\Saved Games\Frontier Developments\Elite Dangerous
```

For a normal Elite Dangerous installation, no manual configuration should be required.

You can change the Journal location from:

**EDGPT → Settings → Elite Journal**

---

# 🤖 MCP Integration

EDGPT includes an MCP server for providing live Elite Dangerous information to compatible AI clients.

The local MCP endpoint is:

```text
http://127.0.0.1:8000/mcp
```

Available tools currently include:

```text
get_elite_state
get_navroute
get_status
get_recent_events
```

---

## ChatGPT / OpenAI

EDGPT can use the **OpenAI Secure MCP Tunnel** to make the local EDGPT MCP server available to supported OpenAI/ChatGPT environments.

Open:

**EDGPT → Settings → OpenAI MCP**

and configure your own OpenAI MCP credentials and tunnel.

Your credentials are not included with EDGPT.

> OpenAI product availability and MCP support may depend on your account, plan and current OpenAI features.

---

# 🤖 Other MCP-Compatible AI Clients

EDGPT is **not limited to ChatGPT**.

Any MCP-compatible AI client that supports EDGPT's MCP transport may potentially connect to:

```text
http://127.0.0.1:8000/mcp
```

How the connection is configured depends on the AI client.

The OpenAI Secure MCP Tunnel is specifically an OpenAI integration and is not required for clients that can connect directly to the local MCP server.

---

# 🐙 GitHub Relay

EDGPT also provides an **optional GitHub Relay**.

This is useful for AI assistants that can read a GitHub repository but cannot directly access your local MCP server.

The relay periodically uploads your Elite Dangerous state as:

```text
elite_state.json
```

to a GitHub repository that **you control**.

GitHub Relay is **disabled by default**.

---

## 1. Create a State Repository

Go to GitHub and create a new repository.

A simple name is:

```text
EDGPT-State
```

For example:

```text
yourname/EDGPT-State
```

### Private vs Public

**Private is recommended** if your AI integration can access private GitHub repositories.

If the repository is public, anyone may be able to see the Elite Dangerous state uploaded by EDGPT, including information such as your current system.

When creating the repository, enable:

**Add a README file**

so that the `main` branch is created immediately.

---

## 2. Create a GitHub Token

Create a **fine-grained GitHub Personal Access Token**.

For better security, restrict the token to only your:

```text
EDGPT-State
```

repository.

Give it the repository permission:

```text
Contents: Read and write
```

EDGPT uses this permission to create and update the state file.

> ⚠️ Never share your GitHub token or commit it to a repository.

---

## 3. Configure EDGPT

Open:

**EDGPT → Settings → GitHub Relay**

Enable GitHub Relay and enter:

```text
Repository: yourname/EDGPT-State
Branch: main
File: elite_state.json
Token: YOUR TOKEN
```

Save your settings and start EDGPT.

EDGPT will then create/update:

```text
elite_state.json
```

inside your repository.

---

## 4. Connect Your AI

Connect your AI assistant to GitHub using whatever GitHub integration that AI supports.

Give it access to your:

```text
EDGPT-State
```

repository.

The AI can then read:

```text
elite_state.json
```

as your current Elite Dangerous state.

For example, you could ask:

> **"Read my EDGPT-State repository and tell me where I am in Elite Dangerous."**

or:

> **"Check elite_state.json and tell me about my current ship and route."**

Exactly how GitHub repositories are connected depends on the AI assistant being used.

---

# 🔄 How It Works

### MCP Mode

```text
Elite Dangerous
       ↓
Journal / Status / NavRoute
       ↓
      EDGPT
       ↓
  Local MCP Server
       ↓
MCP-Compatible AI Client
```

### GitHub Relay Mode

```text
Elite Dangerous
       ↓
      EDGPT
       ↓
 elite_state.json
       ↓
Your GitHub Repository
       ↓
AI with GitHub access
```

Both methods can be used independently depending on your AI client and setup.

---

# 🔐 Privacy & Security

EDGPT reads Elite Dangerous files locally.

EDGPT does **not** require your Frontier account password.

OpenAI and GitHub credentials configured in EDGPT are stored locally using **Windows DPAPI encryption**.

Sensitive configuration data is stored under EDGPT's local `data/` directory.

The `data/` directory should **never be committed to GitHub**.

GitHub Relay is optional and disabled by default.

If you enable GitHub Relay, information contained in your EDGPT state file is uploaded to the GitHub repository you configure.

Using a **private repository is recommended** when possible.

---

# 🧑‍💻 Running From Source

The packaged Windows release is recommended for normal users.

Developers who want to run EDGPT from source can clone the repository and create a Python virtual environment.

Example:

```powershell
git clone https://github.com/PanosFilGit/EDGPT.git
cd EDGPT

python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

.\.venv\Scripts\python.exe launcher.py
```

Additional integration components may be required depending on which MCP/tunnel configuration you use.

---

# 🧪 Alpha Status

EDGPT v0.1 is an **early public alpha**.

Currently:

- 🪟 Windows only
- 🎮 Elite Dangerous journal/state integration
- 🤖 MCP server
- 🧠 ChatGPT/OpenAI MCP integration
- 🐙 Optional GitHub Relay
- 🔐 Local DPAPI credential encryption
- 📦 Standalone Windows builds

Things may change significantly before a stable release.

Bug reports and contributions are welcome.

When reporting an issue, **remove API keys, access tokens, usernames or other private information from screenshots and logs.**

---

# 🗺️ Roadmap

Possible future improvements include:

- Easier first-run setup
- More Elite Dangerous state information
- More MCP tools
- Better automatic configuration
- Additional AI-client documentation
- Improved error reporting
- Automatic updates
- Cross-platform support
- Community integrations

---

# 🤝 Contributing

Contributions, testing and bug reports are welcome.

If you find a problem, open a GitHub Issue with:

- What you expected to happen
- What actually happened
- Your Windows version
- Relevant EDGPT logs/errors

Please remove all secrets and private information before posting logs.

---

# ⚖️ Disclaimer

EDGPT is an **unofficial community project**.

It is not affiliated with, endorsed by, or sponsored by **Frontier Developments** or **OpenAI**.

**Elite Dangerous** is a trademark of Frontier Developments.

Third-party software, services and components used with EDGPT remain subject to their respective licenses and terms.

Use EDGPT at your own risk.

---

## o7 CMDR 🚀
