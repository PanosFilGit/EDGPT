# EDGPT Release Checklist

- [ ] Build using `build-release.ps1` (not `-IncludeThirdParty`).
- [ ] Confirm release safety scan passes.
- [ ] Install `EDGPT-Setup-0.2.0-beta.exe` on a clean Windows user/PC.
- [ ] Confirm no Python installation is required.
- [ ] Launch EDGPT and click CHECK.
- [ ] Confirm local state at `http://127.0.0.1:8080/state`.
- [ ] Confirm MCP endpoint at `http://127.0.0.1:8000/mcp`.
- [ ] Test at least one MCP client.
- [ ] Test GitHub Relay against a private test repository.
- [ ] Confirm `elite_state.json`, `edgpt_manifest.json`, `edgpt_raw/journals/`, and `edgpt_raw/live/` are created.
- [ ] Confirm a fresh install contains no `data/`, `.bin`, `.db`, API key, token, username, or personal path.
- [ ] Verify README/Quick Start match the release.
- [ ] Upload installer, portable ZIP, and `SHA256SUMS.txt`.
- [ ] Mark 0.2.0 as beta/pre-release until tested by multiple independent PCs.
