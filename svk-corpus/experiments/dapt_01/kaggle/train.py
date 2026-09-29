#!/usr/bin/env python3
"""DAPT-01 resume from checkpoint-13781, save_steps=200, train toward 15248.

Locked config: Qwen3-8B-Base, 4-bit NF4 QLoRA, r=16/alpha=32/dropout=0.05,
lr=2e-4 cosine warmup_ratio=0.03, batch 1x16, seq 2048, fp16, no eval.
Forces trainer_state.save_steps=200. Session wall 6.5h (quota-capped).
"""
from __future__ import annotations
import json, os, shutil, subprocess, sys, time, traceback
from pathlib import Path

FROM_STEP = 13781
GLOBAL_TARGET = 15248
SESSION_TARGET = int(os.environ.get("DAPT_TARGET_STEP", str(GLOBAL_TARGET)))
SAVE_STEPS = 200
SAVE_TOTAL_LIMIT = 4  # >=3; 13781 survives until 5 new ckpts exist; 13981 verified long before
SESSION_MAX_SEC = float(os.environ.get("DAPT_SESSION_MAX_SEC", str(11.25 * 3600)))  # target 15248 finishes first

LOCKED = {
    "model": "Qwen/Qwen3-8B-Base",
    "quant": "4bit-nf4-double",
    "lora_r": 16, "lora_alpha": 32, "lora_dropout": 0.05,
    "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj",
                       "gate_proj", "up_proj", "down_proj"],
    "lr": 2e-4, "scheduler": "cosine", "warmup_ratio": 0.03,
    "batch": 1, "grad_accum": 16, "effective_batch": 16,
    "max_seq_length": 2048, "precision": "fp16", "seed": 42,
}

WORK = Path("/kaggle/working")
LOG = WORK / "dapt_train_worker.log"
STATUS = WORK / "dapt_train_status.json"
OUT = WORK / "dapt-01-output"
CKPT_ATTACH_ID = "priyanshu471/dapt01-checkpoint-13781"
TRAIN_DS = "priyanshu47/jainllm-domain-train"
OWNER = os.environ.get("KAGGLE_USERNAME", "priyanshu471")

_T0 = time.time()
_TRAIN_T0: float | None = None
_DURABLE = {"step": FROM_STEP, "slug": f"{OWNER}/dapt01-checkpoint-13781"}


def log(msg: str):
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}"
    print(line, flush=True)
    with LOG.open("a") as f:
        f.write(line + "\n")


def write_status(**kw):
    d = {"ts": time.time(), "from": FROM_STEP, "target": SESSION_TARGET,
         "global_target": GLOBAL_TARGET}
    d.update(kw)
    STATUS.write_text(json.dumps(d, indent=2))


def _import_ok(mod: str) -> bool:
    try:
        __import__(mod)
        return True
    except Exception:
        return False


def ensure_deps():
    need = [p for p, m in {
        "transformers": "transformers", "peft": "peft",
        "datasets": "datasets", "accelerate": "accelerate",
        "kaggle": "kaggle", "bitsandbytes": "bitsandbytes",
    }.items() if not _import_ok(m)]
    if not need:
        log("deps preinstalled")
        return
    log(f"pip install missing: {need}")
    last = None
    for attempt in range(1, 7):
        subprocess.run("getent hosts pypi.org || sleep 5", shell=True, capture_output=True)
        r = subprocess.run(
            f"{sys.executable} -m pip install -q --retries 10 --timeout 60 {' '.join(need)}",
            shell=True, capture_output=True, text=True, timeout=1800,
        )
        if r.returncode == 0:
            log(f"pip ok attempt={attempt}")
            return
        last = ((r.stdout or "") + (r.stderr or ""))[-500:]
        log(f"pip attempt {attempt} failed: {last}")
        need = [p for p, m in {
            "transformers": "transformers", "peft": "peft",
            "datasets": "datasets", "accelerate": "accelerate",
            "kaggle": "kaggle", "bitsandbytes": "bitsandbytes",
        }.items() if not _import_ok(m)]
        if not need:
            return
        time.sleep(20 * attempt)
    raise SystemExit(f"pip failed: {last}")


def _find_train_jsonl(root: Path) -> Path | None:
    if not root.exists():
        return None
    if (root / "train.jsonl").exists():
        return root / "train.jsonl"
    hits = list(root.glob("**/train.jsonl"))
    return hits[0] if hits else None


