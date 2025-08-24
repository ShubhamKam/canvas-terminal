#!/usr/bin/env python3
import argparse
import os
import pty
import select
import signal
import sys
import termios
import tty
import fcntl
import struct


def set_winsize(fd, rows, cols):
    winsize = struct.pack("HHHH", rows, cols, 0, 0)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)


def raw_tty(stdin_fd):
    old = termios.tcgetattr(stdin_fd)
    tty.setraw(stdin_fd)
    return old


def detect_shell_path() -> str:
    # Prefer explicit SHELL
    shell = os.environ.get("SHELL")
    # Termux
    termux_bash = "/data/data/com.termux/files/usr/bin/bash"
    if not shell and os.path.exists(termux_bash):
        shell = termux_bash
    # Common fallbacks
    if not shell and os.path.exists("/bin/bash"):
        shell = "/bin/bash"
    if not shell:
        shell = "/bin/sh"
    return shell


def build_shell_argv(clean_start: bool, login: bool = False, explicit_shell: str | None = None, initial_cmd: str | None = None) -> list[str]:
    shell = explicit_shell or detect_shell_path()
    shell_name = os.path.basename(shell)
    args: list[str] = [shell]
    if login:
        # many shells honor -l for login shell formatting of env
        args.append("-l")
    if clean_start:
        # Start without user rc to avoid auto-start side effects (e.g., pg_ctl)
        if shell_name in ("bash", "bash.exe"):
            args += ["--noprofile", "--norc", "-i"]
            return args
        if shell_name in ("zsh", "zsh.exe"):
            args += ["-f", "-i"]
            return args
        # POSIX sh/dash
        args += ["-i"]
        return args
    # Normal interactive shell (sources rc files)
    if shell_name in ("bash", "bash.exe"):
        args += ["-i"]
        return args
    if shell_name in ("zsh", "zsh.exe"):
        args += ["-i"]
        return args
    if initial_cmd:
        args += ["-c", initial_cmd]
    return args


def get_stdout_winsize():
    try:
        data = fcntl.ioctl(sys.stdout.fileno(), termios.TIOCGWINSZ, b"\0" * 8)
        rows, cols, _xp, _yp = struct.unpack("HHHH", data)
        return int(rows) or 32, int(cols) or 120
    except Exception:
        return 32, 120


def main():
    parser = argparse.ArgumentParser(description="Device-native PTY terminal (no browser)")
    parser.add_argument("--no-clean", action="store_true", help="Start shell with user rc files (default: clean)")
    parser.add_argument("--login", action="store_true", help="Run as a login shell (-l)")
    parser.add_argument("--shell", help="Explicit shell path (e.g., /bin/bash)")
    parser.add_argument("--cmd", help="Run an initial command instead of interactive")
    args = parser.parse_args()

    os.environ.setdefault("TERM", "xterm-256color")
    os.environ.setdefault("COLORTERM", "truecolor")

    pid, master_fd = pty.fork()
    if pid == 0:
        # Child executes the shell
        argv = build_shell_argv(clean_start=not args.no_clean, login=args.login, explicit_shell=args.shell, initial_cmd=args.cmd)
        os.execvp(argv[0], argv)
        return

    # Parent: connect stdin/stdout to PTY master
    old_tty = raw_tty(sys.stdin.fileno())
    try:
        # Initial size from current TTY
        rows, cols = get_stdout_winsize()
        try:
            set_winsize(master_fd, rows, cols)
        except Exception:
            pass

        def on_winch(_signum, _frame):
            r, c = get_stdout_winsize()
            try:
                set_winsize(master_fd, r, c)
            except Exception:
                pass

        signal.signal(signal.SIGWINCH, on_winch)

        while True:
            rfds, _, _ = select.select([sys.stdin.fileno(), master_fd], [], [])
            if sys.stdin.fileno() in rfds:
                data = os.read(sys.stdin.fileno(), 4096)
                if not data:
                    break
                os.write(master_fd, data)
            if master_fd in rfds:
                out = os.read(master_fd, 4096)
                if not out:
                    break
                os.write(sys.stdout.fileno(), out)
    finally:
        termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, old_tty)


if __name__ == "__main__":
    main()
