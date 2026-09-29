#!/usr/bin/env python3
"""
DAPT-01 resume runner (Colab). Detects global_step; trains to --target-step.

Default: dry-run. Requires --execute to train.
Never modifies the source checkpoint in place; works on a copy under output_dir.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import time
from pathlib import Path

LOCKED = {
    "model": "Qwen/Qwen3-8B-Base",
    "lora_r": 16,
    "lora_alpha": 32,
    "lora_dropout": 0.05,
    "lr": 2e-4,
    "scheduler": "cosine",
    "warmup_ratio": 0.03,
    "max_seq_length": 2048,
    "batch": 1,
    "grad_accum": 16,
    "seed": 42,
    "total_steps": 15248,
    "save_steps": 500,
    "target_modules": ["q_proj","k_proj","v_proj","o_proj","gate_proj","up_proj","down_proj"],
}


def detect_step(ckpt: Path) -> int:
    state = ckpt / "trainer_state.json"
    if not state.exists():
        raise FileNotFoundError(f"missing {state}")
    with open(state) as f:
        ts = json.load(f)
    step = int(ts["global_step"])
    max_steps = int(ts.get("max_steps", LOCKED["total_steps"]))
    if max_steps != LOCKED["total_steps"]:
        raise ValueError(f"max_steps drift: {max_steps} != {LOCKED['total_steps']}")
    return step


def verify_adapter_config(ckpt: Path) -> dict:
    with open(ckpt / "adapter_config.json") as f:
        ac = json.load(f)
    assert ac.get("base_model_name_or_path") == LOCKED["model"], ac.get("base_model_name_or_path")
    assert ac.get("r") == LOCKED["lora_r"]
    assert ac.get("lora_alpha") == LOCKED["lora_alpha"]
    assert ac.get("lora_dropout") == LOCKED["lora_dropout"]
    assert set(ac.get("target_modules") or []) == set(LOCKED["target_modules"])
    return ac


def next_checkpoint_step(step: int, save_steps: int) -> int:
    return ((step // save_steps) + 1) * save_steps


def snapshot_known_good(ckpt: Path, backup_root: Path) -> Path:
    backup_root.mkdir(parents=True, exist_ok=True)
    step = detect_step(ckpt)
    dest = backup_root / f"known_good_step_{step}"
    if dest.exists():
        return dest
    dest.mkdir(parents=True)
    for name in [
        "adapter_model.safetensors", "adapter_config.json", "trainer_state.json",
        "optimizer.pt", "scheduler.pt", "training_args.bin",
        "tokenizer.json", "tokenizer_config.json",
    ]:
        src = ckpt / name
        if src.exists():
            shutil.copy2(src, dest / name)
    (dest / "SOURCE_STEP.txt").write_text(str(step))
    return dest


def prepare_output_checkpoint(ckpt: Path, output_dir: Path, step: int) -> Path:
    """Copy resume source into output_dir/checkpoint-<step> without touching original."""
    dst = output_dir / f"checkpoint-{step}"
    if dst.exists() and (dst / "trainer_state.json").exists():
        return dst
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(ckpt, dst)
    return dst


def build_trainer(ckpt: Path, data_dir: Path, output_dir: Path, target_abs: int, save_steps: int):
    import torch
    from transformers import (
        AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig,
        TrainingArguments, Trainer, DataCollatorForLanguageModeling,
    )
    from peft import PeftModel, prepare_model_for_kbit_training
    from datasets import load_dataset

    step = detect_step(ckpt)
    verify_adapter_config(ckpt)
    if target_abs <= step:
        raise ValueError(f"target_abs {target_abs} must be > current step {step}")
    if target_abs > LOCKED["total_steps"]:
        raise ValueError(f"target_abs {target_abs} > total {LOCKED['total_steps']}")
    print(f"[runner] resume from global_step={step} -> target={target_abs} "
          f"({target_abs - step} steps, save_steps={save_steps})", flush=True)

    tok = AutoTokenizer.from_pretrained(ckpt, trust_remote_code=True)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    bnb = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
    )
    try:
        base = AutoModelForCausalLM.from_pretrained(
            LOCKED["model"], dtype=torch.float16, device_map="auto",
            quantization_config=bnb, trust_remote_code=True,
        )
    except TypeError:
        base = AutoModelForCausalLM.from_pretrained(
            LOCKED["model"], torch_dtype=torch.float16, device_map="auto",
            quantization_config=bnb, trust_remote_code=True,
        )
    base = prepare_model_for_kbit_training(base, use_gradient_checkpointing=True)
    model = PeftModel.from_pretrained(base, ckpt, is_trainable=True)

    ds = load_dataset(
        "json",
        data_files={
            "train": str(data_dir / "train.jsonl"),
            "validation": str(data_dir / "val.jsonl"),
        },
    )

    cols = ds["train"].column_names
    if "text" in cols:
        def tok_fn(examples):
            return tok(
                examples["text"],
                truncation=True,
                max_length=LOCKED["max_seq_length"],
                padding=False,
            )
        ds = ds.map(tok_fn, batched=True, remove_columns=cols)

    args = TrainingArguments(
        output_dir=str(output_dir),
        overwrite_output_dir=False,
        max_steps=target_abs,
        per_device_train_batch_size=LOCKED["batch"],
        gradient_accumulation_steps=LOCKED["grad_accum"],
        learning_rate=LOCKED["lr"],
        lr_scheduler_type="cosine",
        warmup_ratio=LOCKED["warmup_ratio"],
        warmup_steps=0,
        weight_decay=0.01,
        max_grad_norm=1.0,
        seed=LOCKED["seed"],
        fp16=True,
        bf16=False,
        optim="adamw_torch",
        logging_steps=10,
        save_steps=save_steps,
        save_strategy="steps",
        save_total_limit=3,
        report_to=[],
        eval_strategy="no",
        load_best_model_at_end=False,
        remove_unused_columns=True,
        dataloader_num_workers=0,
        gradient_checkpointing=True,
    )
    args.warmup_steps = 0

    collator = DataCollatorForLanguageModeling(tokenizer=tok, mlm=False)
    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=ds["train"],
        eval_dataset=None,
        data_collator=collator,
        processing_class=tok,
    )
    return trainer, step, target_abs


class TimeSafetyCallback:
    """Minimal callback: stop before session deadline; last checkpoint preserved."""
    def __init__(self, timeout_sec: float):
        self.t0 = time.time()
        self.timeout_sec = timeout_sec

    def on_step_end(self, args, state, control, **kwargs):
        elapsed = time.time() - self.t0
        if elapsed > self.timeout_sec:
            control.should_training_stop = True
            print(f"\n[TIME SAFETY] stop at step {state.global_step} after {elapsed/60:.1f} min",
                  flush=True)
        return control


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", default="/content/checkpoint-3893")
    ap.add_argument("--data", default="/content/domain_train")
    ap.add_argument("--output", default="/content/dapt-01-output")
    ap.add_argument("--backup-root", default="/content/dapt_known_good")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--target-step", type=int, default=0,
                    help="absolute global step to train through (0 => next save boundary)")
    ap.add_argument("--max-steps-in-session", type=int, default=0,
                    help="alternative: step + N (ignored if --target-step set)")
    ap.add_argument("--session-timeout-min", type=int, default=90)
    args = ap.parse_args()

    ckpt = Path(args.ckpt)
    step = detect_step(ckpt)
    verify_adapter_config(ckpt)
    save_steps = LOCKED["save_steps"]
    auto_target = next_checkpoint_step(step, save_steps)
    if args.target_step:
        target = args.target_step
    elif args.max_steps_in_session:
        target = min(LOCKED["total_steps"], step + args.max_steps_in_session)
    else:
        target = auto_target

    facts = {
        "global_step": step,
        "target_step": target,
        "auto_next_checkpoint": auto_target,
        "steps_to_run": target - step,
        "save_steps": save_steps,
        "remaining_after_target": LOCKED["total_steps"] - target,
        "locked": LOCKED,
    }
    print(json.dumps(facts, indent=2), flush=True)

    if not args.execute or args.dry_run:
        print("[runner] DRY RUN complete — training NOT started.", flush=True)
        return 0

    if target <= step:
        raise SystemExit(f"target {target} <= current {step}")

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    backup = snapshot_known_good(ckpt, Path(args.backup_root))
    print(f"[runner] known-good snapshot -> {backup}", flush=True)

    resume_ckpt = prepare_output_checkpoint(ckpt, out, step)
    print(f"[runner] resume checkpoint at {resume_ckpt}", flush=True)

    trainer, step, target = build_trainer(ckpt, Path(args.data), out, target, save_steps)
    trainer.add_callback(TimeSafetyCallback(args.session_timeout_min * 60))

    print(f"[runner] TRAINING resume_from_checkpoint={resume_ckpt} max_steps={target}", flush=True)
    t0 = time.time()
    result = trainer.train(resume_from_checkpoint=str(resume_ckpt))
    elapsed = time.time() - t0

    final_step = int(getattr(trainer.state, "global_step", -1))
    # Ensure a resumable checkpoint exists at final_step
    final_ckpt = out / f"checkpoint-{final_step}"
    if not (final_ckpt / "trainer_state.json").exists():
        final_ckpt.mkdir(parents=True, exist_ok=True)
        trainer.save_model(str(final_ckpt))
        tok_src = ckpt
        for name in ["tokenizer.json", "tokenizer_config.json", "special_tokens_map.json",
                     "chat_template.jinja", "README.md"]:
            src = tok_src / name
            if src.exists():
                shutil.copy2(src, final_ckpt / name)
        if trainer.optimizer is not None:
            import torch
            torch.save(trainer.optimizer.state_dict(), final_ckpt / "optimizer.pt")
        if trainer.lr_scheduler is not None:
            import torch
            torch.save(trainer.lr_scheduler.state_dict(), final_ckpt / "scheduler.pt")
        trainer.state.save_to_json(final_ckpt / "trainer_state.json")
        import torch
        torch.save(trainer.args, final_ckpt / "training_args.bin")

    trainer.save_model(str(out / "final_adapter"))
    (out / "LAST_RUN.json").write_text(json.dumps({
        "started_from": step,
        "final_step": final_step,
        "target": target,
        "elapsed_sec": elapsed,
        "train_metrics": result.metrics if result else {},
        "timestamp": time.time(),
    }, indent=2))
    print(f"[runner] done final_step={final_step} elapsed_sec={elapsed:.1f}", flush=True)
    # list checkpoints
    print("checkpoints:", sorted(p.name for p in out.glob("checkpoint-*")), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
