#!/usr/bin/env python3
"""Push training status + log tail to Kaggle so Azure VM is optional for polling."""
from __future__ import annotations
import json, os, shutil, sys, time, traceback
from pathlib import Path

SLUG = "Priyanshu47/dapt01-train-status"
INTERVAL = int(os.environ.get("STATUS_INTERVAL", "60"))
MAX_LOG_CHARS = 120_000


def _api():
    from kaggle.api.kaggle_api_extended import KaggleApi
    api = KaggleApi()
    api.authenticate()
    return api


def _read(path: Path, limit: int | None = None) -> str:
    if not path.exists():
        return ""
    try:
        t = path.read_text(errors="ignore")
    except Exception:
        return ""
    if limit and len(t) > limit:
        t = t[-limit:]
    return t


def snapshot(dst: Path) -> dict:
    dst.mkdir(parents=True, exist_ok=True)
    status = Path("/content/dapt_train_status.json")
    last = Path("/content/dapt-01-output/LAST_RUN.json")
    pidf = Path("/content/dapt_train.pid")
    worker_log = Path("/content/dapt_train_worker.log")
    stdout_log = Path("/content/dapt_train_stdout.log")
    stderr_log = Path("/content/dapt_train_stderr.log")

    payload = {
        "ts": time.time(),
        "iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": _read(status, 4000),
        "last_run": _read(last, 4000),
        "worker_log_tail": _read(worker_log, 40_000),
        "stdout_tail": _read(stdout_log, 20_000),
        "stderr_tail": _read(stderr_log, 20_000),
        "pid": None,
        "pid_alive": False,
        "checkpoints": [],
        "global_step": None,
    }
    if pidf.exists():
        try:
            pid = int(pidf.read_text().strip())
            payload["pid"] = pid
            os.kill(pid, 0)
            payload["pid_alive"] = True
        except Exception:
            payload["pid_alive"] = False
    try:
        payload["status_obj"] = json.loads(status.read_text()) if status.exists() else None
    except Exception:
        payload["status_obj"] = None
    out = Path("/content/dapt-01-output")
    if out.exists():
        cks = sorted(out.glob("checkpoint-*"), key=lambda p: int(p.name.split("-")[-1]) if p.name.split("-")[-1].isdigit() else -1)
        payload["checkpoints"] = [p.name for p in cks]
        for p in reversed(cks):
            ts_path = p / "trainer_state.json"
            if ts_path.exists():
                try:
                    payload["global_step"] = int(json.loads(ts_path.read_text())["global_step"])
                except Exception:
                    pass
                break
    # compact json for dataset
    (dst / "status.json").write_text(json.dumps(payload, indent=2))
    tail = payload["worker_log_tail"][-MAX_LOG_CHARS:]
    (dst / "worker_log_tail.txt").write_text(tail)
    (dst / "status_compact.txt").write_text(
        f"iso={payload['iso']}\n"
        f"state={(payload.get('status_obj') or {}).get('state')}\n"
        f"global_step={payload['global_step']}\n"
        f"pid={payload['pid']} alive={payload['pid_alive']}\n"
        f"checkpoints={payload['checkpoints']}\n"
        f"last_line={tail.splitlines()[-1] if tail.splitlines() else ''}\n"
    )
    return payload


def push_once(force: bool = False) -> None:
    stage = Path("/tmp/dapt_status_push")
    if stage.exists():
        shutil.rmtree(stage)
    payload = snapshot(stage)
    step = payload.get("global_step") or 0
    state = (payload.get("status_obj") or {}).get("state") or "unknown"
    (stage / "dataset-metadata.json").write_text(json.dumps({
        "title": "DAPT-01 train status",
        "id": SLUG,
        "licenses": [{"name": "CC0-1.0"}],
        "description": f"DAPT-01 live status step={step} state={state} (polled independent of Azure VM).",
    }, indent=2))
    api = _api()
    # Prefer create_new if dataset missing; fall back to version; tolerate 403 on version
    try:
        api.dataset_create_new(str(stage), public=True, quiet=True,
                               convert_to_csv=False, dir_mode="skip")
        print(f"PUSH_CREATE_OK step={step} state={state}", flush=True)
        return
    except Exception as e_new:
        msg = str(e_new).lower()
        if "already" in msg or "exists" in msg or "conflict" in msg or "409" in msg:
            pass  # dataset exists — version it
        else:
            # try version path anyway
            pass
    try:
        api.dataset_create_version(
            str(stage),
            version_notes=f"step={step} state={state} ts={int(time.time())}",
            quiet=True,
            convert_to_csv=False,
            dir_mode="skip",
        )
        print(f"PUSH_OK step={step} state={state} ts={payload['iso']}", flush=True)
    except Exception as e:
        print(f"PUSH_WARN version failed: {e}", flush=True)
        # last resort: create with slightly different id then abandon
        try:
            api.dataset_create_new(str(stage), public=True, quiet=True,
                                   convert_to_csv=False, dir_mode="skip")
            print(f"PUSH_CREATE_RETRY_OK step={step}", flush=True)
        except Exception as e2:
            print(f"PUSH_FAIL create: {e2}", flush=True)


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "once"
    if mode == "once":
        push_once()
        return 0
    print(f"STATUS_PUSHER start interval={INTERVAL}s", flush=True)
    while True:
        try:
            push_once()
        except Exception:
            print("PUSH_FAIL\n" + traceback.format_exc(), flush=True)
        time.sleep(INTERVAL)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        print(traceback.format_exc(), flush=True)
        sys.exit(1)
