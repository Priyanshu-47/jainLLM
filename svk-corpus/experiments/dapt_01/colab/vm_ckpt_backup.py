#!/usr/bin/env python3
"""Poll Colab session for new checkpoints; download each to local VM backup."""
from __future__ import annotations
import json, os, subprocess, sys, time, shutil
from pathlib import Path

SESSION = "dapt57"
BACKUP = Path("/home/azureuser/jainLLM/svk-corpus/experiments/dapt_01/checkpoints_vm_backup")
BACKUP.mkdir(parents=True, exist_ok=True)
KNOWN_FILE = BACKUP / ".known_steps.json"
LOG = BACKUP / "backup_poll.log"
INTERVAL = int(os.environ.get("BACKUP_INTERVAL", "60"))
COLAB = ["colab", "--auth=adc"]
PATH_ENV = os.environ.copy()
PATH_ENV["PATH"] = "/home/azureuser/.local/bin:" + PATH_ENV.get("PATH", "")


def log(msg: str):
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}"
    print(line, flush=True)
    with LOG.open("a") as f:
        f.write(line + "\n")


def run(args, timeout=120):
    r = subprocess.run(args, capture_output=True, text=True, timeout=timeout, env=PATH_ENV)
    return r.returncode, r.stdout, r.stderr


def known() -> set[int]:
    if KNOWN_FILE.exists():
        try:
            return set(json.loads(KNOWN_FILE.read_text()))
        except Exception:
            return set()
    return set()


def save_known(steps: set[int]):
    KNOWN_FILE.write_text(json.dumps(sorted(steps)))


def list_remote_ckpts() -> list[str]:
    rc, out, err = run(COLAB + ["ls", "-s", SESSION, "/content/dapt-01-output"], timeout=60)
    if rc != 0:
        log(f"ls fail rc={rc} {err[:200]}")
        return []
    names = []
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("checkpoint-"):
            names.append(line.split()[0])
    return names


def step_of(name: str) -> int | None:
    try:
        return int(name.split("-")[-1])
    except Exception:
        return None


def ensure_trainer_state(name: str) -> bool:
    """Check remote trainer_state.json exists (complete save)."""
    rc, out, err = run(
        COLAB + ["exec", "-s", SESSION, "--timeout", "30"],
        timeout=45,
    )
    # better: use download of small file
    local_tmp = Path(f"/tmp/colab_xfer/_ts_{name}.json")
    if local_tmp.exists():
        local_tmp.unlink()
    rc, out, err = run(
        COLAB + ["download", "-s", SESSION,
                 f"/content/dapt-01-output/{name}/trainer_state.json",
                 str(local_tmp)],
        timeout=60,
    )
    if rc != 0 or not local_tmp.exists():
        return False
    try:
        json.loads(local_tmp.read_text())
        return True
    except Exception:
        return False


def download_ckpt(name: str) -> bool:
    dest = BACKUP / name
    if dest.exists() and (dest / "trainer_state.json").exists():
        log(f"already have {name}")
        return True
    tmp = BACKUP / f".tmp_{name}"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    # download whole directory
    rc, out, err = run(
        COLAB + ["download", "-s", SESSION,
                 f"/content/dapt-01-output/{name}", str(tmp)],
        timeout=900,
    )
    # colab download of dir may put files under tmp/name or flatten
    candidates = list(tmp.rglob("trainer_state.json"))
    if not candidates:
        # try per-file list
        rc2, out2, err2 = run(
            COLAB + ["ls", "-s", SESSION, f"/content/dapt-01-output/{name}"],
            timeout=45,
        )
        files = [ln.strip().split()[0] for ln in out2.splitlines() if ln.strip() and not ln.startswith("total")]
        for fn in files:
            if fn in (".", "..") or fn.startswith("/"):
                continue
            run(
                COLAB + ["download", "-s", SESSION,
                         f"/content/dapt-01-output/{name}/{fn}",
                         str(tmp / fn)],
                timeout=600,
            )
        candidates = list(tmp.rglob("trainer_state.json"))
    if not candidates:
        log(f"FAIL download {name}: no trainer_state (rc={rc} err={err[:200]})")
        shutil.rmtree(tmp, ignore_errors=True)
        return False
    # normalize into dest
    if dest.exists():
        shutil.rmtree(dest)
    src_dir = candidates[0].parent
    shutil.move(str(src_dir), str(dest))
    shutil.rmtree(tmp, ignore_errors=True)
    ts = json.loads((dest / "trainer_state.json").read_text())
    log(f"BACKUP_OK {name} step={ts.get('global_step')} files={len(list(dest.iterdir()))}")
    return True


def poll_once():
    names = list_remote_ckpts()
    steps_known = known()
    for name in sorted(names, key=lambda n: step_of(n) or -1):
        st = step_of(name)
        if st is None:
            continue
        if st <= 3893:
            continue  # source resume ckpt not a new save
        if st in steps_known:
            continue
        if not ensure_trainer_state(name):
            log(f"skip incomplete {name}")
            continue
        if download_ckpt(name):
            steps_known.add(st)
            save_known(steps_known)


def main():
    log(f"VM_CKPT_BACKUP start interval={INTERVAL}s dest={BACKUP}")
    while True:
        try:
            poll_once()
        except Exception as e:
            log(f"POLL_FAIL {e}")
        time.sleep(INTERVAL)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "once":
        poll_once()
    else:
        main()
