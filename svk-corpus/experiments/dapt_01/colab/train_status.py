import json
from pathlib import Path
import os
import time

print("=== DAPT-01 STATUS ===", flush=True)
print("iso", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), flush=True)

for p in [
    "/content/dapt_train_status.json",
    "/content/dapt_train.pid",
    "/content/status_pusher.pid",
    "/content/dapt-01-output/LAST_RUN.json",
]:
    path = Path(p)
    if path.exists():
        print(f"== {p} ==", flush=True)
        print(path.read_text()[:3000], flush=True)

# worker alive?
pidf = Path("/content/dapt_train.pid")
if pidf.exists():
    pid = int(pidf.read_text().strip())
    try:
        os.kill(pid, 0)
        print(f"worker pid {pid} ALIVE", flush=True)
    except ProcessLookupError:
        print(f"worker pid {pid} DEAD", flush=True)

# logs
for p in [
    "/content/dapt_train_worker.log",
    "/content/dapt_train_stdout.log",
    "/content/dapt_train_stderr.log",
    "/content/status_pusher.log",
]:
    path = Path(p)
    if path.exists():
        lines = path.read_text(errors="ignore").splitlines()[-40:]
        print(f"== tail {p} ==", flush=True)
        print("\n".join(lines), flush=True)

ck = Path("/content/dapt-01-output")
if ck.exists():
    names = sorted(
        (x.name for x in ck.glob("checkpoint-*")),
        key=lambda n: int(n.split("-")[-1]) if n.split("-")[-1].isdigit() else -1,
    )
    print("checkpoints", names, flush=True)
    for n in reversed(names):
        ts = ck / n / "trainer_state.json"
        if ts.exists():
            print("global_step", json.loads(ts.read_text()).get("global_step"), flush=True)
            break

# gpu
try:
    import torch
    print("cuda", torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else None, flush=True)
except Exception as e:
    print("torch check failed", e, flush=True)

print("=== END STATUS ===", flush=True)
