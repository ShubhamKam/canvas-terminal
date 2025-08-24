#!/usr/bin/env python3
# A cross-platform, standalone Python shell (no external shell).
# Features: cd/pwd/export/which, pipelines (|), redirection (> >> <), globs, env expansion.
# Runs on Android (Termux Python), macOS, and Windows.

from __future__ import annotations
import os
import sys
import shlex
import subprocess
import glob as pyglob
import re
from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple

IS_WINDOWS = os.name == 'nt'
HOME = os.path.expanduser('~')

@dataclass
class Redirection:
    stdin: Optional[str] = None
    stdout: Optional[str] = None
    stdout_append: bool = False
    stderr: Optional[str] = None
    stderr_append: bool = False
    stderr_to_stdout: bool = False

@dataclass
class Command:
    argv: List[str]
    redir: Redirection

VAR_PATTERN = re.compile(r"\$(\w+)|\$\{([^}]+)\}")

def expand_vars(token: str, env: Dict[str, str]) -> str:
    def repl(m: re.Match[str]) -> str:
        key = m.group(1) or m.group(2) or ''
        return env.get(key, '')
    return VAR_PATTERN.sub(repl, token)


def expand_globs(args: List[str]) -> List[str]:
    expanded: List[str] = []
    for a in args:
        if any(ch in a for ch in ['*', '?', '[']):
            matches = pyglob.glob(a)
            if matches:
                expanded.extend(matches)
            else:
                expanded.append(a)
        else:
            expanded.append(a)
    return expanded


def parse_pipeline(cmd_str: str, env: Dict[str, str]) -> List[Command]:
    # Split by '|' respecting quotes via shlex
    parts: List[str] = []
    buf = ''
    level = 0
    for ch in cmd_str:
        if ch == '|' and level == 0:
            parts.append(buf.strip())
            buf = ''
        else:
            buf += ch
            if ch in ('"', "'"):
                # naive quote toggle; shlex will handle quotes properly later
                level ^= 1
    if buf.strip():
        parts.append(buf.strip())

    pipeline: List[Command] = []
    for part in parts:
        tokens = shlex.split(part, posix=not IS_WINDOWS)
        tokens = [expand_vars(t, env) for t in tokens]
        redir = Redirection()
        argv: List[str] = []
        it = iter(range(len(tokens)))
        i = 0
        while i < len(tokens):
            t = tokens[i]
            if t == '<' and i + 1 < len(tokens):
                redir.stdin = tokens[i + 1]
                i += 2
                continue
            if t == '>' and i + 1 < len(tokens):
                redir.stdout = tokens[i + 1]
                redir.stdout_append = False
                i += 2
                continue
            if t == '>>' and i + 1 < len(tokens):
                redir.stdout = tokens[i + 1]
                redir.stdout_append = True
                i += 2
                continue
            if t == '2>' and i + 1 < len(tokens):
                redir.stderr = tokens[i + 1]
                redir.stderr_append = False
                i += 2
                continue
            if t == '2>>' and i + 1 < len(tokens):
                redir.stderr = tokens[i + 1]
                redir.stderr_append = True
                i += 2
                continue
            if t == '2>&1':
                redir.stderr_to_stdout = True
                i += 1
                continue
            argv.append(t)
            i += 1
        argv = expand_globs(argv)
        pipeline.append(Command(argv=argv, redir=redir))
    return pipeline


BUILTINS = ('cd', 'pwd', 'exit', 'set', 'export', 'which')

def run_builtin(argv: List[str], env: Dict[str, str]) -> int:
    cmd = argv[0]
    if cmd == 'cd':
        target = argv[1] if len(argv) > 1 else env.get('HOME', HOME)
        try:
            os.chdir(os.path.expanduser(target))
            return 0
        except Exception as e:
            print(f"cd: {e}", file=sys.stderr)
            return 1
    if cmd == 'pwd':
        print(os.getcwd())
        return 0
    if cmd == 'exit':
        code = int(argv[1]) if len(argv) > 1 and argv[1].isdigit() else 0
        sys.exit(code)
    if cmd == 'set':
        if len(argv) == 1:
            for k, v in env.items():
                print(f"{k}={v}")
            return 0
        for item in argv[1:]:
            if '=' in item:
                k, v = item.split('=', 1)
                env[k] = v
        return 0
    if cmd == 'export':
        for item in argv[1:]:
            if '=' in item:
                k, v = item.split('=', 1)
                env[k] = v
                os.environ[k] = v
        return 0
    if cmd == 'which':
        for a in argv[1:]:
            path = shutil_which(a)
            if path:
                print(path)
            else:
                print(f"which: no {a} in PATH", file=sys.stderr)
        return 0
    return 1


