import ctypes
import json
import os
import subprocess
import sys
import threading
import time
import tkinter as tk
import urllib.request
from ctypes import wintypes
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog

APP_NAME = "EDGPT"
APP_VERSION = "0.2.0-beta"
MCP_URL = "http://127.0.0.1:8000/mcp"
STATE_URL = "http://127.0.0.1:8080/state"

FROZEN = bool(getattr(sys, "frozen", False))
ROOT = Path(sys.executable).resolve().parent if FROZEN else Path(__file__).resolve().parent
BIN = ROOT / "bin"
DATA = ROOT / "data"
DATA.mkdir(parents=True, exist_ok=True)

if FROZEN:
    PYTHON = None
    STATE_SERVER = BIN / "edgpt-state.exe"
    MCP_SERVER = BIN / "edgpt-mcp.exe"
    UPLOADER = BIN / "edgpt-uploader.exe"
else:
    PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
    STATE_SERVER = BIN / "server.py"
    MCP_SERVER = BIN / "mcp_server.py"
    UPLOADER = BIN / "uploader.py"

TUNNEL_CLIENT = BIN / "tunnel-client.exe"
CONFIG_FILE = DATA / "config.json"
GITHUB_SECRET_FILE = DATA / "github_secret.bin"
OPENAI_SECRET_FILE = DATA / "openai_secret.bin"

DEFAULT_CONFIG = {
    "elite": {
        "journal_path": str(Path.home() / "Saved Games" / "Frontier Developments" / "Elite Dangerous")
    },
    "github": {
        "enabled": False,
        "repository": "",
        "branch": "main",
        "file": "elite_state.json",
    },
    "openai": {
        "enabled": False,
        "profile": "edgpt",
        "tunnel_id": "",
    },
    "app": {
        "auto_start": True,
    },
}

CREATE_FLAGS = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

state_proc = None
mcp_proc = None
uploader_proc = None
openai_proc = None


class DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_byte)),
    ]


crypt32 = ctypes.windll.crypt32
kernel32 = ctypes.windll.kernel32


def _blob(data: bytes):
    buf = ctypes.create_string_buffer(data)
    return DATA_BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_byte))), buf


def encrypt_dpapi(data: bytes, description: str) -> bytes:
    source, _ = _blob(data)
    target = DATA_BLOB()
    if not crypt32.CryptProtectData(
        ctypes.byref(source), description, None, None, None, 0, ctypes.byref(target)
    ):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(target.pbData, target.cbData)
    finally:
        kernel32.LocalFree(target.pbData)


def decrypt_dpapi(data: bytes) -> bytes:
    source, _ = _blob(data)
    target = DATA_BLOB()
    if not crypt32.CryptUnprotectData(
        ctypes.byref(source), None, None, None, None, 0, ctypes.byref(target)
    ):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(target.pbData, target.cbData)
    finally:
        kernel32.LocalFree(target.pbData)


def save_secret(path: Path, value: str, description: str):
    value = value.strip()
    if not value:
        raise ValueError("Secret cannot be empty.")
    path.write_bytes(encrypt_dpapi(value.encode("utf-8"), description))


