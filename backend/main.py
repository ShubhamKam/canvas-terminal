import asyncio
import json
import os
import platform
import shlex
import signal
import sys
import select
from pathlib import Path
from typing import Optional

from starlette.applications import Starlette
from starlette.websockets import WebSocket, WebSocketDisconnect
from starlette.responses import RedirectResponse
from starlette.staticfiles import StaticFiles

IS_WINDOWS = platform.system() == "Windows"
# Ensure sane terminal defaults for child shells
os.environ.setdefault("TERM", "xterm-256color")
os.environ.setdefault("COLORTERM", "truecolor")

if IS_WINDOWS:
    # Windows: use pywinpty to create a conpty-backed process
    import pywinpty
else:
    import pty
    import tty

app = Starlette(debug=False)

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

# Serve static frontend under /app to avoid conflicting with API/WS
if FRONTEND_DIR.exists():
    app.mount("/app", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="static")


@app.route("/", methods=["GET"])
def root_index(request):
    # Redirect to the app shell
    return RedirectResponse(url="/app/")


def default_shell() -> list[str]:
    if IS_WINDOWS:
        # Prefer PowerShell if available
        pwsh = os.environ.get("COMSPEC") or "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe"
        if Path(pwsh).exists():
            return [pwsh, "-NoLogo"]
        return ["cmd.exe"]
    # POSIX
    shell_env = os.environ.get("SHELL")
    if shell_env and Path(shell_env).exists():
        return [shell_env]
    # Termux common path
    termux_bash = "/data/data/com.termux/files/usr/bin/bash"
    if Path(termux_bash).exists():
        return [termux_bash]
    # Fallbacks
    if Path("/bin/bash").exists():
        return ["/bin/bash"]
    return ["/bin/sh"]


class PtyProcess:
    def __init__(self, argv: Optional[list[str]] = None, cols: int = 120, rows: int = 32):
        self.argv = argv or default_shell()
        self.cols = cols
        self.rows = rows
        self.pid: Optional[int] = None
        self.fd: Optional[int] = None
        if IS_WINDOWS:
            self.pty: Optional[pywinpty.PtyProcess] = None
        else:
            self.pty = None

    def spawn(self):
        if IS_WINDOWS:
            argv_str = " ".join(shlex.quote(a) for a in self.argv)
            self.pty = pywinpty.PtyProcess.spawn(argv_str, dimensions=(self.rows, self.cols))
            self.pid = self.pty.pid
            print(f"[pty] spawned Windows shell pid={self.pid} argv={self.argv}")
        else:
            pid, fd = pty.fork()
            if pid == 0:
                # Child
                try:
                    home = os.environ.get("HOME") or str(Path.home())
                    if home:
                        os.chdir(home)
                except Exception:
                    pass
                # Exec the shell
                os.execvp(self.argv[0], self.argv)
            else:
                # Parent
                self.pid = pid
                self.fd = fd
                print(f"[pty] spawned POSIX shell pid={self.pid} fd={self.fd} argv={self.argv}")

    def write(self, data: bytes):
        if IS_WINDOWS:
            assert self.pty is not None
            self.pty.write(data.decode("utf-8", errors="ignore"))
        else:
            assert self.fd is not None
            os.write(self.fd, data)

    def read(self, num_bytes: int = 4096) -> bytes:
        if IS_WINDOWS:
            assert self.pty is not None
            out = self.pty.read(num_bytes)
            return out.encode("utf-8", errors="ignore")
        else:
            assert self.fd is not None
            try:
                return os.read(self.fd, num_bytes)
            except OSError:
                return b""

    def resize(self, cols: int, rows: int):
        self.cols = cols
        self.rows = rows
        if IS_WINDOWS:
            assert self.pty is not None
            self.pty.setwinsize(rows, cols)
        else:
            import fcntl, termios, struct
            assert self.fd is not None
            # TIOCSWINSZ
            winsize = struct.pack("HHHH", rows, cols, 0, 0)
            fcntl.ioctl(self.fd, termios.TIOCSWINSZ, winsize)

    def terminate(self):
        try:
            if IS_WINDOWS:
                if self.pty is not None:
                    self.pty.terminate()
            else:
                if self.pid:
                    os.kill(self.pid, signal.SIGTERM)
        except Exception:
            pass

    def is_alive(self) -> bool:
        if IS_WINDOWS:
            if self.pty is None:
                return False
            # Prefer dedicated API when available
            isalive = getattr(self.pty, "isalive", None)
            if callable(isalive):
                try:
                    return bool(isalive())
                except Exception:
                    pass
            # Fallback: if exitstatus exists, it's dead; else assume alive
            if getattr(self.pty, "exitstatus", None) is not None:
                return False
            return True
        # POSIX: non-blocking wait to probe child status
        if self.pid is None:
            return False
        try:
            waited_pid, _status = os.waitpid(self.pid, os.WNOHANG)
            return waited_pid == 0
        except ChildProcessError:
            return False


