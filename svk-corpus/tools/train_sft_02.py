#!/usr/bin/env python3
"""SFT-02 entrypoint: preflight + launch preparation (Task 68).

This tool does NOT start training. It verifies that every input SFT-02 needs
exists and is consistent with the locked Task-67 config, then emits the exact
Kaggle launch commands. The training code lives in
experiments/sft_02/kaggle/train.py (self-contained Kaggle session script).

Usage:
    python3 tools/train_sft_02.py            # preflight (default)
    python3 tools/train_sft_02.py --launch   # preflight + print launch commands
    python3 tools/train_sft_02.py --emit     # preflight + write scripts/run_sft_02.sh
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone

import yaml

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

CONFIG_PATH = os.path.join(ROOT, "configs", "sft_qwen3_8b_sft02_v1.yaml")
SHELL_PATH = os.path.join(ROOT, "scripts", "run_sft_02.sh")
KAGGLE_DIR = os.path.join(ROOT, "experiments", "sft_02", "kaggle")
TASK67_REPORT = os.path.join(ROOT, "data", "reports", "task67_sft02_dataset.json")

TRAIN_SHA = "3a45925f7f3e3c8d7beaecff4b1a6ac14592dc12b9849c8b70c32bb328b5b7e5"
EVAL_SHA = "ba59533699b28328e4dc9e5fa3df1c24a0b026824bafc852cfc703f38e6fcc35"
FROZEN_SHA = "06625f72190e3ae130447345afdc04342bd19cb76f842285706480cba7765b81"

SECRET_RE = re.compile(
    r"(?i)(kaggle_?username|kaggle_?key|api_?key|secret|token|password|passwd)"
    r"\s*[:=]\s*[\"']?[a-z0-9]{8,}"
)
CREDENTIAL_PAT = re.compile(r"\b[0-9a-f]{40}\b|kaggle\.json|KAGGLE_USERNAME\s*=")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def preflight(cfg):
    checks = []

    def ok(name, passed, detail=""):
        checks.append((name, bool(passed), detail))

    model = cfg.get("model", {}).get("name", "")
    ok("model is Qwen3-8B-Base (not Instruct)",
       model == "Qwen/Qwen3-8B-Base", model)

    quant = cfg.get("quantization", {})
    ok("4-bit NF4 QLoRA quantization",
       quant.get("load_in_4bit") is True and quant.get("bnb_4bit_quant_type") == "nf4")

    lora = cfg.get("lora", {})
    ok("LoRA geometry locked to DAPT-01 (r16/a32/d0.05, 7 targets)",
       lora.get("r") == 16 and lora.get("lora_alpha") == 32
       and float(lora.get("lora_dropout") or 0) == 0.05
       and len(lora.get("target_modules") or []) == 7)

    adapter = cfg.get("adapter", {})
    ok("continues DAPT-01 checkpoint-15248 (NOT SFT-01)",
       "dapt01-checkpoint-15248" in str(adapter.get("continue_from", ""))
       and "sft01" not in str(adapter.get("continue_from", "")).lower()
       and adapter.get("is_trainable") is True,
       str(adapter.get("continue_from")))

    tr = cfg.get("training", {})
    ok("Task-66 hyperparameter corrections applied (lr 3e-5, epochs 2)",
       float(tr.get("learning_rate") or 0) == 3e-5
       and float(tr.get("num_train_epochs") or 0) == 2,
       f"lr={tr.get('learning_rate')} epochs={tr.get('num_train_epochs')}")

    ok("training settings per config (seq 2048, seed 42, save_total_limit 2, "
       "cosine, warmup 0.03, wd 0.01, fp16)",
       tr.get("max_seq_length") == 2048 and tr.get("seed") == 42
       and tr.get("save_total_limit") == 2
       and tr.get("lr_scheduler_type") == "cosine"
       and float(tr.get("warmup_ratio") or 0) == 0.03
       and float(tr.get("weight_decay") or 0) == 0.01
       and tr.get("fp16") is True and tr.get("bf16") is False,
       f"seq={tr.get('max_seq_length')} seed={tr.get('seed')} "
       f"save_total_limit={tr.get('save_total_limit')}")

    ok("output dir / run name per config",
       tr.get("output_dir") == "./outputs/sft-02"
       and tr.get("run_name") == "sft-02-qwen3-8b-dapt01-lineage",
       f"{tr.get('output_dir')} / {tr.get('run_name')}")

    ds = cfg.get("dataset", {})
    train_file = os.path.join(ROOT, ds.get("train_file", "").lstrip("./"))
    eval_file = os.path.join(ROOT, ds.get("eval_file", "").lstrip("./"))
    ok("train file exists", os.path.exists(train_file), ds.get("train_file", ""))
    ok("eval file exists", os.path.exists(eval_file), ds.get("eval_file", ""))

    if os.path.exists(train_file) and os.path.exists(eval_file):
        with open(train_file, encoding="utf-8") as fh:
            train_rows = [json.loads(l) for l in fh if l.strip()]
        with open(eval_file, encoding="utf-8") as fh:
            eval_rows = [json.loads(l) for l in fh if l.strip()]
        ok("row counts match config (61 train / 13 eval)",
           len(train_rows) == ds.get("train_rows") == 61
           and len(eval_rows) == ds.get("eval_rows") == 13,
           f"train={len(train_rows)}/{ds.get('train_rows')} "
           f"eval={len(eval_rows)}/{ds.get('eval_rows')}")
        ok("all rows are chat-format messages",
           all(len(r.get("messages") or []) >= 2
               and r["messages"][0]["role"] == "user"
               and r["messages"][-1]["role"] == "assistant"
               for r in train_rows + eval_rows))
        allow = set(ds.get("rights_allowlist") or [])
        ok("every row rights-cleared",
           all(r.get("rights_status") in allow for r in train_rows + eval_rows),
           str(sorted({r.get("rights_status") for r in train_rows + eval_rows})))
        all_ids = [r["example_id"] for r in train_rows + eval_rows]
        ok("no duplicate example_id", len(set(all_ids)) == len(all_ids))

        t_sha, e_sha = sha256_file(train_file), sha256_file(eval_file)
        ok("train/eval sha256 match Task-67 records",
           t_sha == TRAIN_SHA and e_sha == EVAL_SHA,
           f"train={t_sha} eval={e_sha}")

        if os.path.exists(TASK67_REPORT):
            with open(TASK67_REPORT, encoding="utf-8") as fh:
                report = json.load(fh)
            delivered = {d["path"]: d["sha256"] for d in report.get("deliverables", [])}
            ok("hashes match task67_sft02_dataset.json deliverables",
               delivered.get("data/training/sft_train_v2.jsonl") == t_sha
               and delivered.get("data/evaluation/sft_eval_v2.jsonl") == e_sha)
        else:
            ok("task67_sft02_dataset.json present", False, TASK67_REPORT)

    frozen = os.path.join(ROOT, "data", "evaluation", "dapt01_eval_cases.jsonl")
    ok("frozen 47-case eval untouched",
       os.path.exists(frozen) and sha256_file(frozen) == FROZEN_SHA)

    ev = cfg.get("evaluation", {})
    ok("config pins frozen benchmark sha256",
       ev.get("frozen_benchmark_sha256") == FROZEN_SHA
       and ev.get("frozen_benchmark_rows") == 47)

    ok("kaggle session script exists",
       os.path.exists(os.path.join(KAGGLE_DIR, "train.py")))
    ok("kaggle kernel metadata exists",
       os.path.exists(os.path.join(KAGGLE_DIR, "kernel-metadata.json")))

    blob = json.dumps(cfg, ensure_ascii=False)
    ok("no credentials in config", not SECRET_RE.search(blob)
       and not CREDENTIAL_PAT.search(blob))

    return checks


LAUNCH_STEPS = """\
# SFT-02 exact launch sequence (Task 68; run from the repo root)