def shutil_which(cmd: str) -> Optional[str]:
    # Avoid importing shutil.which to keep minimal
    exts = os.environ.get('PATHEXT', '.EXE;.BAT;.CMD').split(';') if IS_WINDOWS else ['']
    if os.path.isabs(cmd) and os.access(cmd, os.X_OK):
        return cmd
    paths = os.environ.get('PATH', '').split(os.pathsep)
    for p in paths:
        candidate = os.path.join(p, cmd)
        if os.access(candidate, os.X_OK):
            return candidate
        if IS_WINDOWS:
            for e in exts:
                cand2 = candidate + e
                if os.path.exists(cand2):
                    return cand2
    return None


def launch_pipeline(pipeline: List[Command], env: Dict[str, str]) -> int:
    num = len(pipeline)
    procs: List[subprocess.Popen] = []
    prev_stdout = None
    for idx, cmd in enumerate(pipeline):
        if not cmd.argv:
            continue
        # Builtins only valid when single command and no pipe
        if num == 1 and cmd.argv[0] in BUILTINS:
            return run_builtin(cmd.argv, env)
        stdin = None
        stdout = None
        stderr = None
        # stdin redirection
        if cmd.redir.stdin:
            stdin = open(cmd.redir.stdin, 'rb')
        elif prev_stdout is not None:
            stdin = prev_stdout
        # stdout redirection or pipe
        if idx < num - 1:
            stdout = subprocess.PIPE
        elif cmd.redir.stdout:
            mode = 'ab' if cmd.redir.stdout_append else 'wb'
            stdout = open(cmd.redir.stdout, mode)
        # stderr
        if cmd.redir.stderr_to_stdout:
            stderr = subprocess.STDOUT
        elif cmd.redir.stderr:
            mode = 'ab' if cmd.redir.stderr_append else 'wb'
            stderr = open(cmd.redir.stderr, mode)
        # Resolve executable
        exe = cmd.argv[0]
        if not os.path.isabs(exe):
            located = shutil_which(exe)
            if located:
                exe = located
        try:
            p = subprocess.Popen(
                [exe] + cmd.argv[1:],
                stdin=stdin,
                stdout=stdout or sys.stdout.buffer,
                stderr=stderr or sys.stderr.buffer,
                env=env,
                cwd=os.getcwd(),
                shell=False,
            )
        except FileNotFoundError:
            print(f"command not found: {cmd.argv[0]}", file=sys.stderr)
            # Close inherited pipe from prev to avoid hanging
            if prev_stdout and prev_stdout is not sys.stdin.buffer:
                try:
                    prev_stdout.close()  # type: ignore
                except Exception:
                    pass
            return 127
        if prev_stdout and prev_stdout is not sys.stdin.buffer:
            try:
                prev_stdout.close()
            except Exception:
                pass
        prev_stdout = p.stdout if p.stdout else None
        procs.append(p)
    # Wait and propagate last exit code
    last_code = 0
    for p in procs:
        p.wait()
        last_code = p.returncode
    return last_code


def split_commands(line: str) -> List[str]:
    # split on ';' but not inside quotes
    result: List[str] = []
    buf = ''
    q = None
    for ch in line:
        if ch in ('"', "'"):
            if q is None:
                q = ch
            elif q == ch:
                q = None
        if ch == ';' and q is None:
            if buf.strip():
                result.append(buf.strip())
            buf = ''
        else:
            buf += ch
    if buf.strip():
        result.append(buf.strip())
    return result


def main() -> int:
    env = dict(os.environ)
    env.setdefault('TERM', 'xterm-256color')
    env.setdefault('HOME', HOME)
    while True:
        try:
            cwd = os.getcwd()
            prompt = f"{cwd}$ "
            line = input(prompt)
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line.strip():
            continue
        for cmd_str in split_commands(line):
            try:
                pipeline = parse_pipeline(cmd_str, env)
                code = launch_pipeline(pipeline, env)
                # If desired, could stop on non-zero; keep going for now
            except Exception as e:
                print(f"error: {e}", file=sys.stderr)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
