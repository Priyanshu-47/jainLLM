"""Phase 8: LOAD TEST ONLY — verify checkpoint-3893 on Colab. Do not train."""
import json, os, sys
from pathlib import Path

CKPT = Path(os.environ.get("DAPT_CKPT", "/content/checkpoint-3893"))
BASE = os.environ.get("DAPT_BASE", "Qwen/Qwen3-8B-Base")

report = {"ok": False, "checks": {}}

def check(name, cond, detail=""):
    report["checks"][name] = {"pass": bool(cond), "detail": str(detail)}
    print(f"[{'PASS' if cond else 'FAIL'}] {name}: {detail}")

required = [
    "adapter_config.json", "adapter_model.safetensors", "optimizer.pt",
    "scheduler.pt", "trainer_state.json", "training_args.bin",
    "tokenizer.json", "tokenizer_config.json",
]
missing = [f for f in required if not (CKPT / f).exists()]
check("files_present", not missing, f"missing={missing}")

with open(CKPT / "adapter_config.json") as f:
    ac = json.load(f)
check("base_model", ac.get("base_model_name_or_path") == BASE, ac.get("base_model_name_or_path"))
check("lora_r", ac.get("r") == 16, str(ac.get("r")))
check("lora_alpha", ac.get("lora_alpha") == 32, str(ac.get("lora_alpha")))
check("lora_dropout", ac.get("lora_dropout") == 0.05, str(ac.get("lora_dropout")))
check("peft_type", ac.get("peft_type") == "LORA", str(ac.get("peft_type")))
tm = set(ac.get("target_modules") or [])
expected_tm = {"q_proj","k_proj","v_proj","o_proj","gate_proj","up_proj","down_proj"}
check("target_modules", tm == expected_tm, str(sorted(tm)))

with open(CKPT / "trainer_state.json") as f:
    ts = json.load(f)
check("global_step_3893", ts.get("global_step") == 3893, str(ts.get("global_step")))
check("max_steps_15248", ts.get("max_steps") == 15248, str(ts.get("max_steps")))

try:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from peft import PeftModel
    import peft
    check("cuda", torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else "no")
    check("torch", True, torch.__version__)
    import transformers
    check("transformers", True, transformers.__version__)
    check("peft", True, peft.__version__)

    tok = AutoTokenizer.from_pretrained(CKPT, trust_remote_code=True)
    check("tokenizer_load", tok is not None, type(tok).__name__)

    bnb = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
    )
    # Prefer dtype= over torch_dtype= on new transformers
    kwargs = dict(
        quantization_config=bnb,
        device_map="auto",
        trust_remote_code=True,
    )
    try:
        base = AutoModelForCausalLM.from_pretrained(BASE, dtype=torch.float16, **kwargs)
    except TypeError:
        base = AutoModelForCausalLM.from_pretrained(BASE, torch_dtype=torch.float16, **kwargs)

    model = PeftModel.from_pretrained(base, CKPT, is_trainable=False)
    check("adapter_load", isinstance(model, PeftModel), type(model).__name__)

    try:
        opt = torch.load(CKPT / "optimizer.pt", map_location="cpu", weights_only=False)
        check("optimizer_state", opt is not None, type(opt).__name__)
    except Exception as e:
        check("optimizer_state", False, f"{type(e).__name__}: {e}")

    try:
        sch = torch.load(CKPT / "scheduler.pt", map_location="cpu", weights_only=False)
        check("scheduler_state", sch is not None, type(sch).__name__)
    except Exception as e:
        check("scheduler_state", False, f"{type(e).__name__}: {e}")

    # smoke: forward on cuda with adapter (tiny)
    try:
        model.eval()
        input_ids = torch.tensor([[tok.bos_token_id or 151643, 151645]], device="cuda")
        with torch.no_grad():
            out = model(input_ids=input_ids)
        logits = out.logits
        check("forward_smoke", logits is not None and logits.shape[-1] > 0, f"shape={tuple(logits.shape)}")
    except Exception as e:
        check("forward_smoke", False, f"{type(e).__name__}: {e}")

except Exception as e:
    check("full_load", False, f"{type(e).__name__}: {e}")
else:
    check("full_load", True, "BitsAndBytes 4bit + PeftModel loaded")

report["ok"] = all(c["pass"] for c in report["checks"].values())
out = Path("/content/checkpoint_load_test_report.json")
out.write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
sys.exit(0 if report["ok"] else 1)