def locate_checkpoint_from_step() -> Path | None:
    for att in [
        Path(f"/kaggle/input/dapt01-checkpoint-{FROM_STEP}"),
        Path(f"/kaggle/input/dapt01-checkpoint-{FROM_STEP}/dapt01-checkpoint-{FROM_STEP}"),
        Path(f"/kaggle/input/checkpoint-{FROM_STEP}"),
    ]:
        if (att / "trainer_state.json").exists():
            return att
        hits = list(att.glob("**/trainer_state.json")) if att.exists() else []
        if hits:
            return hits[0].parent
    return None


def ensure_data() -> Path:
    """Prepare OUT/checkpoint-{FROM_STEP} (or newer durable in OUT). Return resume path."""
    dt = WORK / "domain_train"
    if _find_train_jsonl(dt) is None:
        attached = None
        for att in [Path("/kaggle/input/jainllm-domain-train"),
                    Path("/kaggle/input/jainllm-domain-train/jainllm-domain-train")]:
            attached = _find_train_jsonl(att)
            if attached:
                break
        if attached:
            dt.mkdir(parents=True, exist_ok=True)
            tgt = dt / "train.jsonl"
            if not tgt.exists():
                try:
                    os.symlink(str(attached), tgt)
                except FileExistsError:
                    pass
            log(f"attached train.jsonl -> {attached}")
        else:
            r = subprocess.run(
                f"kaggle datasets download -d {TRAIN_DS} -p {dt} --unzip",
                shell=True, capture_output=True, text=True, timeout=900,
            )
            if r.returncode != 0:
                raise SystemExit(f"train download failed: {((r.stdout or '') + (r.stderr or ''))[-400:]}")
    if not (dt / "train.jsonl").exists():
        raise SystemExit("train.jsonl missing after ensure_data")

    # Prefer any already-saved step >= FROM_STEP in OUT (this session's verified ckpts)
    newest = None
    if OUT.exists():
        for p in OUT.glob("checkpoint-*"):
            try:
                st = int(p.name.split("-")[-1])
            except Exception:
                continue
            if st >= FROM_STEP and (p / "trainer_state.json").exists():
                if newest is None or st > newest:
                    newest = st
    if newest is not None and newest > FROM_STEP:
        path = OUT / f"checkpoint-{newest}"
        log(f"resume from session checkpoint {path}")
        return path

    ck = OUT / f"checkpoint-{FROM_STEP}"
    if (ck / "trainer_state.json").exists():
        log(f"checkpoint-{FROM_STEP} already in OUT")
        _force_save_steps(ck)
        return ck

    src = locate_checkpoint_from_step()
    if src is None:
        dl = WORK / f"ck{FROM_STEP}_dl"
        r = subprocess.run(
            f"kaggle datasets download -d {CKPT_ATTACH_ID} -p {dl} --unzip",
            shell=True, capture_output=True, text=True, timeout=900,
        )
        if r.returncode != 0:
            raise SystemExit(f"ckpt_resume download failed: {((r.stdout or '') + (r.stderr or ''))[-400:]}")
        hits = list(dl.rglob("trainer_state.json"))
        if not hits:
            raise SystemExit("ckpt_resume download has no trainer_state.json")
        src = hits[0].parent
    if ck.exists():
        shutil.rmtree(ck)
    ck.mkdir(parents=True)
    for p in src.iterdir():
        if p.is_file() and p.name != "README.md":
            shutil.copy2(p, ck / p.name)
    log(f"staged checkpoint-{FROM_STEP} from {src}")
    _force_save_steps(ck)
    return ck


def _force_save_steps(ckpt: Path) -> None:
    """Old checkpoints baked save_steps=500; force 200 without touching global_step."""
    p = ckpt / "trainer_state.json"
    if not p.exists():
        return
    try:
        ts = json.loads(p.read_text())
    except Exception as e:
        log(f"cannot read trainer_state for save_steps patch: {e}")
        return
    if ts.get("save_steps") != SAVE_STEPS:
        old = ts.get("save_steps")
        ts["save_steps"] = SAVE_STEPS
        p.write_text(json.dumps(ts, indent=2))
        gs = ts.get("global_step")
        log(f"patched trainer_state.save_steps {old} -> {SAVE_STEPS} (global_step={gs} unchanged)")


