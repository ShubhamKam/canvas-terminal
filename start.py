#!/usr/bin/env python3
import os
import sys
import subprocess
import venv
import platform
import time
import socket
import shutil
import signal
import webbrowser
from pathlib import Path
from urllib.request import urlopen
from urllib.error import URLError

PROJECT_ROOT = Path(__file__).resolve().parent
BACKEND_DIR = PROJECT_ROOT / "backend"
REQ_FILE = BACKEND_DIR / "requirements.txt"
PORT = int(os.environ.get("PORT", "8000"))
URL = f"http://127.0.0.1:{PORT}/app"


def is_android_termux() -> bool:
    # Heuristics for Termux/Android
    if "TERMUX_VERSION" in os.environ:
        return True
    if "ANDROID_ROOT" in os.environ or "ANDROID_DATA" in os.environ:
        # Likely Android; Termux installs under this prefix
        if str(PROJECT_ROOT).startswith("/data/data/"):
            return True
    return False


def is_macos() -> bool:
    return platform.system() == "Darwin"


def is_windows() -> bool:
    return platform.system() == "Windows"


def venv_paths(base: Path):
    if is_windows():
        return {
            "python": base / "Scripts" / "python.exe",
            "pip": base / "Scripts" / "pip.exe",
        }
    return {
        "python": base / "bin" / "python",
        "pip": base / "bin" / "pip",
    }


def ensure_venv(venv_dir: Path) -> Path:
    if not venv_dir.exists():
        print(f"[setup] Creating virtual environment at {venv_dir}")
        venv.create(str(venv_dir), with_pip=True, clear=False)
    vp = venv_paths(venv_dir)
    if not vp["python"].exists():
        raise RuntimeError("Virtual environment creation failed: python not found")
    return venv_dir


def pip_install(pip_path: Path, requirements: Path):
    print("[setup] Ensuring recent pip/setuptools/wheel…")
    subprocess.check_call([str(pip_path), "install", "--upgrade", "pip", "setuptools", "wheel"])
    print("[setup] Installing Python dependencies (this may take a minute)...")
    cmd = [str(pip_path), "install", "--prefer-binary", "-r", str(requirements)]
    try:
        subprocess.check_call(cmd)
    except subprocess.CalledProcessError:
        # Retry without prefer-binary as fallback
        subprocess.check_call([str(pip_path), "install", "-r", str(requirements)])


def wait_for_server(port: int, timeout: float = 30.0) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.8):
                # Also verify HTTP route
                try:
                    urlopen(f"http://127.0.0.1:{port}/app", timeout=0.8)
                    return True
                except URLError:
                    return True
        except OSError:
            time.sleep(0.2)
    return False


def open_url(url: str):
    print(f"[open] Opening {url}")
    try:
        if is_android_termux():
            if shutil.which("termux-open-url"):
                subprocess.Popen(["termux-open-url", url])
                return
        if is_macos():
            subprocess.Popen(["open", url])
            return
        if is_windows():
            os.startfile(url)  # type: ignore[attr-defined]
            return
    except Exception:
        pass
    # Fallback
    webbrowser.open(url)


def main():
    print("Canvas Terminal – zero friction launcher")
    print(f"[detect] Platform: {'Android/Termux' if is_android_termux() else platform.platform()}\n")

    venv_dir = PROJECT_ROOT / ".venv"
    ensure_venv(venv_dir)
    vp = venv_paths(venv_dir)

    # Install requirements if first run or user requests
    marker = PROJECT_ROOT / ".deps_ok"
    try:
        if not marker.exists() or os.environ.get("REINSTALL_DEPS") == "1":
            pip_install(vp["pip"], REQ_FILE)
            marker.write_text("ok")
    except subprocess.CalledProcessError as e:
        print("[error] Failed to install dependencies. You can retry: REINSTALL_DEPS=1 python start.py")
        raise e

    # Start backend server
    env = os.environ.copy()
    env.setdefault("PORT", str(PORT))

    # Use backend/main.py which already mounts static at /app
    server_cmd = [str(vp["python"]), str(BACKEND_DIR / "main.py")]
    print(f"[run] Starting backend: {' '.join(server_cmd)}")
    server = subprocess.Popen(server_cmd, cwd=str(BACKEND_DIR), env=env)

    try:
        if wait_for_server(PORT, timeout=40):
            open_url(URL)
        else:
            print(f"[warn] Server not reachable on port {PORT} after timeout. You can open {URL} manually.")
        # Wait until server exits
        server.wait()
    except KeyboardInterrupt:
        print("\n[exit] Shutting down…")
    finally:
        try:
            if server.poll() is None:
                if is_windows():
                    server.terminate()
                else:
                    os.kill(server.pid, signal.SIGTERM)
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
