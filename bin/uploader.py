import base64
import ctypes
import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from ctypes import wintypes
from pathlib import Path

LOCAL_STATE_URL = "http://localhost:8080/state"
CONFIG_FILE = Path(os.environ.get("EDGPT_CONFIG_FILE", "data/config.json")).expanduser()
TOKEN_FILE = Path(os.environ.get("EDGPT_GITHUB_SECRET_FILE", "data/github_secret.bin")).expanduser()

POLL_SECONDS = 2
MIN_PUSH_SECONDS = 10
RAW_MIRROR_SECONDS = 300
MAX_RAW_FILE_BYTES = 90 * 1024 * 1024

DEFAULT_ELITE_DIR = Path.home() / "Saved Games" / "Frontier Developments" / "Elite Dangerous"
ELITE_DIR = Path(os.environ.get("ELITE_JOURNAL_DIR", str(DEFAULT_ELITE_DIR))).expanduser()

VOLATILE_KEYS = {"fetched_at", "generated_at", "updated_at", "last_updated"}


class DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]


crypt32 = ctypes.windll.crypt32
kernel32 = ctypes.windll.kernel32


def make_blob(data):
    buf = ctypes.create_string_buffer(data)
    return DATA_BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_byte))), buf


def decrypt(data):
    blob_in, _ = make_blob(data)
    blob_out = DATA_BLOB()
    if not crypt32.CryptUnprotectData(ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out)):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        kernel32.LocalFree(blob_out.pbData)


def load_settings():
    if not CONFIG_FILE.exists():
        raise RuntimeError("EDGPT config.json was not found.")
    data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    github = data.get("github", {})
    repo = github.get("repository", "").strip()
    branch = github.get("branch", "main").strip() or "main"
    filename = github.get("file", "elite_state.json").strip() or "elite_state.json"
    if not repo or "/" not in repo:
        raise RuntimeError("GitHub repository is not configured. Use owner/repository.")
    return repo, branch, filename


def get_token():
    if not TOKEN_FILE.exists():
        raise RuntimeError("GitHub token is not configured in EDGPT Settings.")
    token = decrypt(TOKEN_FILE.read_bytes()).decode("utf-8").strip()
    if not token:
        raise RuntimeError("GitHub token is empty.")
    return token


def get_local_state():
    request = urllib.request.Request(LOCAL_STATE_URL, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def github_request(token, url, method="GET", body=None):
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "EDGPT",
    }
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def clean_state(value):
    if isinstance(value, dict):
        return {k: clean_state(v) for k, v in value.items() if k not in VOLATILE_KEYS}
    if isinstance(value, list):
        return [clean_state(v) for v in value]
    return value


def get_hash(state):
    encoded = json.dumps(state, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def get_remote_file(token, api_url, branch):
    try:
        return github_request(token, api_url + f"?ref={branch}")
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise


def upload_text_file(token, repo, branch, path, text, message):
    api_url = f"https://api.github.com/repos/{repo}/contents/{path}"
    current = get_remote_file(token, api_url, branch)
    encoded = base64.b64encode(text.encode("utf-8")).decode("ascii")
    body = {"message": message, "content": encoded, "branch": branch}
    if current is not None:
        body["sha"] = current["sha"]
    github_request(token, api_url, method="PUT", body=body)


def mirror_raw_elite_files(token, repo, branch, known_hashes):
    files = []
    files.extend(sorted(ELITE_DIR.glob("Journal.*.log")))
    files.extend(sorted(ELITE_DIR.glob("*.json")))
    manifest_files = []

    for path in files:
        try:
            size = path.stat().st_size
            if size > MAX_RAW_FILE_BYTES:
                print("Raw mirror skipped (>90MB):", path.name)
                manifest_files.append({"name": path.name, "skipped": "too_large", "size": size})
                continue
            data = path.read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            is_journal = path.name.startswith("Journal.") and path.suffix.lower() == ".log"
            remote_path = ("edgpt_raw/journals/" if is_journal else "edgpt_raw/live/") + path.name
            manifest_files.append({"name": path.name, "path": remote_path, "sha256": digest, "size": size})
            if known_hashes.get(remote_path) == digest:
                continue
            text = data.decode("utf-8", errors="replace")
            upload_text_file(token, repo, branch, remote_path, text, f"Mirror Elite raw data: {path.name}")
            known_hashes[remote_path] = digest
            print(time.strftime("[%H:%M:%S]"), "Raw mirrored:", path.name)
        except urllib.error.HTTPError as error:
            body = error.read().decode(errors="replace")
            print("Raw mirror GitHub error:", path.name, error.code, body)
        except Exception as error:
            print("Raw mirror error:", path.name, error)

    manifest = {
        "generated_unix": int(time.time()),
        "journal_directory": "local/private path intentionally not published",
        "files": manifest_files,
        "usage": "AI: read elite_state.json for current context, then use this manifest to fetch any raw journal/live JSON file when deeper history is needed.",
    }
    upload_text_file(
        token, repo, branch, "edgpt_manifest.json",
        json.dumps(manifest, indent=2, ensure_ascii=False),
        "Update EDGPT raw-data manifest",
    )
    return known_hashes


def upload(token, state, repo, branch, filename):
    api_url = f"https://api.github.com/repos/{repo}/contents/{filename}"
    current = get_remote_file(token, api_url, branch)
    state = dict(state)
    state["_edgpt_relay"] = {
        "uploaded_unix": int(time.time()),
        "mode": "full-context",
        "note": "Current rich context + preserved raw recent events. Complete raw history is queryable over EDGPT MCP.",
    }
    text = json.dumps(state, indent=2, ensure_ascii=False)
    encoded = base64.b64encode(text.encode("utf-8")).decode("ascii")
    body = {"message": "Update EDGPT full context", "content": encoded, "branch": branch}
    if current is not None:
        body["sha"] = current["sha"]
    github_request(token, api_url, method="PUT", body=body)


repo, branch, filename = load_settings()
token = get_token()

print("\n==============================")
print(" EDGPT GITHUB RELAY - FULL CONTEXT")
print("==============================\n")
print("Local:")
print(LOCAL_STATE_URL)
print("\nGitHub:")
print(f"https://github.com/{repo}/blob/{branch}/{filename}\n")

last_hash = None
pending = None
last_upload = 0
last_raw_mirror = 0
raw_hashes = {}

while True:
    try:
        state = clean_state(get_local_state())
        current_hash = get_hash(state)
        if current_hash != last_hash:
            last_hash = current_hash
            pending = state
        if pending is not None and time.time() - last_upload >= MIN_PUSH_SECONDS:
            upload(token, pending, repo, branch, filename)
            pending = None
            last_upload = time.time()
            print(time.strftime("[%H:%M:%S]"), "GitHub updated")

        if time.time() - last_raw_mirror >= RAW_MIRROR_SECONDS:
            raw_hashes = mirror_raw_elite_files(token, repo, branch, raw_hashes)
            last_raw_mirror = time.time()
    except urllib.error.HTTPError as error:
        body = error.read().decode(errors="replace")
        print("GitHub error:", error.code, body)
    except Exception as error:
        print("Waiting:", error)
    time.sleep(POLL_SECONDS)