def verify_ckpt_dir(ckpt: Path, expect_step: int | None = None) -> list[str]:
    errs: list[str] = []
    if not ckpt.is_dir():
        return [f"missing dir {ckpt}"]
    for name in ["adapter_model.safetensors", "adapter_config.json",
                 "optimizer.pt", "scheduler.pt", "trainer_state.json"]:
        p = ckpt / name
        if not p.exists():
            errs.append(f"missing {name}")
        elif p.stat().st_size == 0:
            errs.append(f"empty {name}")
    if not any((ckpt / n).exists() for n in ("tokenizer.json", "tokenizer_config.json")):
        errs.append("missing tokenizer")
    if (ckpt / "trainer_state.json").exists():
        try:
            ts = json.loads((ckpt / "trainer_state.json").read_text())
            gs = ts.get("global_step")
            if expect_step is not None and gs != expect_step:
                errs.append(f"trainer_state global_step={gs} != {expect_step}")
            if expect_step is None and isinstance(gs, int):
                try:
                    dir_step = int(ckpt.name.split("-")[-1])
                    if gs != dir_step:
                        errs.append(f"trainer_state global_step={gs} != dir {dir_step}")
                except Exception:
                    pass
        except Exception as e:
            errs.append(f"trainer_state unreadable: {e}")
    if (ckpt / "adapter_config.json").exists():
        try:
            ad = json.loads((ckpt / "adapter_config.json").read_text())
            if ad.get("r") != LOCKED["lora_r"] or ad.get("lora_alpha") != LOCKED["lora_alpha"]:
                errs.append(f"adapter r/alpha mismatch r={ad.get('r')} alpha={ad.get('lora_alpha')}")
        except Exception as e:
            errs.append(f"adapter_config unreadable: {e}")
    if not errs:
        for heavy in ("optimizer.pt", "adapter_model.safetensors"):
            p = ckpt / heavy
            if p.exists() and p.stat().st_size < 1_000_000:
                errs.append(f"{heavy} suspiciously small ({p.stat().st_size}B)")
    if not errs:
        try:
            import torch
            sch = torch.load(ckpt / "scheduler.pt", map_location="cpu", weights_only=False)
            if sch is None:
                errs.append("scheduler state empty")
        except Exception as e:
            # weights_only may reject; try without
            try:
                import torch
                torch.load(ckpt / "scheduler.pt", map_location="cpu")
            except Exception as e2:
                errs.append(f"scheduler not loadable: {e2}")
    return errs


def startup_checks(ckpt: Path) -> list[str]:
    fails: list[str] = []
    import torch
    if not torch.cuda.is_available():
        fails.append("CUDA not available")
    else:
        n = torch.cuda.device_count()
        name = torch.cuda.get_device_name(0) if n else "?"
        log(f"GPU count={n} name={name}")
        if "T4" not in name and "Tesla" not in name:
            fails.append(f"unexpected GPU: {name}")
        free, total = torch.cuda.mem_get_info(0) if n else (0, 0)
        log(f"VRAM free={free/1e9:.2f}GB total={total/1e9:.2f}GB")
        if total and total < 10e9:
            fails.append(f"VRAM too low: {total/1e9:.1f}GB")

    for name in ["adapter_config.json", "adapter_model.safetensors",
                 "trainer_state.json", "optimizer.pt", "scheduler.pt"]:
        if not (ckpt / name).exists():
            fails.append(f"checkpoint missing {name}")
    if not fails:
        ts = json.loads((ckpt / "trainer_state.json").read_text())
        if ts.get("global_step") != FROM_STEP and int(ckpt.name.split("-")[-1]) != FROM_STEP:
            # allow higher session steps only if dir matches state
            dir_step = int(ckpt.name.split("-")[-1])
            if ts.get("global_step") != dir_step:
                fails.append(f"global_step {ts.get('global_step')} != dir {dir_step}")
        try:
            import torch
            opt = torch.load(ckpt / "optimizer.pt", map_location="cpu", weights_only=False)
            if not opt:
                fails.append("optimizer state empty")
        except Exception as e:
            try:
                import torch
                torch.load(ckpt / "optimizer.pt", map_location="cpu")
            except Exception as e2:
                fails.append(f"optimizer not loadable: {e2}")
        try:
            import torch
            torch.load(ckpt / "scheduler.pt", map_location="cpu", weights_only=False)
        except Exception:
            try:
                import torch
                torch.load(ckpt / "scheduler.pt", map_location="cpu")
            except Exception as e2:
                fails.append(f"scheduler not loadable: {e2}")
        ad = json.loads((ckpt / "adapter_config.json").read_text())
        if ad.get("r") != 16 or ad.get("lora_alpha") != 32 or float(ad.get("lora_dropout") or 0) != 0.05:
            fails.append(f"LoRA config mismatch r={ad.get('r')} a={ad.get('lora_alpha')} d={ad.get('lora_dropout')}")
        if set(ad.get("target_modules") or []) != set(LOCKED["target_modules"]):
            fails.append(f"target_modules mismatch: {ad.get('target_modules')}")
        if ad.get("peft_type") and ad.get("peft_type") != "LORA":
            fails.append(f"peft_type {ad.get('peft_type')}")
        if not any((ckpt / n).exists() for n in ("tokenizer.json", "tokenizer_config.json")):
            fails.append("tokenizer missing")
        if not (OUT / f"checkpoint-{FROM_STEP}" ).exists() and ckpt.name != f"checkpoint-{FROM_STEP}":
            pass  # session resume step
        # locked meta verification
        if LOCKED["model"] != "Qwen/Qwen3-8B-Base" or LOCKED["lr"] != 2e-4 or LOCKED["max_seq_length"] != 2048:
            fails.append("LOCKED dict corrupted")
        if LOCKED["batch"] * LOCKED["grad_accum"] != LOCKED["effective_batch"]:
            fails.append("effective batch != 16")
    return fails


