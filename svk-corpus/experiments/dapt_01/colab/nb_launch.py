#!/usr/bin/env python3
"""DAPT-01 notebook launcher — start detached training without blocking the kernel."""
from __future__ import annotations
import json, os, subprocess, sys, time
from pathlib import Path

CONTENT = Path("/content")
WORKER = CONTENT / "dapt_train_worker.py"
RELAY = CONTENT / "relaunch_worker.py"
PIDF = CONTENT / "dapt_train.pid"
STATUS_PUSH = CONTENT / "status_pusher.py"


def pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def ensure_worker_running() -> int | None:
    if PIDF.exists():
        try:
            pid = int(PIDF.read_text().strip())
            if pid_alive(pid):
                print(f"ALREADY_RUNNING pid={pid}", flush=True)
                return pid
        except Exception:
            pass
    if not WORKER.exists():
        print("ERROR worker missing", flush=True)
        return None
    env_path = CONTENT / "dapt_train_env.json"
    # relay reads env from process env or file
    if RELAY.exists():
        r = subprocess.run(
            [sys.executable, "-u", str(RELAY)],
            capture_output=True, text=True, timeout=120,
        )
        print(r.stdout, flush=True)
        if r.stderr:
            print(r.stderr, file=sys.stderr, flush=True)
        if r.returncode != 0:
            print(f"RELAY_FAIL rc={r.returncode}", flush=True)
            return None
    else:
        print("ERROR relaunch_worker.py missing", flush=True)
        return None
    if PIDF.exists():
        try:
            return int(PIDF.read_text().strip())
        except Exception:
            return None
    return None


def ensure_status_pusher() -> None:
    # kill old pusher
    subprocess.run(
        "ps -eo pid,cmd | grep '[s]tatus_pusher.py loop' | awk '{print $1}' | xargs -r kill || true",
        shell=True,
    )
    time.sleep(0.5)
    if not STATUS_PUSH.exists():
        print("WARN status_pusher missing", flush=True)
        return
    env = os.environ.copy()
    env["STATUS_INTERVAL"] = "60"
    with open("/content/status_pusher.log", "a") as out:
        p = subprocess.Popen(
            [sys.executable, "-u", str(STATUS_PUSH), "loop"],
            stdout=out, stderr=out,
            env=env, start_new_session=True, cwd="/content",
        )
    (CONTENT / "status_pusher.pid").write_text(str(p.pid))
    print(f"STATUS_PUSHER pid={p.pid}", flush=True)


def main() -> int:
    print("=== DAPT-01 launch ===", flush=True)
    print("gpu check later in worker; starting...", flush=True)
    pid = ensure_worker_running()
    if pid is None:
        return 1
    print(f"WORKER pid={pid}", flush=True)
    ensure_status_pusher()
    time.sleep(2)
    # quick status
    st = CONTENT / "dapt_train_status.json"
    if st.exists():
        print(st.read_text(), flush=True)
    log = CONTENT / "dapt_train_worker.log"
    if log.exists():
        lines = log.read_text(errors="ignore").splitlines()[-20:]
        print("--- worker log tail ---", flush=True)
        print("\n".join(lines), flush=True)
    print("LAUNCH_OK", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