@app.websocket_route("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    # Ensure per-connection locale and interactive shell behavior
    os.environ.setdefault("LC_ALL", "C.UTF-8")
    os.environ.setdefault("LANG", "C.UTF-8")
    print("[ws] client connected")
    proc = PtyProcess()
    proc.spawn()
    try:
        # Nudge shell to emit a prompt and basic diagnostics
        proc.write(b"printf '\r'\n")
        proc.write(b"echo 'CONNECTED' && uname -a && printf '\r'\n")
    except Exception as e:
        print(f"[pty] initial write failed: {e}")

    async def reader():
        try:
            while proc.is_alive():
                await asyncio.sleep(0)
                if not IS_WINDOWS:
                    if proc.fd is None:
                        break
                    r, _w, _e = select.select([proc.fd], [], [], 0.05)
                    if not r:
                        continue
                data = proc.read(4096)
                if data:
                    # Debug prints (trim large)
                    try:
                        preview = data.decode("utf-8", errors="ignore")[:120]
                    except Exception:
                        preview = str(len(data)) + " bytes"
                    print(f"[pty→ws] {len(data)} bytes: {preview!r}")
                    await ws.send_bytes(data)
        except Exception:
            pass

    read_task = asyncio.create_task(reader())

    try:
        while True:
            msg = await ws.receive()
            if "type" in msg and msg["type"] == "websocket.disconnect":
                break
            if "bytes" in msg and msg["bytes"] is not None:
                # print(f"[ws→pty] {len(msg['bytes'])} bytes")
                try:
                    proc.write(msg["bytes"])
                except Exception:
                    # Ensure bytes; some servers provide memoryview
                    data_bytes = bytes(msg["bytes"]) if not isinstance(msg["bytes"], (bytes, bytearray)) else msg["bytes"]
                    proc.write(data_bytes)
                print(f"[ws→pty] {len(msg['bytes'])} bytes")
            elif "text" in msg and msg["text"] is not None:
                txt = msg["text"]
                # Some browsers might send text frames for keys; handle resize JSON explicitly
                try:
                    payload = json.loads(txt)
                    if payload.get("type") == "resize":
                        proc.resize(int(payload.get("cols", 120)), int(payload.get("rows", 32)))
                        continue
                except (json.JSONDecodeError, ValueError, TypeError):
                    pass
                # Convert to bytes; ensure CRLF handling for enter keys if needed
                b = txt.encode("utf-8", errors="ignore")
                print(f"[ws→pty] text {len(b)} bytes: {txt!r}")
                proc.write(b)
    except WebSocketDisconnect:
        print("[ws] client disconnected")
    finally:
        read_task.cancel()
        proc.terminate()
        await asyncio.sleep(0.05)


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8000"))
    # Mount static if running standalone
    if FRONTEND_DIR.exists():
        app.mount("/app", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="static")
    uvicorn.run(app, host="0.0.0.0", port=port, reload=False)