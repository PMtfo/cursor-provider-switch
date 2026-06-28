#!/usr/bin/env python3
"""按提供商切换 Cursor 的 OpenAI API Key + Base URL（macOS）。

用法:
  curswitch deepseek    # 或 ds / d
  curswitch minimax     # 或 mm / m
  curswitch status
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

DIR = Path(__file__).resolve().parent
REPO_ROOT = DIR.parent
STATE_DB = Path.home() / "Library/Application Support/Cursor/User/globalStorage/state.vscdb"
STATE_KEY = "src.vs.platform.reactivestorage.browser.reactiveStorageServiceImpl.persistentStorage.applicationUser"
AUTH_KEY = "cursorAuth/openAIKey"
CONFIG_DIR = Path.home() / ".cursor-provider-switch"
LOCAL_ENV = REPO_ROOT / "config" / "cursor-providers.env"
SECRETS_ENV = CONFIG_DIR / "secrets.env"
HERMES_ENV = Path.home() / ".hermes" / ".env"
MARKER = Path.home() / ".cursor-active-provider"
SWITCH_LOG = Path.home() / ".cursor-switch.log"

ALIASES = {
    "ds": "deepseek",
    "d": "deepseek",
    "deepseek": "deepseek",
    "mm": "minimax",
    "m": "minimax",
    "minimax": "minimax",
    "status": "status",
    "s": "status",
}

PROVIDERS = {
    "deepseek": {
        "label": "DeepSeek",
        "base_url_key": "DEEPSEEK_BASE_URL",
        "base_url_default": "https://api.deepseek.com",
        "api_key_keys": ("DEEPSEEK_API_KEY",),
    },
    "minimax": {
        "label": "MiniMax",
        "base_url_key": "MINIMAX_BASE_URL",
        "base_url_default": "https://api.minimaxi.com/v1",
        "api_key_keys": ("MINIMAX_CN_API_KEY", "MINIMAX_API_KEY"),
    },
}


def default_workspace() -> Path:
    if os.environ.get("CURSOR_DEFAULT_WORKSPACE"):
        return Path(os.environ["CURSOR_DEFAULT_WORKSPACE"]).expanduser()
    cfg = CONFIG_DIR / "config"
    if cfg.exists():
        for line in cfg.read_text().splitlines():
            if line.startswith("CURSOR_DEFAULT_WORKSPACE="):
                return Path(line.split("=", 1)[1].strip()).expanduser()
    return Path.home() / "Desktop" / "Hermes"


def load_dotenv_files() -> dict[str, str]:
    merged: dict[str, str] = {}
    for path in (SECRETS_ENV, HERMES_ENV, LOCAL_ENV):
        if not path.exists():
            continue
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            merged[k.strip()] = v.strip().strip('"').strip("'")
    return merged


def resolve_value(keys: tuple[str, ...], dotenv: dict[str, str], default: str | None = None) -> str:
    for key in keys:
        if os.environ.get(key):
            return os.environ[key]
        if dotenv.get(key):
            return dotenv[key]
    if default is not None:
        return default
    raise SystemExit(
        f"缺少密钥。请先运行 env-unlock.sh，或写入 {SECRETS_ENV} / {HERMES_ENV}：{', '.join(keys)}"
    )


def cursor_main_running() -> bool:
    return (
        subprocess.run(
            ["pgrep", "-f", "Cursor.app/Contents/MacOS/Cursor"],
            capture_output=True,
        ).returncode
        == 0
    )


def cursor_gui_open() -> bool:
    if cursor_main_running():
        return True
    proc = subprocess.run(
        ["osascript", "-e", 'application "Cursor" is running'],
        capture_output=True,
        text=True,
    )
    return proc.returncode == 0 and proc.stdout.strip().lower() == "true"


def read_current() -> dict:
    conn = sqlite3.connect(STATE_DB)
    row = conn.execute("SELECT value FROM ItemTable WHERE key = ?", (STATE_KEY,)).fetchone()
    auth = conn.execute("SELECT value FROM ItemTable WHERE key = ?", (AUTH_KEY,)).fetchone()
    conn.close()
    if not row:
        raise SystemExit("未找到 Cursor 配置，请先打开过一次 Cursor")
    data = json.loads(row[0])
    return {
        "openAIBaseUrl": data.get("openAIBaseUrl"),
        "useOpenAIKey": data.get("useOpenAIKey"),
        "apiKey": auth[0] if auth else None,
    }


def apply_provider(base_url: str, api_key: str) -> None:
    base_url = base_url.rstrip("/")
    conn = sqlite3.connect(STATE_DB)
    cur = conn.cursor()
    row = cur.execute("SELECT value FROM ItemTable WHERE key = ?", (STATE_KEY,)).fetchone()
    if not row:
        conn.close()
        raise SystemExit("未找到 Cursor reactive storage")

    data = json.loads(row[0])
    data["openAIBaseUrl"] = base_url
    data["useOpenAIKey"] = True
    cur.execute(
        "UPDATE ItemTable SET value = ? WHERE key = ?",
        (json.dumps(data, ensure_ascii=False, separators=(",", ":")), STATE_KEY),
    )

    if cur.execute("SELECT 1 FROM ItemTable WHERE key = ?", (AUTH_KEY,)).fetchone():
        cur.execute("UPDATE ItemTable SET value = ? WHERE key = ?", (api_key, AUTH_KEY))
    else:
        cur.execute("INSERT INTO ItemTable (key, value) VALUES (?, ?)", (AUTH_KEY, api_key))

    conn.commit()
    conn.close()


def mask_key(key: str) -> str:
    if len(key) <= 12:
        return "***"
    return f"{key[:8]}...{key[-4:]}"


def guess_active_provider(base_url: str | None, dotenv: dict[str, str]) -> str | None:
    if not base_url:
        return MARKER.read_text().strip() if MARKER.exists() else None
    for name, cfg in PROVIDERS.items():
        url = resolve_value((cfg["base_url_key"],), dotenv, cfg["base_url_default"]).rstrip("/")
        if base_url.rstrip("/") == url:
            return name
    return MARKER.read_text().strip() if MARKER.exists() else None


def notify(title: str, message: str) -> None:
    safe = message.replace('"', '\\"')
    subprocess.run(
        ["osascript", "-e", f'display notification "{safe}" with title "{title}"'],
        check=False,
    )


def log_line(msg: str) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    with SWITCH_LOG.open("a", encoding="utf-8") as f:
        f.write(f"[{ts}] {msg}\n")


def wait_cursor_stopped(timeout: float = 30.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not cursor_main_running():
            time.sleep(1.0)
            return True
        time.sleep(0.3)
    return not cursor_main_running()


def get_cursor_main_pids() -> list[int]:
    proc = subprocess.run(
        ["pgrep", "-f", "Cursor.app/Contents/MacOS/Cursor"],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return []
    return [int(x) for x in proc.stdout.split() if x.strip().isdigit()]


def stop_cursor() -> bool:
    if not cursor_gui_open():
        return True
    time.sleep(1.0)
    for pid in get_cursor_main_pids():
        subprocess.run(["kill", "-9", str(pid)], check=False)
    subprocess.run(["pkill", "-9", "-f", "Cursor.app/Contents/MacOS/Cursor"], check=False)
    return wait_cursor_stopped(12.0)


def patch_after_cursor_boot(base_url: str, api_key: str, duration: float = 22.0) -> bool:
    deadline = time.time() + duration
    while time.time() < deadline:
        if cursor_main_running():
            apply_provider(base_url, api_key)
            cur = read_current()
            if cur.get("openAIBaseUrl") == base_url.rstrip("/") and cur.get("useOpenAIKey"):
                return True
        time.sleep(2.0)
    return False


def open_cursor(workspace: Path | None = None) -> None:
    ws = workspace or default_workspace()
    if ws.exists():
        subprocess.run(["open", "-a", "Cursor", str(ws)], check=False)
    else:
        subprocess.run(["open", "-a", "Cursor"], check=False)


def spawn_background_worker(provider: str) -> None:
    log_line(f"spawn worker → {provider}")
    script = shlex.quote(str(Path(__file__).resolve()))
    py = shlex.quote(sys.executable)
    log = shlex.quote(str(SWITCH_LOG))
    prov = shlex.quote(provider)
    cmd = f"nohup {py} {script} --_worker {prov} >> {log} 2>&1 &"
    subprocess.Popen(
        ["/bin/bash", "-c", cmd],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        close_fds=True,
        cwd=str(DIR),
    )


def worker_main(provider: str) -> int:
    dotenv = load_dotenv_files()
    cfg = PROVIDERS[provider]
    base_url = resolve_value((cfg["base_url_key"],), dotenv, cfg["base_url_default"]).rstrip("/")
    api_key = resolve_value(cfg["api_key_keys"], dotenv)

    log_line(f"worker start {provider} url={base_url}")
    time.sleep(0.6)

    if not stop_cursor():
        msg = f"切换 {cfg['label']} 失败：无法退出 Cursor"
        log_line(msg)
        notify("Cursor 模型", msg)
        return 3

    before = read_current()
    apply_provider(base_url, api_key)
    MARKER.write_text(provider + "\n")

    after = read_current()
    if after.get("openAIBaseUrl") != base_url or not after.get("useOpenAIKey"):
        msg = f"切换 {cfg['label']} 失败：写入校验未通过"
        log_line(f"{msg} got url={after.get('openAIBaseUrl')}")
        notify("Cursor 模型", msg)
        return 4

    open_cursor()
    time.sleep(1.0)
    if not patch_after_cursor_boot(base_url, api_key):
        log_line(f"二次写入未确认 useOpenAIKey，Base URL 应为 {base_url}")

    msg = f"已切到 {cfg['label']}，Cursor 已自动重开"
    log_line(f"{msg} ({before.get('openAIBaseUrl')} → {base_url})")
    notify("Cursor 模型", msg)
    return 0


def cmd_status(dotenv: dict[str, str]) -> int:
    cur = read_current()
    active = guess_active_provider(cur["openAIBaseUrl"], dotenv)
    print("当前 Cursor 配置:")
    print(f"  推测提供商:    {active or '未知'}")
    print(f"  Base URL:      {cur['openAIBaseUrl']}")
    print(f"  useOpenAIKey:  {cur['useOpenAIKey']}")
    print(f"  API Key:       {mask_key(cur['apiKey']) if cur['apiKey'] else None}")
    print()
    print("可用提供商:")
    for name, cfg in PROVIDERS.items():
        try:
            url = resolve_value((cfg["base_url_key"],), dotenv, cfg["base_url_default"])
            key = resolve_value(cfg["api_key_keys"], dotenv)
            mark = " ← 当前" if name == active else ""
            print(f"  {name:10} {cfg['label']:12} url={url}  key={mask_key(key)}{mark}")
        except SystemExit:
            print(f"  {name:10} {cfg['label']:12} (密钥未配置)")
    return 0


def normalize_provider(raw: str | None) -> str | None:
    if not raw:
        return None
    return ALIASES.get(raw.lower(), raw.lower())


def main() -> int:
    parser = argparse.ArgumentParser(description="切换 Cursor DeepSeek / MiniMax")
    parser.add_argument("provider", nargs="?", help="deepseek|minimax|ds|mm|status")
    parser.add_argument("--no-restart", action="store_true", help="不自动退出/重开 Cursor")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--_worker", dest="worker", metavar="PROVIDER", help=argparse.SUPPRESS)
    args = parser.parse_args()

    if args.worker:
        if args.worker not in PROVIDERS:
            return 1
        return worker_main(args.worker)

    provider = normalize_provider(args.provider)
    dotenv = load_dotenv_files()

    if not provider or provider == "status":
        return cmd_status(dotenv)

    if provider not in PROVIDERS:
        print(f"未知提供商: {args.provider}", file=sys.stderr)
        print("可用: deepseek, minimax, ds, mm, status", file=sys.stderr)
        return 1

    cfg = PROVIDERS[provider]
    base_url = resolve_value((cfg["base_url_key"],), dotenv, cfg["base_url_default"])
    api_key = resolve_value(cfg["api_key_keys"], dotenv)

    if args.dry_run:
        print(f"[dry-run] {cfg['label']}: {base_url}  key={mask_key(api_key)}")
        return 0

    if cursor_gui_open() and not args.no_restart:
        spawn_background_worker(provider)
        msg = f"正在切换到 {cfg['label']}，Cursor 将自动退出并重开（约 5 秒）"
        notify("Cursor 模型", msg)
        print(f"✓ {msg}")
        print(f"  目标 Base URL: {base_url}")
        print(f"  日志: {SWITCH_LOG}")
        return 0

    if cursor_gui_open() and args.no_restart:
        print("Cursor 正在运行。直接写库会被覆盖，请去掉 --no-restart 或先 Cmd+Q", file=sys.stderr)
        return 2

    before = read_current()
    apply_provider(base_url.rstrip("/"), api_key)
    MARKER.write_text(provider + "\n")

    after = read_current()
    if after.get("openAIBaseUrl") != base_url.rstrip("/") or not after.get("useOpenAIKey"):
        print("写入后校验失败", file=sys.stderr)
        return 4

    open_cursor()
    msg = f"已切到 {cfg['label']}"
    notify("Cursor 模型", msg)
    print(f"✓ {msg}")
    print(f"  Base URL: {before['openAIBaseUrl']} → {base_url.rstrip('/')}")
    print(f"  useOpenAIKey: {before['useOpenAIKey']} → True")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
