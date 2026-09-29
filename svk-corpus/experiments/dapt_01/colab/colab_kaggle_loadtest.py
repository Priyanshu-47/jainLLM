"""Phase 8: download public Kaggle datasets on Colab + LOAD TEST ONLY (no training)."""
import json, os, subprocess, sys, shutil, zipfile, tarfile
from pathlib import Path

def sh(cmd, env=None):
    print(f"$ {cmd}", flush=True)
    r = subprocess.run(cmd, shell=True, env=env, capture_output=True, text=True)
    print(r.stdout)
    if r.stderr:
        print(r.stderr, file=sys.stderr)
    if r.returncode != 0:
        raise SystemExit(f"cmd failed rc={r.returncode}: {cmd}")
    return r

# 1) Install kaggle if needed and configure from env (no token in source)
token = os.environ.get("KAGGLE_API_TOKEN") or os.environ.get("KAGGLE_KEY")
user = os.environ.get("KAGGLE_USERNAME", "Priyanshu47")
if not token:
    print("FATAL: KAGGLE_API_TOKEN not set in env"); sys.exit(2)

cfg_dir = Path.home() / ".kaggle"
cfg_dir.mkdir(exist_ok=True)
cfg = cfg_dir / "kaggle.json"
cfg.write_text(json.dumps({"username": user, "key": token}))
cfg.chmod(0o600)

# pip install kaggle if needed
try:
    import kaggle  # noqa
except ImportError:
    sh(f"{sys.executable} -m pip install -q kaggle")

env = os.environ.copy()
env["KAGGLE_CONFIG_DIR"] = str(cfg_dir)
env["KAGGLE_API_TOKEN"] = token
env["KAGGLE_USERNAME"] = user
env["KAGGLE_KEY"] = token

content = Path("/content")
# 2) Download domain_train (small enough) and checkpoint
for slug, dest in [
    ("priyanshu47/jainllm-domain-train", "/content/domain_train"),
    ("priyanshu47/dapt01-checkpoint-3893", "/content/ck_dl"),
]:
    print(f"=== download {slug} ===", flush=True)
    sh(f"kaggle datasets download -d {slug} -p {dest} --unzip", env=env)

# 3) Layout checkpoint dir
ck = content / "checkpoint-3893"
if ck.exists():
    shutil.rmtree(ck)
ck.mkdir()
# files may be loose under ck_dl
src_root = content / "ck_dl"
# If zip contained a folder, find files
candidates = list(src_root.rglob("adapter_config.json"))
if candidates:
    # copy everything from that parent
    parent = candidates[0].parent
    for p in parent.iterdir():
        if p.is_file():
            shutil.copy2(p, ck / p.name)
else:
    for p in src_root.iterdir():
        if p.is_file() and p.suffix != ".zip":
            shutil.copy2(p, ck / p.name)

print("ckpt files:", sorted(x.name for x in ck.iterdir()), flush=True)

# 4) data layout check
dt = content / "domain_train"
print("domain_train:", sorted(x.name for x in dt.iterdir()) if dt.exists() else "MISSING", flush=True)

# 5) Run load test (LOAD ONLY)
load_script = content / "checkpoint_load_test.py"
if not load_script.exists():
    # fallback: write inline minimal if upload missing
    print("checkpoint_load_test.py missing — will fail intentionally if required files also missing")
env2 = os.environ.copy()
env2["DAPT_CKPT"] = str(ck)
r = subprocess.run([sys.executable, str(load_script)], env=env2, capture_output=True, text=True, timeout=1800)
print(r.stdout)
print(r.stderr, file=sys.stderr)
print("load_test_exit:", r.returncode, flush=True)
rep = content / "checkpoint_load_test_report.json"
if rep.exists():
    print("REPORT_JSON_START")
    print(rep.read_text())
    print("REPORT_JSON_END")

# 6) Dry-run resume runner (no --execute)
rr = content / "resume_dapt_colab.py"
if rr.exists():
    r2 = subprocess.run([sys.executable, str(rr), "--dry-run", "--ckpt", str(ck), "--data", str(dt)],
                        capture_output=True, text=True, timeout=120)
    print(r2.stdout)
    print(r2.stderr, file=sys.stderr)
    print("resume_dry_exit:", r2.returncode, flush=True)

sys.exit(r.returncode)
