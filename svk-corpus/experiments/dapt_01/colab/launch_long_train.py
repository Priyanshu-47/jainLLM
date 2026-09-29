#!/usr/bin/env python3
"""Start DAPT worker detached on this Colab VM; return immediately."""
import json, os, subprocess, sys, time
from pathlib import Path

WORKER = "/content/dapt_train_worker.py"
PIDF = Path("/content/dapt_train.pid")
LOG = Path("/content/dapt_train_launcher.log")

def main():
    # already running?
    if PIDF.exists():
        try:
            pid = int(PIDF.read_text().strip())
            os.kill(pid, 0)
            print(f"ALREADY_RUNNING pid={pid}")
            return 0
        except Exception:
            pass

    # ensure worker exists
    assert Path(WORKER).exists(), "worker missing"

    # propagate kaggle env into worker file? worker reads os.environ — pass via env file
    env_path = Path("/content/dapt_train_env.json")
    env_path.write_text(json.dumps({
        "KAGGLE_API_TOKEN": os.environ.get("KAGGLE_API_TOKEN") or os.environ.get("KAGGLE_KEY") or "",
        "KAGGLE_KEY": os.environ.get("KAGGLE_KEY") or os.environ.get("KAGGLE_API_TOKEN") or "",
        "KAGGLE_USERNAME": os.environ.get("KAGGLE_USERNAME", "Priyanshu47"),
        "DAPT_TARGET_STEP": os.environ.get("DAPT_TARGET_STEP", "5500"),
    }))
    os.chmod(env_path, 0o600)

    # wrapper loads env file then execs worker
    wrapper = Path("/content/dapt_train_wrap.py")
    wrapper.write_text(f'''
import json, os, runpy, sys
env = json.loads(open({str(env_path)!r}).read())
for k,v in env.items():
    if v: os.environ[k]=v
sys.argv = ["dapt_train_worker.py"]
runpy.run_path({WORKER!r}, run_name="__main__")
''')

    env = os.environ.copy()
    # load env file into this spawn too
    try:
        for k,v in json.loads(env_path.read_text()).items():
            if v: env[k]=v
    except Exception:
        pass

    # detach: new session, redirect logs
    with open("/content/dapt_train_stdout.log", "a") as out, open("/content/dapt_train_stderr.log", "a") as err:
        p = subprocess.Popen(
            [sys.executable, "-u", str(wrapper)],
            stdout=out, stderr=err,
            env=env,
            start_new_session=True,  # setsid — survives parent death
            cwd="/content",
        )
    PIDF.write_text(str(p.pid))
    print(f"LAUNCHED pid={p.pid} target={env.get('DAPT_TARGET_STEP','5500')}")
    time.sleep(3)
    # confirm alive
    try:
        os.kill(p.pid, 0)
        print("ALIVE")
    except ProcessLookupError:
        print("DIED_EARLY")
        return 1
    # show first lines of log
    for f in [Path("/content/dapt_train_stdout.log"), Path("/content/dapt_train_worker.log")]:
        if f.exists():
            lines = f.read_text(errors="ignore").splitlines()[-15:]
            print(f"--- {f.name} ---")
            print("\n".join(lines))
    return 0

if __name__ == "__main__":
    sys.exit(main())