# 1) Publish the SFT-02 dataset as a Kaggle dataset (one-time upload)
mkdir -p /tmp/sft02_data && \\
  cp data/training/sft_train_v2.jsonl /tmp/sft02_data/train.jsonl && \\
  cp data/evaluation/sft_eval_v2.jsonl /tmp/sft02_data/eval.jsonl && \\
  printf '{"id":"priyanshu471/jainllm-sft02-train","title":"SFT-02 train/eval (Task 68)",'
         '"licenses":[{"name":"CC0-1.0"}]}' > /tmp/sft02_data/dataset-metadata.json && \\
  kaggle datasets create -p /tmp/sft02_data --public

# 2) Push the SFT-02 kernel (GPU T4; attaches jainllm-sft02-train + dapt01-checkpoint-15248)
kaggle kernels push -p experiments/sft_02/kaggle

# 3) Watch the run
kaggle kernels status priyanshu471/sft-02-qlora-on-dapt-01-lineage-task-68
kaggle kernels output priyanshu471/sft-02-qlora-on-dapt-01-lineage-task-68 -p /tmp/sft02_out

# 4) The kernel writes sft02_train_report.json + final adapter; it uploads the
#    adapter to the Kaggle dataset priyanshu471/sft02-output (created on first run).
# 5) Infer kernel (experiments/sft_02/kaggle_infer) runs the frozen 47 cases +
#    the 13 held-out eval rows against that adapter.
"""


def emit_shell():
    os.makedirs(os.path.dirname(SHELL_PATH), exist_ok=True)
    content = f"""#!/bin/bash
# SFT-02: generated by tools/train_sft_02.py on {datetime.now(timezone.utc).isoformat()}
# Preflight only - this script never starts training by itself.
set -e
cd "$(dirname "$0")/.."

echo "=== SFT-02 preflight ==="
python3 tools/train_sft_02.py

cat <<'LAUNCH'
{LAUNCH_STEPS}LAUNCH
"""
    with open(SHELL_PATH, "w", encoding="utf-8") as fh:
        fh.write(content)
    os.chmod(SHELL_PATH, 0o755)
    return SHELL_PATH


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--launch", action="store_true", help="print exact Kaggle launch commands")
    ap.add_argument("--emit", action="store_true", help="write scripts/run_sft_02.sh")
    args = ap.parse_args(argv)

    cfg = load_config()
    checks = preflight(cfg)
    failures = 0
    print("=== SFT-02 preflight (Task 68) ===")
    for name, passed, detail in checks:
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}"
              + (f" -> {detail}" if detail and not passed else ""))
        failures += 0 if passed else 1
    print(f"preflight: {len(checks) - failures}/{len(checks)} checks passed")

    if args.emit:
        path = emit_shell()
        print(f"  wrote {os.path.relpath(path, ROOT)}")
    if args.launch:
        print("\n" + LAUNCH_STEPS)
    if failures:
        return 1
    print("\nNOTE: training was NOT started. Run with --launch to print the Kaggle commands.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