def load_secret(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(path.name)
    return decrypt_dpapi(path.read_bytes()).decode("utf-8").strip()


def deep_merge(default, custom):
    result = dict(default)
    for key, value in custom.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config():
    if not CONFIG_FILE.exists():
        cfg = json.loads(json.dumps(DEFAULT_CONFIG))
        CONFIG_FILE.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
        return cfg
    try:
        loaded = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        return deep_merge(DEFAULT_CONFIG, loaded)
    except Exception:
        return json.loads(json.dumps(DEFAULT_CONFIG))


def save_config():
    CONFIG_FILE.write_text(json.dumps(config, indent=2), encoding="utf-8")


config = load_config()


def proc_running(proc):
    return proc is not None and proc.poll() is None


def log(text):
    log_box.configure(state="normal")
    log_box.insert("end", text + "\n")
    log_box.see("end")
    log_box.configure(state="disabled")


def process_env():
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["ELITE_JOURNAL_DIR"] = config["elite"]["journal_path"]
    env["EDGPT_CONFIG_FILE"] = str(CONFIG_FILE)
    env["EDGPT_GITHUB_SECRET_FILE"] = str(GITHUB_SECRET_FILE)
    env["EDGPT_DATA_DIR"] = str(DATA)
    return env


def stream_output(proc, prefix):
    if proc is None or proc.stdout is None:
        return
    try:
        for line in proc.stdout:
            line = line.rstrip()
            if line:
                root.after(0, log, f"[{prefix}] {line}")
    except Exception as exc:
        root.after(0, log, f"[{prefix}] output error: {exc}")


def start_helper(path: Path, prefix: str):
    command = [str(path)] if FROZEN else [str(PYTHON), str(path)]
    proc = subprocess.Popen(
        command,
        cwd=str(ROOT),
        env=process_env(),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        creationflags=CREATE_FLAGS,
    )
    threading.Thread(target=stream_output, args=(proc, prefix), daemon=True).start()
    return proc


def url_ok(url, timeout=2):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return response.status == 200
    except Exception:
        return False


def wait_for_state(timeout=12):
    end = time.time() + timeout
    while time.time() < end:
        if url_ok(STATE_URL, timeout=1):
            return True
        time.sleep(0.25)
    return False


def validate_core_files():
    required = [STATE_SERVER, MCP_SERVER]
    if not FROZEN:
        required.insert(0, PYTHON)
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        messagebox.showerror(APP_NAME, "Missing required files:\n\n" + "\n".join(missing))
        return False
    return True


def ensure_tunnel_profile(api_key):
    if not TUNNEL_CLIENT.exists():
        raise RuntimeError(
            "OpenAI tunnel-client.exe is not installed in EDGPT\\bin. "
            "The public EDGPT build does not bundle it."
        )
    tunnel_id = config["openai"]["tunnel_id"].strip()
    profile = config["openai"]["profile"].strip() or "edgpt"
    if not tunnel_id:
        raise RuntimeError("OpenAI Tunnel ID is missing in Settings.")

    env = process_env()
    env["CONTROL_PLANE_API_KEY"] = api_key
    result = subprocess.run(
        [
            str(TUNNEL_CLIENT),
            "init",
            "--profile", profile,
            "--tunnel-id", tunnel_id,
            "--mcp-server-url", MCP_URL,
            "--health-listen-addr", "127.0.0.1:0",
        ],
        cwd=str(BIN),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=CREATE_FLAGS,
    )
    if result.returncode != 0 and "exist" not in (result.stdout or "").lower():
        raise RuntimeError((result.stdout or "Tunnel initialization failed.").strip())


def start_openai():
    global openai_proc
    api_key = load_secret(OPENAI_SECRET_FILE)
    ensure_tunnel_profile(api_key)
    env = process_env()
    env["CONTROL_PLANE_API_KEY"] = api_key
    profile = config["openai"]["profile"].strip() or "edgpt"
    openai_proc = subprocess.Popen(
        [
            str(TUNNEL_CLIENT),
            "run",
            "--profile", profile,
            "--health.listen-addr", "127.0.0.1:0",
        ],
        cwd=str(BIN),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        creationflags=CREATE_FLAGS,
    )
    threading.Thread(target=stream_output, args=(openai_proc, "OPENAI"), daemon=True).start()


def start_all():
    global state_proc, mcp_proc, uploader_proc

    if not validate_core_files():
        return

    journal = Path(config["elite"]["journal_path"])
    if not journal.exists():
        messagebox.showerror(
            APP_NAME,
            "Elite Dangerous journal folder was not found.\n\nOpen Settings and choose the correct folder.",
        )
        return

    log("")
    log(f"Starting EDGPT {APP_VERSION}...")

    if not proc_running(state_proc):
        state_proc = start_helper(STATE_SERVER, "STATE")
    if wait_for_state():
        log("Core state server ready.")
    else:
        log("WARNING: state server did not answer on port 8080.")

    if not proc_running(mcp_proc):
        mcp_proc = start_helper(MCP_SERVER, "MCP")
        log(f"MCP starting at {MCP_URL}")

    if config["github"]["enabled"]:
        if not UPLOADER.exists():
            log("GitHub Relay enabled, but uploader helper is missing.")
        elif not config["github"]["repository"].strip():
            log("GitHub Relay enabled, but repository is not configured.")
        elif not GITHUB_SECRET_FILE.exists():
            log("GitHub Relay enabled, but token is not configured.")
        elif not proc_running(uploader_proc):
            uploader_proc = start_helper(UPLOADER, "GITHUB")
            log("GitHub Relay started.")

    if config["openai"]["enabled"] and not proc_running(openai_proc):
        try:
            start_openai()
            log("OpenAI tunnel started.")
        except Exception as exc:
            log(f"OpenAI tunnel not started: {exc}")

    log("Bridge start sequence complete.")
    log("")


def stop_proc(proc, name):
    if not proc_running(proc):
        return
    log(f"Stopping {name}...")
    try:
        proc.terminate()
        proc.wait(timeout=4)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def stop_all():
    global state_proc, mcp_proc, uploader_proc, openai_proc
    stop_proc(openai_proc, "OpenAI tunnel")
    stop_proc(uploader_proc, "GitHub Relay")
    stop_proc(mcp_proc, "MCP")
    stop_proc(state_proc, "state server")
    state_proc = None
    mcp_proc = None
    uploader_proc = None
    openai_proc = None
    log("Bridge stopped.")


def run_diagnostics():
    checks = [
        ("Elite journal folder", Path(config["elite"]["journal_path"]).exists(), config["elite"]["journal_path"]),
        ("State server", url_ok(STATE_URL), STATE_URL),
        ("MCP process", proc_running(mcp_proc), MCP_URL),
    ]
    if config["github"]["enabled"]:
        checks.append(("GitHub Relay", proc_running(uploader_proc), config["github"]["repository"] or "not configured"))
    if config["openai"]["enabled"]:
        checks.append(("OpenAI tunnel", proc_running(openai_proc), config["openai"]["tunnel_id"] or "not configured"))

    log("")
    log("EDGPT CHECK")
    log("-" * 58)
    failed = 0
    for name, ok, detail in checks:
        log(f"{'OK' if ok else 'FAIL'}  {name}  |  {detail}")
        if not ok:
            failed += 1
    log("-" * 58)
    log("Bridge is ready." if failed == 0 else f"{failed} check(s) need attention.")
    log("")


def open_settings():
    win = tk.Toplevel(root)
    win.title("EDGPT Settings")
    win.geometry("700x610")
    win.resizable(False, False)
    win.transient(root)
    win.grab_set()

    elite = tk.LabelFrame(win, text="Elite Dangerous")
    elite.pack(fill="x", padx=14, pady=(14, 6))
    journal_var = tk.StringVar(value=config["elite"]["journal_path"])
    tk.Label(elite, text="Journal folder:").grid(row=0, column=0, sticky="w", padx=10, pady=(8, 2))
    tk.Entry(elite, textvariable=journal_var, width=72).grid(row=1, column=0, padx=10, pady=(0, 8))

    def browse():
        chosen = filedialog.askdirectory(parent=win)
        if chosen:
            journal_var.set(chosen)

    tk.Button(elite, text="Browse", command=browse).grid(row=1, column=1, padx=8, pady=(0, 8))

    github = tk.LabelFrame(win, text="GitHub Relay (optional)")
    github.pack(fill="x", padx=14, pady=6)
    github_enabled = tk.BooleanVar(value=config["github"]["enabled"])
    repo_var = tk.StringVar(value=config["github"]["repository"])
    branch_var = tk.StringVar(value=config["github"]["branch"])
    file_var = tk.StringVar(value=config["github"]["file"])
    tk.Checkbutton(github, text="Enable GitHub Relay", variable=github_enabled).grid(row=0, column=0, columnspan=3, sticky="w", padx=10, pady=6)
    tk.Label(github, text="Repository:").grid(row=1, column=0, sticky="w", padx=10, pady=3)
    tk.Entry(github, textvariable=repo_var, width=42).grid(row=1, column=1, sticky="w", pady=3)
    tk.Label(github, text="owner/repository").grid(row=1, column=2, sticky="w", padx=8)
    tk.Label(github, text="Branch:").grid(row=2, column=0, sticky="w", padx=10, pady=3)
    tk.Entry(github, textvariable=branch_var, width=18).grid(row=2, column=1, sticky="w", pady=3)
    tk.Label(github, text="State file:").grid(row=3, column=0, sticky="w", padx=10, pady=3)
    tk.Entry(github, textvariable=file_var, width=28).grid(row=3, column=1, sticky="w", pady=3)
    github_secret_status = tk.StringVar(value="Saved securely" if GITHUB_SECRET_FILE.exists() else "Not set")
    tk.Label(github, text="Token:").grid(row=4, column=0, sticky="w", padx=10, pady=6)
    tk.Label(github, textvariable=github_secret_status).grid(row=4, column=1, sticky="w", pady=6)

    def set_github_token():
        value = simpledialog.askstring("GitHub Token", "Enter a fine-grained GitHub token:", show="*", parent=win)
        if value:
            save_secret(GITHUB_SECRET_FILE, value, "EDGPT GitHub Token")
            github_secret_status.set("Saved securely")

    tk.Button(github, text="Set token", command=set_github_token).grid(row=4, column=2, padx=8, pady=6)

    openai = tk.LabelFrame(win, text="OpenAI Secure MCP Tunnel (advanced / optional)")
    openai.pack(fill="x", padx=14, pady=6)
    openai_enabled = tk.BooleanVar(value=config["openai"]["enabled"])
    profile_var = tk.StringVar(value=config["openai"]["profile"])
    tunnel_var = tk.StringVar(value=config["openai"]["tunnel_id"])
    tk.Checkbutton(openai, text="Enable OpenAI tunnel", variable=openai_enabled).grid(row=0, column=0, columnspan=3, sticky="w", padx=10, pady=6)
    tk.Label(openai, text="Profile:").grid(row=1, column=0, sticky="w", padx=10, pady=3)
    tk.Entry(openai, textvariable=profile_var, width=22).grid(row=1, column=1, sticky="w", pady=3)
    tk.Label(openai, text="Tunnel ID:").grid(row=2, column=0, sticky="w", padx=10, pady=3)
    tk.Entry(openai, textvariable=tunnel_var, width=46).grid(row=2, column=1, sticky="w", pady=3)
    openai_secret_status = tk.StringVar(value="Saved securely" if OPENAI_SECRET_FILE.exists() else "Not set")
    tk.Label(openai, text="API key:").grid(row=3, column=0, sticky="w", padx=10, pady=6)
    tk.Label(openai, textvariable=openai_secret_status).grid(row=3, column=1, sticky="w", pady=6)

    def set_openai_key():
        value = simpledialog.askstring("OpenAI API Key", "Enter the tunnel runtime API key:", show="*", parent=win)
        if value:
            save_secret(OPENAI_SECRET_FILE, value, "EDGPT OpenAI API Key")
            openai_secret_status.set("Saved securely")

    tk.Button(openai, text="Set key", command=set_openai_key).grid(row=3, column=2, padx=8, pady=6)

    app = tk.LabelFrame(win, text="Bridge")
    app.pack(fill="x", padx=14, pady=6)
    auto_start = tk.BooleanVar(value=config["app"]["auto_start"])
    tk.Checkbutton(app, text="Start the bridge automatically when EDGPT opens", variable=auto_start).pack(anchor="w", padx=10, pady=8)

    def save_close():
        config["elite"]["journal_path"] = journal_var.get().strip()
        config["github"]["enabled"] = bool(github_enabled.get())
        config["github"]["repository"] = repo_var.get().strip()
        config["github"]["branch"] = branch_var.get().strip() or "main"
        config["github"]["file"] = file_var.get().strip() or "elite_state.json"
        config["openai"]["enabled"] = bool(openai_enabled.get())
        config["openai"]["profile"] = profile_var.get().strip() or "edgpt"
        config["openai"]["tunnel_id"] = tunnel_var.get().strip()
        config["app"]["auto_start"] = bool(auto_start.get())
        save_config()
        log("Settings saved. Restart bridge to apply connection changes.")
        win.destroy()

    tk.Button(win, text="SAVE", width=18, height=2, command=save_close).pack(pady=12)


def update_status():
    state_var.set("RUNNING" if proc_running(state_proc) else "STOPPED")
    mcp_var.set("RUNNING" if proc_running(mcp_proc) else "STOPPED")
    github_var.set("RUNNING" if proc_running(uploader_proc) else ("DISABLED" if not config["github"]["enabled"] else "STOPPED"))
    openai_var.set("RUNNING" if proc_running(openai_proc) else ("DISABLED" if not config["openai"]["enabled"] else "STOPPED"))
    root.after(1000, update_status)


def on_close():
    if any(proc_running(p) for p in (state_proc, mcp_proc, uploader_proc, openai_proc)):
        if not messagebox.askyesno(APP_NAME, "Stop the bridge and exit?"):
            return
        stop_all()
    root.destroy()


root = tk.Tk()
root.title(f"EDGPT {APP_VERSION}")
root.geometry("790x560")
root.minsize(700, 500)

tk.Label(root, text="EDGPT", font=("Segoe UI", 24, "bold")).pack(pady=(18, 2))
tk.Label(root, text="Elite Dangerous → AI bridge", font=("Segoe UI", 11)).pack(pady=(0, 4))
tk.Label(root, text=f"Local MCP: {MCP_URL}", font=("Consolas", 9)).pack(pady=(0, 12))

buttons = tk.Frame(root)
buttons.pack(pady=4)
tk.Button(buttons, text="START BRIDGE", width=17, height=2, command=start_all).grid(row=0, column=0, padx=5)
tk.Button(buttons, text="STOP", width=13, height=2, command=stop_all).grid(row=0, column=1, padx=5)
tk.Button(buttons, text="SETTINGS", width=13, height=2, command=open_settings).grid(row=0, column=2, padx=5)
tk.Button(buttons, text="CHECK", width=13, height=2, command=run_diagnostics).grid(row=0, column=3, padx=5)

status = tk.LabelFrame(root, text="Bridge status", padx=12, pady=8)
status.pack(fill="x", padx=18, pady=14)
state_var = tk.StringVar(value="STOPPED")
mcp_var = tk.StringVar(value="STOPPED")
github_var = tk.StringVar(value="DISABLED")
openai_var = tk.StringVar(value="DISABLED")
for row, (name, variable) in enumerate([
    ("Elite state", state_var),
    ("Local MCP", mcp_var),
    ("GitHub Relay", github_var),
    ("OpenAI tunnel", openai_var),
]):
    tk.Label(status, text=name + ":", width=18, anchor="w", font=("Segoe UI", 10, "bold")).grid(row=row, column=0, sticky="w", pady=2)
    tk.Label(status, textvariable=variable, anchor="w", font=("Consolas", 9)).grid(row=row, column=1, sticky="w", pady=2)

log_frame = tk.LabelFrame(root, text="Log")
log_frame.pack(fill="both", expand=True, padx=18, pady=(0, 18))
log_box = tk.Text(log_frame, state="disabled", font=("Consolas", 9))
log_box.pack(fill="both", expand=True, padx=6, pady=6)

root.protocol("WM_DELETE_WINDOW", on_close)
update_status()

journal = Path(config["elite"]["journal_path"])
if not journal.exists():
    root.after(250, open_settings)
elif config["app"]["auto_start"]:
    root.after(350, start_all)

root.mainloop()
