Canvas Terminal

A cross-platform Python + JavaScript terminal with a Material 3-inspired Command Canvas UI. Runs on Android (Termux), macOS, and Windows.

- Backend: FastAPI + WebSockets, per-session PTY (posix) / conpty (Windows)
- Frontend: Vanilla JS + xterm.js + Material 3-inspired design

Quick start

1) Python deps
```
python -m venv .venv
. .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r backend/requirements.txt
pip install -r tui/requirements.txt
```

2) Run backend
```
python backend/main.py
```

3) Open frontend
- Serve `frontend/` statically (e.g., `python -m http.server` from that directory) and open http://localhost:8001
- Or access FastAPI static route at http://127.0.0.1:8000

Notes
- On Windows, install pywinpty.
- On Android/Termux, the default shell is `$SHELL` or /data/data/com.termux/files/usr/bin/bash.

Local, device-native TUI (no browser)
```
python tui/terminal_tui.py
```
This TUI attaches directly to a local PTY for full device permissions/behavior without WebSocket/browser limits.
