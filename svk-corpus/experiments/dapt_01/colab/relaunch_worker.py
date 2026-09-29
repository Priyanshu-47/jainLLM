#!/usr/bin/env python3
import json, os, subprocess, sys, time
from pathlib import Path

def main():
    content = Path("/content")
    worker = content / "dapt_train_worker.py"
    assert worker.exists(), "worker missing"
    pidf = content / "dapt_train.pid"
    if pidf.exists():
        try:
            pid = int(pidf.read_text().strip()); os.kill(pid, 9); print("killed old", pid)
        except Exception as e:
            print("old pid cleanup", e)
    subprocess.run("pkill -9 -f dapt_train_worker.py || true", shell=True)
    subprocess.run("pkill -9 -f dapt_train_wrap.py || true", shell=True)
    time.sleep(1)
    for name in ["dapt_train_worker.log","dapt_train_stdout.log","dapt_train_stderr.log"]:
        p = content / name
        if p.exists(): p.write_text("")
    (content / "dapt_train_status.json").write_text(json.dumps({
        "ts": time.time(), "from": 3893, "target": 5500, "state": "relaunching"
    }))
    env_path = content / "dapt_train_env.json"
    token = os.environ.get("KAGGLE_API_TOKEN") or os.environ.get("KAGGLE_KEY")
    if token:
        env_path.write_text(json.dumps({
            "KAGGLE_API_TOKEN": token,
            "KAGGLE_KEY": token,
            "KAGGLE_USERNAME": os.environ.get("KAGGLE_USERNAME", "Priyanshu47"),
            "DAPT_TARGET_STEP": "5500",
        }))
        os.chmod(env_path, 0o600)
    elif not env_path.exists():
        raise SystemExit("no kaggle env")
    env = os.environ.copy()
    try:
        for k,v in json.loads(env_path.read_text()).items():
            if v: env[k]=v
    except Exception:
        pass
    with open("/content/dapt_train_stdout.log", "a") as out, open("/content/dapt_train_stderr.log", "a") as err:
        p = subprocess.Popen([sys.executable, "-u", str(worker)], stdout=out, stderr=err,
                             env=env, start_new_session=True, cwd="/content")
    pidf.write_text(str(p.pid))
    print(f"RELAUNCHED pid={p.pid}")
    time.sleep(3)
    try:
        os.kill(p.pid, 0); print("ALIVE")
    except ProcessLookupError:
        print("DIED_EARLY")
        errp = content / "dapt_train_stderr.log"
        if errp.exists(): print(errp.read_text()[-2000:])
        return 1
    subprocess.run([sys.executable, "-u", "/content/train_status.py"])
    return 0

if __name__ == "__main__":
    sys.exit(main())