def upload_ckpt(ckpt_dir: Path, step: int) -> str:
    from kaggle.api.kaggle_api_extended import KaggleApi
    slug = f"dapt01-checkpoint-{step}"
    folder = Path(f"/tmp/kaggle_up_{step}")
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True)
    for p in ckpt_dir.iterdir():
        if p.is_file() and p.name != "README.md":
            shutil.copy2(p, folder / p.name)
    (folder / "dataset-metadata.json").write_text(json.dumps({
        "title": f"DAPT-01 checkpoint {step}",
        "id": f"{OWNER}/{slug}",
        "licenses": [{"name": "CC0-1.0"}],
        "description": f"DAPT-01 QLoRA resume checkpoint global_step={step} (session from 13781).",
    }, indent=2))
    api = KaggleApi()
    api.authenticate()
    try:
        api.dataset_create_new(folder=str(folder), public=True, quiet=True,
                               convert_to_csv=False, dir_mode="skip")
        log(f"upload create ok {OWNER}/{slug}")
    except Exception as e:
        log(f"create failed ({e}); trying version")
        api.dataset_create_version(str(folder), version_notes=f"step {step}",
                                   quiet=True, convert_to_csv=False, dir_mode="skip")
        log(f"upload version ok {OWNER}/{slug}")
    return f"{OWNER}/{slug}"


def main() -> int:
    global _TRAIN_T0
    import torch
    if not torch.cuda.is_available():
        write_status(state="error", error="no_cuda")
        log("STOP: CUDA not available")
        return 2
    gpu_name = torch.cuda.get_device_name(0)
    log(f"KAGGLE_TRAIN START from={FROM_STEP} target={SESSION_TARGET} "
        f"save_steps={SAVE_STEPS} gpu={gpu_name} fp16")
    write_status(state="starting", accelerator="gpu", device=gpu_name)
    ensure_deps()

    from transformers import (
        TrainerCallback, AutoModelForCausalLM, AutoTokenizer,
        TrainingArguments, Trainer, DataCollatorForLanguageModeling,
        BitsAndBytesConfig, TrainerControl, TrainerState, TrainingArguments as TA,
    )
    from peft import LoraConfig, PeftModel, get_peft_model, prepare_model_for_kbit_training
    from datasets import load_dataset
    import inspect

    resume_path = ensure_data()
    OUT.mkdir(exist_ok=True)
    dir_step = int(resume_path.name.split("-")[-1])
    log(f"resume={resume_path} dir_step={dir_step} target={SESSION_TARGET}")

    if dir_step < FROM_STEP:
        write_status(state="error", error=f"step {dir_step} < {FROM_STEP}")
        log(f"STOP: refusing to resume from {dir_step} (must be >= {FROM_STEP})")
        return 3
    if dir_step >= SESSION_TARGET:
        write_status(state="done", final_step=dir_step, note="already at target")
        log("already at/past session target")
        return 0

    fails = startup_checks(resume_path)
    if fails:
        for f in fails:
            log(f"STARTUP_FAIL: {f}")
        write_status(state="startup_failed", fails=fails, resume=str(resume_path))
        log("STOP: startup checks failed; checkpoint untouched")
        return 4
    log("startup checks OK (GPU/CUDA/VRAM/ckpt/optimizer/scheduler/lora/tokenizer/locked)")
    _force_save_steps(resume_path)

    log(f"resume={resume_path} step={dir_step} target={SESSION_TARGET}")
    write_status(state="loading_model", global_step=dir_step)

    tok = AutoTokenizer.from_pretrained(str(resume_path), trust_remote_code=True)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    bnb = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
    )
    base = AutoModelForCausalLM.from_pretrained(
        LOCKED["model"],
        quantization_config=bnb,
        device_map="auto",
        trust_remote_code=True,
    )
    base = prepare_model_for_kbit_training(base, use_gradient_checkpointing=True)
    model = PeftModel.from_pretrained(base, str(resume_path), is_trainable=True)
    log("loaded adapter from resume checkpoint")
    try:
        model.print_trainable_parameters()
    except Exception:
        pass

    write_status(state="loading_data")
    data = WORK / "domain_train"
    try:
        ds = load_dataset("json", data_files={"train": str(data / "train.jsonl")})
        cols = ds["train"].column_names
        if "text" not in cols:
            raise ValueError(f"no text col: {cols}")
    except Exception as e:
        log(f"load_dataset failed ({e}); text-only cache")
        text_only = WORK / "domain_train_textonly.jsonl"
        if not text_only.exists() or text_only.stat().st_size == 0:
            with (data / "train.jsonl").open() as fin, text_only.open("w") as fout:
                for line in fin:
                    try:
                        o = json.loads(line)
                    except Exception:
                        continue
                    tx = o.get("text") or ""
                    if tx:
                        fout.write(json.dumps({"text": tx}) + "\n")
        ds = load_dataset("json", data_files={"train": str(text_only)})
        cols = ds["train"].column_names

    def tok_fn(ex):
        return tok(ex["text"], truncation=True, max_length=LOCKED["max_seq_length"], padding=False)
    ds = ds.map(tok_fn, batched=True, remove_columns=cols, num_proc=1)
    log(f"dataset train={len(ds['train'])}")

    ta_params = set(inspect.signature(TrainingArguments.__init__).parameters)
    candidate = {
        "output_dir": str(OUT),
        "max_steps": SESSION_TARGET,
        "per_device_train_batch_size": LOCKED["batch"],
        "gradient_accumulation_steps": LOCKED["grad_accum"],
        "learning_rate": LOCKED["lr"],
        "lr_scheduler_type": LOCKED["scheduler"],
        "warmup_ratio": LOCKED["warmup_ratio"],
        "weight_decay": 0.01,
        "max_grad_norm": 1.0,
        "seed": LOCKED["seed"],
        "fp16": True,
        "bf16": False,
        "optim": "adamw_torch",
        "logging_steps": 20,
        "save_steps": SAVE_STEPS,
        "save_strategy": "steps",
        "save_total_limit": SAVE_TOTAL_LIMIT,
        "report_to": [],
        "eval_strategy": "no",
        "remove_unused_columns": True,
        "dataloader_num_workers": 0,
        "gradient_checkpointing": True,
    }
    kwargs = {k: v for k, v in candidate.items() if k in ta_params}
    dropped = sorted(set(candidate) - set(kwargs))
    if dropped:
        log(f"TrainingArguments dropped: {dropped}")
    if "warmup_ratio" in kwargs and "warmup_steps" in ta_params:
        kwargs["warmup_steps"] = 0
    args = TrainingArguments(**kwargs)
    log(f"TrainingArguments ok max_steps={args.max_steps} save_steps={args.save_steps} "
        f"save_total_limit={args.save_total_limit} fp16={args.fp16} bf16={args.bf16} "
        f"warmup_ratio={getattr(args, 'warmup_ratio', None)}")

    class Task58Callback(TrainerCallback):
        def __init__(self):
            self._uploaded: set[int] = set()
            self._verified: set[int] = set()
            self._forced_stop = False

        def on_train_begin(self, args, state, control, **kwargs):
            global _TRAIN_T0
            _TRAIN_T0 = time.time()
            if getattr(state, "save_steps", None) != SAVE_STEPS:
                log(f"forcing state.save_steps {getattr(state, 'save_steps', None)} -> {SAVE_STEPS}")
                state.save_steps = SAVE_STEPS
            if getattr(args, "save_steps", None) != SAVE_STEPS:
                log(f"forcing args.save_steps {args.save_steps} -> {SAVE_STEPS}")
                args.save_steps = SAVE_STEPS
            log(f"on_train_begin global_step={state.global_step} max_steps={state.max_steps} save_steps={getattr(state, 'save_steps', None)}")
            return control

        def on_step_end(self, args, state, control, **kwargs):
            global _DURABLE
            step = state.global_step
            elapsed = time.time() - (_TRAIN_T0 or _T0)
            if step % 100 == 0:
                try:
                    free, total = torch.cuda.mem_get_info(0)
                    du = shutil.disk_usage(str(WORK))
                    log(f"monitor step={step} elapsed={elapsed/3600:.2f}h "
                        f"vram_free={free/1e9:.1f}GB disk_free={du.free/1e9:.1f}GB")
                except Exception:
                    log(f"monitor step={step} elapsed={elapsed/3600:.2f}h")
            if elapsed >= SESSION_MAX_SEC and not self._forced_stop:
                self._forced_stop = True
                control.should_save = True
                control.should_training_stop = True
                log(f"SESSION_LIMIT elapsed={elapsed:.0f}s >= {SESSION_MAX_SEC:.0f}s "
                    f"— save current step={step} and stop cleanly")
            return control

        def on_save(self, args, state, control, **kwargs):
            global _DURABLE
            step = state.global_step
            ckpt = OUT / f"checkpoint-{step}"
            if not (ckpt / "trainer_state.json").exists():
                log(f"VERIFY_FAIL step={step}: trainer_state missing right after save")
                return control
            if step in self._verified and step in self._uploaded:
                return control
            errs = verify_ckpt_dir(ckpt, expect_step=step)
            if errs:
                log(f"VERIFY_FAIL step={step}: {'; '.join(errs)}")
                write_status(state="verify_failed", global_step=step, errors=errs)
                control.should_training_stop = True
                return control
            self._verified.add(step)
            log(f"VERIFY_OK step={step}")
            kg = WORK / "dapt_known_good" / f"known_good_step_{step}"
            try:
                kg.mkdir(parents=True, exist_ok=True)
                for name in ["adapter_model.safetensors", "adapter_config.json",
                             "trainer_state.json", "optimizer.pt", "scheduler.pt",
                             "tokenizer.json", "tokenizer_config.json"]:
                    src = ckpt / name
                    if src.exists() and not (kg / name).exists():
                        shutil.copy2(src, kg / name)
            except Exception as e:
                log(f"known_good copy fail step={step}: {e}")
            if step in self._uploaded:
                return control
            try:
                slug = upload_ckpt(ckpt, step)
                self._uploaded.add(step)
                if step >= _DURABLE["step"]:
                    _DURABLE = {"step": step, "slug": slug}
                log(f"UPLOAD_OK step={step} slug={slug}")
                write_status(state="training", global_step=step,
                             durable=_DURABLE, uploaded=sorted(self._uploaded))
            except Exception:
                log(f"UPLOAD_FAIL step={step}\n" + traceback.format_exc())
            return control

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=ds["train"],
        eval_dataset=None,
        data_collator=DataCollatorForLanguageModeling(tokenizer=tok, mlm=False),
        processing_class=tok,
    )
    cb = Task58Callback()
    trainer.add_callback(cb)

    write_status(state="training", global_step=dir_step, accelerator="gpu",
                 durable=_DURABLE)
    log(f"TRAIN start resume_from_checkpoint={resume_path} max_steps={SESSION_TARGET} "
        f"save_steps={SAVE_STEPS} gpu={gpu_name}")
    t0 = time.time()
    try:
        result = trainer.train(resume_from_checkpoint=str(resume_path))
    except Exception:
        log("TRAIN_EXCEPTION\n" + traceback.format_exc())
        write_status(state="error", global_step=int(getattr(trainer.state, "global_step", dir_step)),
                     error=traceback.format_exc()[-2000:], durable=_DURABLE)
        result = None

    elapsed = time.time() - t0
    final_step = int(getattr(trainer.state, "global_step", dir_step))
    log(f"TRAIN done final_step={final_step} elapsed={elapsed:.1f}s "
        f"uploaded={sorted(cb._uploaded)} durable={_DURABLE}")

    # Ensure final state is persisted if last step not a save boundary
    final_ck = OUT / f"checkpoint-{final_step}"
    if not (final_ck / "trainer_state.json").exists() and final_step > dir_step:
        log(f"no checkpoint at final_step={final_step}; forcing save")
        try:
            trainer.save_model(str(final_ck))
            if trainer.optimizer is not None:
                torch.save(trainer.optimizer.state_dict(), final_ck / "optimizer.pt")
            if trainer.lr_scheduler is not None:
                torch.save(trainer.lr_scheduler.state_dict(), final_ck / "scheduler.pt")
            trainer.state.save_to_json(final_ck / "trainer_state.json")
            log(f"forced save ok step={final_step}")
        except Exception:
            log("FORCED_SAVE_FAIL\n" + traceback.format_exc())
            final_step = max([d for d in cb._verified] + [dir_step])
            final_ck = OUT / f"checkpoint-{final_step}"

    report: dict = {
        "task": "resume-13781",
        "start_checkpoint": f"checkpoint-{FROM_STEP}",
        "start_global_step": FROM_STEP,
        "resume_path": str(resume_path),
        "final_global_step": final_step,
        "steps_completed": final_step - FROM_STEP,
        "session_target": SESSION_TARGET,
        "global_target": GLOBAL_TARGET,
        "elapsed_sec": elapsed,
        "sec_per_step": (elapsed / max(1, final_step - dir_step)),
        "session_ended": "session_limit" if cb._forced_stop else (
            "completed_session_target" if final_step >= SESSION_TARGET else "stopped"),
        "checkpoints_created": sorted(cb._verified),
        "uploads": sorted(cb._uploaded),
        "durable": dict(_DURABLE),
        "remaining_to_global": GLOBAL_TARGET - final_step,
        "timestamp": time.time(),
    }
    try:
        lh = trainer.state.log_history or []
        losses = [x for x in lh if "loss" in x]
        if losses:
            report["starting_loss"] = losses[0].get("loss")
            report["ending_loss"] = losses[-1].get("loss")
            report["first_loss_step"] = losses[0].get("step")
            report["last_loss_step"] = losses[-1].get("step")
    except Exception:
        pass

    # final integrity pass on final checkpoint
    if final_ck.exists():
        errs = verify_ckpt_dir(final_ck, expect_step=final_step)
        report["final_ckpt_errors"] = errs
        if not errs and final_step not in cb._uploaded:
            try:
                slug = upload_ckpt(final_ck, final_step)
                cb._uploaded.add(final_step)
                _DURABLE.update(step=final_step, slug=slug)
                report["uploads"] = sorted(cb._uploaded)
                report["durable"] = dict(_DURABLE)
                log(f"UPLOAD_OK final step={final_step} slug={slug}")
            except Exception:
                log("FINAL_UPLOAD_FAIL\n" + traceback.format_exc())
        report["final_integrity"] = "ok" if not errs else errs

    (OUT / "RESUME13781_FINAL_REPORT.json").write_text(json.dumps(report, indent=2))
    write_status(state="done", global_step=final_step, durable=_DURABLE,
                 report=report, elapsed_sec=elapsed)
    log("RESUME_REPORT " + json.dumps(report))
    log("WORKER COMPLETE")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        try:
            STATUS.write_text(json.dumps({
                "ts": time.time(), "from": FROM_STEP, "target": SESSION_TARGET,
                "state": "error", "error": traceback.format_exc()[-2000:],
            }, indent=2))
            with LOG.open("a") as f:
                f.write(time.strftime("%Y-%m-%d %H:%M:%S") + " FATAL\n" + traceback.format_exc() + "\n")
        except Exception:
            pass
        raise
