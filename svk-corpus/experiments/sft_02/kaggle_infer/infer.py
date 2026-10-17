"""TASK 68 inference kernel: SFT-02 arm — frozen Task-60 47-case set + sft_eval_v2.

Run on a Kaggle T4 with attached inputs:
  - priyanshu471/sft02-output        -> SFT-02 final adapter (verified by sha256)
  - priyanshu471/jainllm-sft02-train -> eval.jsonl (verified by sha256)

Protocol for the 47-case arm is byte-identical to
experiments/dapt_01/evaluation/kaggle/task60_infer_kaggle.py (Task 60):
  - model: Qwen/Qwen3-8B-Base (4-bit NF4, same BitsAndBytesConfig)
  - SYSTEM_PROMPT, chat_template-if-available prompt, greedy decoding,
    max_new_tokens=192, seed=42
  - cases packed below from data/evaluation/dapt01_eval_cases.jsonl and
    verified against its frozen sha256 before anything runs.

Outputs (to /kaggle/working, pulled with `kaggle kernels output`):
  - dapt01_sft02_results.jsonl   (47 rows, Task-60 row schema)
  - sft02_eval_results.jsonl     (13 rows, per-example sft_eval_v2 generations)
  - task68_sft02_infer_metadata.json

No training, no adapter merge, no corpus writes. Only the SFT-02 arm is
generated here; BASE, DAPT-01 and SFT-01 arms reuse the frozen result files
dapt01_base_results.jsonl, dapt01_dapt_results.jsonl and
dapt01_sft_results.jsonl (same cases, prompts, decoding).
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path


def _import_ok(mod: str) -> bool:
    try:
        __import__(mod)
        return True
    except Exception:
        return False


def ensure_deps() -> None:
    """Mirror task60_infer_kaggle.py: image may lack bitsandbytes."""
    need = [
        pkg
        for pkg, mod in {
            "transformers": "transformers",
            "peft": "peft",
            "accelerate": "accelerate",
            "bitsandbytes": "bitsandbytes",
        }.items()
        if not _import_ok(mod)
    ]
    if "bitsandbytes" not in need and _import_ok("bitsandbytes"):
        import bitsandbytes as _bnb  # noqa: F401

        try:
            from importlib.metadata import version as _v

            if _v("bitsandbytes") < "0.46.1":
                need.append("bitsandbytes")
        except Exception:
            pass
    if not need:
        print("[deps] preinstalled", flush=True)
        return
    print(f"[deps] pip install {need}", flush=True)
    last = ""
    for attempt in range(1, 7):
        subprocess.run(
            "getent hosts pypi.org || sleep 5", shell=True, capture_output=True
        )
        r = subprocess.run(
            f"{sys.executable} -m pip install -q --retries 10 --timeout 60 {' '.join(need)}",
            shell=True,
            capture_output=True,
            text=True,
            timeout=1800,
        )
        last = ((r.stdout or "") + (r.stderr or ""))[-500:]
        if r.returncode == 0:
            print(f"[deps] pip ok attempt={attempt}", flush=True)
            return
        print(f"[deps] attempt {attempt} failed: {last}", flush=True)
        need = [
            p
            for p, m in {
                "transformers": "transformers",
                "peft": "peft",
                "accelerate": "accelerate",
                "bitsandbytes": "bitsandbytes",
            }.items()
            if not _import_ok(m)
        ]
        if not need:
            return
        time.sleep(20 * attempt)
    raise SystemExit(f"pip failed: {last}")


ensure_deps()

import torch  # noqa: E402
from peft import PeftModel  # noqa: E402
from transformers import (  # noqa: E402
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
)

MODEL_ID = "Qwen/Qwen3-8B-Base"
SFT_ADAPTER_DATASET = "priyanshu471/sft02-output"
DATA_DATASET = "priyanshu471/jainllm-sft02-train"

EXPECTED = {
    "adapter_sha256": "2b22228940f81dc507d9815d919a31fe30bd4a9da1804a33f28b41b70766298d",
    "cases_sha256": "06625f72190e3ae130447345afdc04342bd19cb76f842285706480cba7765b81",
    "eval_sha256": "ba59533699b28328e4dc9e5fa3df1c24a0b026824bafc852cfc703f38e6fcc35",
}

WORK = Path("/kaggle/working")


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _first(pattern_root: Path, name: str):
    hits = sorted(pattern_root.glob(f"**/{name}"))
    return hits[0] if hits else None


def resolve_adapter_dir() -> Path:
    """Find the attached sft02-output dir, else download it."""
    candidates = [
        Path("/kaggle/input/sft02-output"),
        Path("/kaggle/input/datasets/priyanshu471/sft02-output"),
        *sorted(Path("/kaggle/input").glob("**/*sft02-output*")),
    ]
    for c in candidates:
        if c.name == "adapter_model.safetensors" and c.is_file():
            return c.parent
        if (c / "adapter_model.safetensors").exists():
            return c
    hit = _first(Path("/kaggle/input"), "adapter_model.safetensors")
    if hit is not None:
        return hit.parent
    try:
        import kagglehub

        dl = Path(kagglehub.dataset_download(SFT_ADAPTER_DATASET))
        if (dl / "adapter_model.safetensors").exists():
            return dl
        for sub in dl.rglob("adapter_model.safetensors"):
            return sub.parent
    except Exception as exc:  # noqa: BLE001
        print(f"kagglehub adapter download failed: {exc}", flush=True)
    raise FileNotFoundError("sft02-output adapter not found")


def resolve_eval_path() -> Path:
    """Find the attached jainllm-sft02-train eval.jsonl, else download."""
    candidates = [
        Path("/kaggle/input/jainllm-sft02-train/eval.jsonl"),
        Path("/kaggle/input/datasets/priyanshu471/jainllm-sft02-train/eval.jsonl"),
        *sorted(Path("/kaggle/input").glob("**/jainllm-sft02-train/**/eval.jsonl")),
    ]
    for c in candidates:
        if c.exists():
            return c
    hit = _first(Path("/kaggle/input"), "eval.jsonl")
    if hit is not None:
        return hit
    dl = WORK / "sft02_eval_dl"
    r = subprocess.run(
        f"kaggle datasets download -d {DATA_DATASET} -p {dl} --unzip",
        shell=True, capture_output=True, text=True, timeout=900,
    )
    if r.returncode != 0:
        raise SystemExit("eval.jsonl download failed: " +
                         ((r.stdout or "") + (r.stderr or ""))[-400:])
    hit = _first(dl, "eval.jsonl")
    if hit is None:
        raise FileNotFoundError("eval.jsonl not found after download")
    return hit


# Cases are packed in by build_infer_kernel.py (keep the marker on one line).
CASES_JSON = r"""
{"example_id": "DAPT01EVAL-001", "category": "JAIN_TERMINOLOGY", "language": "en", "question": "In J. N. Farquhar's Notes on the Religious Literature of India, how is ahimsa defined?", "expected_answer_or_reference": "Ahimsa = non-injury, especially non-injury to animal life.", "provenance": {"role": "grounding_unit", "unit_ids": ["SVK-1005:u04715"], "source_id": "SVK-1005", "dapt_split": "train", "dapt_seen_at_train": true}, "scoring": [{"all_of": ["non-injury"], "any_of": ["animal life", "animal"]}], "source_contains": ["Ahimsa, non-injury", "animal life"], "abstention_case": false, "notes": ""}
{"example_id": "DAPT01EVAL-002", "category": "JAIN_TERMINOLOGY", "language": "en", "question": "According to Stevenson's Notes on Modern Jainism, what is Karma, and how does it affect a person's lives?", "expected_answer_or_reference": "Karma is the accumulated force of a person's good and bad actions in previous existences; it determines present and future life and forces a succession of rebirths until exhausted.", "provenance": {"role": "grounding_unit", "unit_ids": ["SVK-0038:u00638"], "source_id": "SVK-0038", "dapt_split": "train", "dapt_seen_at_train": true}, "scoring": [{"all_of": ["accumulated"], "any_of": ["previous existences", "past", "good and bad"]}], "source_contains": ["accumulated force", "previous existences"], "abstention_case": false, "notes": ""}
{"example_id": "DAPT01EVAL-003", "category": "JAIN_TERMINOLOGY", "language": "en", "question": "According to Stevenson, what are the two great divisions of Jain cosmic time, and how many periods does each contain?", "expected_answer_or_reference": "Utsarpini (rising) and Avasarpini (falling); each is subdivided into six periods.", "provenance": {"role": "grounding_unit", "unit_ids": ["SVK-0038:u00957"], "source_id": "SVK-0038", "dapt_split": "train", "dapt_seen_at_train": true}, "scoring": [{"all_of": ["utsarpini", "avasarpini"], "any_of": ["six periods", "six", "6"]}], "source_contains": ["Utsarpini", "Avasarpini", "six periods"], "abstention_case": false, "notes": ""}
{"example_id": "DAPT01EVAL-004", "category": "JAIN_TERMINOLOGY", "language": "en", "question": "According to Stevenson, what three things make up the Three Jewels (Ratna Traya) in Jainism?", "expected_answer_or_reference": "Right Knowledge (Jnana), Right Faith (Darsana) and Right Conduct (Caritra).", "provenance": {"role": "grounding_unit", "unit_ids": ["SVK-0038:u00989", "SVK-0038:u00990"], "source_id": "SVK-0038", "dapt_split": "train", "dapt_seen_at_train": true}, "scoring": [{"all_of": ["knowledge", "faith", "conduct"]}], "source_contains": ["Three Jewels", "Right Knowledge", "Right Faith", "Right Conduct"], "abstention_case": false, "notes": ""}
{"example_id": "DAPT01EVAL-005", "category": "STHANAKAVASI_TERMINOLOGY", "language": "en", "question": "According to Stevenson, where is the Samayika generally said by Sthanakavasi Jaina?", "expected_answer_or_reference": "In a monastery (an Upasaro).", "provenance": {"role": "grounding_unit", "unit_ids": ["SVK-0038:u01125"], "source_id": "SVK-0038", "dapt_split": "train", "dapt_seen_at_train": true}, "scoring": [{"all_of": ["monastery"], "any_of": ["upasaro", "upasara", "upāsāro"]}], "source_contains": ["Sthanakavasi Jaina in a monastery (Upasaro"], "abstention_case": false, "notes": ""}
{"example_id": "DAPT01EVAL-006", "category": "STHANAKAVASI_TERMINOLOGY", "language": "en", "question": "According to Stevenson's account of the Sthanakavasi canon, how many Mulagrantha are there?", "expected_answer_or_reference": "Four Mulagrantha (according to the Sthanakavasi canon); the Sthanakavasi accept only the first two as Mulagrantha.", "provenance": {"role": "grounding_unit", "unit_ids": ["SVK-0038:u00235", "SVK-0038:u00233"], "source_id": "SVK-0038", "dapt_split": "train", "dapt_seen_at_train": true}, "scoring": [{"all_of": ["four"], "any_of": ["mula", "mulagrantha", "first two"]}], "source_contains": ["Four Mulagrantha", "Sthanakavasi accept only the first two"], "abstention_case": false, "notes": ""}
{"example_id": "DAPT01EVAL-007", "category": "STHANAKAVASI_TERMINOLOGY", "language": "en", "question": "According to Stevenson, what is Vaiyavacca and what does an ascetic do under it?", "expected_answer_or_reference": "Service: an ascetic must serve his superiors and the afflicted (bringing water/food for his guru, massaging him when tired).", "provenance": {"role": "grounding_unit", "unit_ids": ["SVK-0038:u00399"], "source_id": "SVK-0038", "dapt_split": "train", "dapt_seen_at_train": true}, "scoring": [{"all_of": ["serve", "superiors"], "any_of": ["afflicted", "guru", "service"]}], "source_contains": ["This is called Vaiyavacca", "serve his superiors and the afflicted"], "abstention_case": false, "notes": ""}
{"example_id": "DAPT01EVAL-008", "category": "STHANAKAVASI_TERMINOLOGY", "language": "en", "question": "According to Stevenson, which scriptures do the Terapanthi accept?", "expected_answer_or_reference": "They accept the Sthanakavasi scriptures (but read their own meaning into certain passages).", "provenance": {"role": "grounding_unit", "unit_ids": ["SVK-0038:u01199"], "source_id": "SVK-0038", "dapt_split": "train", "dapt_seen_at_train": true}, "scoring": [{"all_of": ["sthanakavasi"], "any_of": ["scripture", "accept", "read"]}], "source_contains": ["The Terapanthi accept the Sthanakavasi scriptures"], "abstention_case": false, "notes": ""}
{"example_id": "DAPT01EVAL-009", "category": "PRAKRIT", "language": "hi", "question": "पाइय-सद्द-महान्नवो के अनुसार प्राकृत शब्द 'अहिंसण' का क्या अर्थ है?", "expected_answer_or_reference": "अहिंसा (ahimsa).", "provenance": {"role": "grounding_unit", "unit_ids": ["SVK-2006:u04075"], "source_id": "SVK-2006", "dapt_split": "train", "dapt_seen_at_train": true}, "scoring": [{"any_of": ["अहिंसा", "ahimsa", "ahinsa", "non-violence", "non-injury"]}], "source_contains": ["अहिंसण", "अहिंसा"], "abstention_case": false, "notes": ""}
{"example_id": "DAPT01EVAL-010", "category": "PRAKRIT", "language": "hi", "question": "पाइय-सद्द-महान्नवो में प्राकृत शब्द 'उवस्सय' के लिए क्या दिया गया है और वह क्या होता है?", "expected_answer_or_reference": "उपाश्रय — जैन साधुओं के निवास करने का स्थान (residence of Jain ascetics).", "provenance": {"role": "grounding_unit", "unit_ids": ["SVK-2007:u09904"], "source_id": "SVK-2007", "dapt_split": "train", "dapt_seen_at_train": true}, "scoring": [{"any_of": ["उपाश्रय", "upashraya", "upāśraya", "upasraya"]}, {"any_of": ["निवास", "residence", "staying", "abode", "place"]}], "source_contains": ["उवस्सय", "उपाश्रय", "निवास"], "abstention_case": false, "notes": ""}
{"example_id": "DAPT01EVAL-011", "category": "PRAKRIT", "language": "hi", "question": "पाइय-सद्द-महान्नवो में प्राकृत शब्द 'सामइगि' का हिंदी रूप और अर्थ क्या दिया गया है?", "expected_answer_or_reference": "सामायिक वाला (samayika) — one who practises Samayika.", "provenance": {"role": "grounding_unit", "unit_ids": ["SVK-2006:u39393"], "source_id": "SVK-2006", "dapt_split": "train", "dapt_seen_at_train": true}, "scoring": [{"any_of": ["सामायिक", "samayika", "samayik"]}, {"any_of": ["वाल", "वाला", "practis", "perform"]}], "source_contains": ["सामइगि", "सामायिक"], "abstention_case": false, "notes": ""}
{"example_id": "DAPT01EVAL-012", "category": "PRAKRIT", "language": "en", "question": "In Woolner's Introduction to Prakrit, which Prakrit was regarded as the 'Prakrt par excellence'?", "expected_answer_or_reference": "Maharastri.", "provenance": {"role": "grounding_unit", "unit_ids": ["SVK-2008:u00366"], "source_id": "SVK-2008", "dapt_split": "train", "dapt_seen_at_train": true}, "scoring": [{"any_of": ["maharastri", "mahārāṣṭrī", "maharashtri", "māhārāṣṭrī"]}], "source_contains": ["Maharastri was regarded as the Prakrt par excellence"], "abstention_case": false, "notes": ""}
{"example_id": "DAPT01EVAL-013", "category": "HINDI", "language": "hi", "question": "उत्तराध्ययन सूत्र की रचना किसने, कहाँ और किस अवसर पर की थी?", "expected_answer_or_reference": "श्रमण भगवान् महावीर ने, पावापुरी के अंतिम समवसरण में, निर्वाण से कुछ समय पूर्व।", "provenance": {"role": "grounding_unit", "unit_ids": ["SVK-2020:u00021"], "source_id": "SVK-2020", "dapt_split": "train", "dapt_seen_at_train": true}, "scoring": [{"all_of": ["महावीर", "पावापुरी"], "any_of": ["समवसरण", "निर्वाण"]}], "source_contains": ["महावीर ने", "पावापुरी", "अन्तिम समवसरण"], "abstention_case": false, "notes": ""}
{"example_id": "DAPT01EVAL-014", "category": "HINDI", "language": "hi", "question": "'उत्तराध्ययन' शब्द का शाब्दिक अर्थ क्या बताया गया है?", "expected_answer_or_reference": "उत्तर + अध्ययन = उत्तम शास्त्र / श्रेष्ठ शास्त्र (excellent or supreme scripture).", "provenance": {"role": "grounding_unit", "unit_ids": ["SVK-2020:u00020"], "source_id": "SVK-2020", "dapt_split": "train", "dapt_seen_at_train": true}, "scoring": [{"any_of": ["उत्तम", "श्रेष्ठ", "excellent", "supreme"]}], "source_contains": ["उत्तम", "शरेष्ठ"], "abstention_case": false, "notes": ""}
{"example_id": "DAPT01EVAL-015", "category": "HINDI", "language": "hi", "question": "उत्तराध्ययनसूत्र की व्याख्या के अनुसार 'विनीत' शिष्य कौन कहलाता है?", "expected_answer_or_reference": "जो गुरु की आज्ञा और निर्देश का पालन करता है, गुरु के पास रहकर सेवा-शुश्रूषा करता है, और इंगित (शरीर की चेष्टा) व आकार से मनोभावों को समंजस्य करता है।", "provenance": {"role": "grounding_unit", "unit_ids": ["SVK-2020:u00168"], "source_id": "SVK-2020", "dapt_split": "train", "dapt_seen_at_train": true}, "scoring": [{"all_of": ["गुरु"]}, {"any_of": ["आज्ञा", "निर्देश", "पालन"]}, {"any_of": ["सेवा", "शुश्रूषा", "service"]}], "source_contains": ["आज्ञा", "निर्देश", "सेवा"], "abstention_case": false, "notes": ""}
{"example_id": "DAPT01EVAL-016", "category": "HINDI", "language": "hi", "question": "'अविनीत' शिष्य की पहचान उत्तराध्ययनसूत्र में क्यै बताई गई है?", "expected_answer_or_reference": "जो गुरु की आज्ञा-निर्देश का पालन नहीं करता, गुरुजनों की सेवा से दूर रहता है और उनके प्रतिकूल आचरण करता है, वह अविनीत है।", "provenance": {"role": "grounding_unit", "unit_ids": ["SVK-2020:u00179"], "source_id": "SVK-2020", "dapt_split": "train", "dapt_seen_at_train": true}, "scoring": [{"all_of": ["गुरु"]}, {"any_of": ["नहीं", "सेवा", "दूर"]}, {"any_of": ["अविनीत"]}], "source_contains": ["गुरु", "अविनीत"], "abstention_case": false, "notes": ""}
{"example_id": "DAPT01EVAL-017", "category": "GUJARATI", "language": "gu", "question": "જૈન શાળાના બાળકોને દરરોજ શું કરવાનું કહેવામાં આવ્યું છે?", "expected_answer_or_reference": "સામાયિક કરવી (to practise Samayika during the Jain-school period).", "provenance": {"role": "grounding_unit", "unit_ids": ["SVK-2027:u095770"], "source_id": "SVK-2027", "dapt_split": "test", "dapt_seen_at_train": false}, "scoring": [{"any_of": ["સામાયિક", "સમાયિક", "samayika", "samayik"]}], "source_contains": ["જૈન શાળાના વખતમાં સામાયિક કરવી"], "abstention_case": false, "notes": ""}
{"example_id": "DAPT01EVAL-018", "category": "GUJARATI", "language": "gu", "question": "જૈન માહાત્મ્ય મુજબ પ્રભુએ ક્યાં મોક્ષ પ્રાપ્ત કર્યો?", "expected_answer_or_reference": "અષ્ટપદ પર્વત ઉપર (on the Astapada mountain).", "provenance": {"role": "grounding_unit", "unit_ids": ["SVK-2014:u00096"], "source_id": "SVK-2014", "dapt_split": "train", "dapt_seen_at_train": true}, "scoring": [{"any_of": ["અષ્ટપદ", "astapada", "અષ્ટપાદ"]}], "source_contains": ["અષ્ટપદ પર્વત"], "abstention_case": false, "notes": ""}
{"example_id": "DAPT01EVAL-019", "category": "GUJARATI", "language": "gu", "question": "પુસ્તક 'જૈન સાથન કવાસી' (1928) ના લેખક કોણ છે?", "expected_answer_or_reference": "સ્વામી જીતમલ (Swami Jitmal).", "provenance": {"role": "manifest", "source_id": "SVK-2010", "manifest_field": "author", "source_title": "Jain Sathan Kavasi (1928)", "dapt_split": "train", "dapt_seen_at_train": true}, "scoring": [{"any_of": ["jitmal", "જીતમલ", "swami jitmal"]}], "source_contains": [], "abstention_case": false, "notes": ""}
{"example_id": "DAPT01EVAL-020", "category": "GUJARATI", "language": "gu", "question": "જૈન શાસનની રચના કયા ત્રણ તત્ત્વો પર આધારિત છે એમ નવયુગ ગ્રંથમાં શું કહેવાયું છે?", "expected_answer_or_reference": "અહિંસા, સંયમ અને તપ (ahiṃsā, saṃyama and tapa).", "provenance": {"role": "grounding_unit", "unit_ids": ["SVK-2012:u00063"], "source_id": "SVK-2012", "dapt_split": "train", "dapt_seen_at_train": true}, "scoring": [{"any_of": ["અહિંસા", "અહિ'સા", "ahimsa", "અહિંસ"]}, {"any_of": ["સંયમ", "સયમ", "samyam"]}, {"any_of": ["તપ", "tapa"]}], "source_contains": ["સયમ", "તપ"], "abstention_case": false, "notes": ""}
{"example_id": "DAPT01EVAL-021", "category": "SANSKRIT", "language": "en", "question": "According to the source manifest of this corpus, who is credited as the author of the Sanskrit work 'Sri Avasyaka Sutra Part-i' (1928)?", "expected_answer_or_reference": "Bhadrabahu.", "provenance": {"role": "manifest", "source_id": "SVK-2015", "manifest_field": "author", "source_title": "Sri Avasyaka Sutra Part-i (1928)", "language": "san", "dapt_split": "train", "dapt_seen_at_train": true}, "scoring": [{"any_of": ["bhadrabahu", "bhadrabahu", "bhadrabāhu"]}], "source_contains": [], "abstention_case": false, "notes": "Sanskrit-language category limited to Sanskrit work provenance: release corpus records contain 0 units with language code 'sa'."}
{"example_id": "DAPT01EVAL-022", "category": "SANSKRIT", "language": "en", "question": "In Stevenson's Kalpa Sutra translation, what is the Sanskrit technical term for the duty of confession/absolution, and what is the Gujarati word for it?", "expected_answer_or_reference": "Sanskrit: Pratikramana; Gujarati: Alavan.", "provenance": {"role": "grounding_unit", "unit_ids": ["SVK-1002:u00101"], "source_id": "SVK-1002", "dapt_split": "train", "dapt_seen_at_train": true}, "scoring": [{"all_of": ["pratikramana"], "any_of": ["alavan", "al-avan"]}], "source_contains": ["Sans. Pratikramana", "Gujarathi word", "Alavan"], "abstention_case": false, "notes": ""}
{"example_id": "DAPT01EVAL-023", "category": "SANSKRIT", "language": "en", "question": "According to Stevenson, what is the first vow taken by a Jaina ascetic, and what term is used for it?", "expected_answer_or_reference": "To refrain from destroying/killing living beings, whether subtle or movable or immovable (Ahimsarata).", "provenance": {"role": "grounding_unit", "unit_ids": ["SVK-0038:u00337"], "source_id": "SVK-0038", "dapt_split": "train", "dapt_seen_at_train": true}, "scoring": [{"any_of": ["refrain", "renounce", "destroying", "kill"]}, {"any_of": ["living beings", "life"]}, {"any_of": ["ahimsa", "ahimsarata", "non-kill"]}], "source_contains": ["first vow the Jaina ascetic takes", "Ahimsarata"], "abstention_case": false, "notes": ""}
{"example_id": "DAPT01EVAL-024", "category": "AGAM_GROUNDED", "language": "en", "question": "In this corpus's illustrated Agam series, which Agam and mool number is the Aavashyak Sutra?", "expected_answer_or_reference": "Agam 28, Mool 01 (Aavashyak Sutra, Sthanakvasi).", "provenance": {"role": "grounding_unit", "unit_ids": ["SVK-2022:u088898"], "source_id": "SVK-2022", "dapt_split": "val", "dapt_seen_at_train": false}, "scoring": [{"all_of": ["28"], "any_of": ["01", "mool 1", "first", "1"]}], "source_contains": ["Agam 28 Mool 01 Aavashyak"], "abstention_case": false, "notes": ""}
{"example_id": "DAPT01EVAL-025", "category": "AGAM_GROUNDED", "language": "en", "question": "In this corpus's illustrated Agam series, which Agam and mool number is the Dasvaikalik Sutra?", "expected_answer_or_reference": "Agam 29, Mool 02 (Dasvaikalik Sutra, Sthanakvasi).", "provenance": {"role": "grounding_unit", "unit_ids": ["SVK-2026:u094492"], "source_id": "SVK-2026", "dapt_split": "test", "dapt_seen_at_train": false}, "scoring": [{"all_of": ["29"], "any_of": ["02", "second", "mool 2"]}], "source_contains": ["Agam 29 Mool 02 Dasvaikalik"], "abstention_case": false, "notes": ""}
{"example_id": "DAPT01EVAL-026", "category": "AGAM_GROUNDED", "language": "en", "question": "According to the introduction of the Dasvaikalik Sutra in this corpus, how many Angas are there, how many are currently available, and what is the missing twelfth Anga called?", "expected_answer_or_reference": "Twelve Angas in all; eleven are currently available; the twelfth is Drstivada (Dṛṣṭivāda), which is not available.", "provenance": {"role": "grounding_unit", "unit_ids": ["SVK-2026:u094511"], "source_id": "SVK-2026", "dapt_split": "test", "dapt_seen_at_train": false}, "scoring": [{"any_of": ["12", "twelve"]}, {"any_of": ["11", "eleven"]}, {"any_of": ["drishti", "dṛṣṭi", "dristi", "drastivada", "dṛṣṭivāda", "tristivada", "dṛṣṭivād"]}], "source_contains": ["12 aNg", "11 aMga", "dRSTivAda"], "abstention_case": false, "notes": ""}
{"example_id": "DAPT01EVAL-027", "category": "AGAM_GROUNDED", "language": "en", "question": "In this corpus's illustrated Agam series, what position does the Aupapatik Sutra hold among the Upangas, and which Anga does it accompany?", "expected_answer_or_reference": "It is the First Upanga, associated with the first Anga (Acaranga Sutra).", "provenance": {"role": "grounding_unit", "unit_ids": ["SVK-2029:u096137", "SVK-2029:u096175"], "source_id": "SVK-2029", "dapt_split": "test", "dapt_seen_at_train": false}, "scoring": [{"all_of": ["first"]}, {"any_of": ["upanga", "upang"]}, {"any_of": ["acharanga", "acaranga", "first anga"]}], "source_contains": ["The First Upanga", "Acharanga Sutra is the first Anga"], "abstention_case": false, "notes": ""}
{"example_id": "DAPT01EVAL-028", "category": "STHANAKAVASI_DISTINCTION", "language": "en", "question": "Are the Sthanakavasi counted among the Svetambara or the Digambara, according to Stevenson and this corpus's source manifest?", "expected_answer_or_reference": "They are Svetambara (manifest: tradition SHWETAMBAR, sect STHANAKAVASI); Stevenson groups Svetambara and Sthanakavasi together and contrasts them with Digambara.", "provenance": {"role": "grounding_unit", "unit_ids": ["SVK-0038:u00185"], "source_id": "SVK-0038", "dapt_split": "train", "dapt_seen_at_train": true, "manifest_source_id": "SVK-2026"}, "scoring": [{"all_of": ["svetambara"], "none_of": ["are digambara", "sthānakavāsī are digambara", "sthankavasi are digambara"]}], "source_contains": ["all Svetambara and Sthanakavasi practically agree"], "abstention_case": false, "notes": "Forbids claiming the Sthanakavasi are Digambara; correct answers must affirm Svetambara affiliation."}
{"example_id": "DAPT01EVAL-029", "category": "STHANAKAVASI_DISTINCTION", "language": "en", "question": "According to Stevenson, do the Sthanakavasi Jaina accept the Kalpa Sutra, and what do they do instead on the fasting days?", "expected_answer_or_reference": "No — the Sthanakavasi do not accept the Kalpa Sutra; they go to their own Upasaro and hear Mahavira's life read in their own scriptures.", "provenance": {"role": "grounding_unit", "unit_ids": ["SVK-0038:u01204"], "source_id": "SVK-0038", "dapt_split": "train", "dapt_seen_at_train": true}, "scoring": [{"any_of": ["do not accept", "don't accept", "not accept", "reject", "no"]}, {"any_of": ["upasaro", "own scriptures", "mahavira's life", "not accept the kalpa"]}], "source_contains": ["Sthanakavasi Jaina, who do not accept the Kalpa Sutra"], "abstention_case": false, "notes": ""}
{"example_id": "DAPT01EVAL-030", "category": "STHANAKAVASI_DISTINCTION", "language": "en", "question": "According to Stevenson, what is the Digambara position on the Svetambara Canon?", "expected_answer_or_reference": "The Digambara reject the Svetambara Canon.", "provenance": {"role": "grounding_unit", "unit_ids": ["SVK-0038:u00171"], "source_id": "SVK-0038", "dapt_split": "train", "dapt_seen_at_train": true}, "scoring": [{"all_of": ["digambara"], "any_of": ["reject", "refuse", "do not accept"]}], "source_contains": ["The Digambara reject the Svetambara Canon"], "abstention_case": false, "notes": ""}
{"example_id": "DAPT01EVAL-031", "category": "STHANAKAVASI_DISTINCTION", "language": "en", "question": "According to Stevenson, does a Sthanakavasi ascetic take a new name at diksha like Digambara and Svetambara ascetics do?", "expected_answer_or_reference": "No — Digambara and Svetambara ascetics take a new name, whereas the Sthanakavasi ascetic retains his old one.", "provenance": {"role": "grounding_unit", "unit_ids": ["SVK-0038:u00297"], "source_id": "SVK-0038", "dapt_split": "train", "dapt_seen_at_train": true}, "scoring": [{"any_of": ["retain", "keeps", "old name", "same name", "still retain", "old one", "no"]}, {"any_of": ["sthānakavāsī", "sthankavasi", "sthana", "sthanakavasi", "not"]}], "source_contains": ["if he be a Sthanakavasi", "retain his old one"], "abstention_case": false, "notes": ""}
{"example_id": "DAPT01EVAL-032", "category": "SOURCE_ATTRIBUTION", "language": "en", "question": "Who wrote the book 'Sthanakvasi Jain Itihas' listed in this corpus's source manifest?", "expected_answer_or_reference": "Kesrichand Bhandari.", "provenance": {"role": "manifest", "source_id": "SVK-2027", "manifest_field": "author", "source_title": "Sthanakvasi Jain Itihas", "dapt_split": "test", "dapt_seen_at_train": false}, "scoring": [{"any_of": ["kesrichand", "kesarichand", "bhandari"]}], "source_contains": [], "abstention_case": false, "notes": ""}
{"example_id": "DAPT01EVAL-033", "category": "SOURCE_ATTRIBUTION", "language": "en", "question": "Who translated 'Gaina Sutras' (Acaranga and Sutrakrtanga) for the Sacred Books of the East, according to this corpus's source manifest?", "expected_answer_or_reference": "Hermann Jacobi.", "provenance": {"role": "manifest", "source_id": "SVK-1001", "manifest_field": "author", "source_title": "Gaina Sutras (Sacred Books of the East): Acaranga and Sutrakrtanga", "dapt_split": "train", "dapt_seen_at_train": true}, "scoring": [{"any_of": ["jacobi", "hermann"]}], "source_contains": [], "abstention_case": false, "notes": ""}
{"example_id": "DAPT01EVAL-034", "category": "SOURCE_ATTRIBUTION", "language": "en", "question": "Who is the author of 'Notes on Modern Jainism' (1910), according to this corpus's source manifest?", "expected_answer_or_reference": "Mrs. Sinclair Stevenson.", "provenance": {"role": "manifest", "source_id": "SVK-0038", "manifest_field": "author", "source_title": "Notes on Modern Jainism (1910)", "dapt_split": "train", "dapt_seen_at_train": true}, "scoring": [{"any_of": ["stevenson"]}, {"any_of": ["sinclair", "mrs"]}], "source_contains": [], "abstention_case": false, "notes": ""}
{"example_id": "DAPT01EVAL-035", "category": "SOURCE_ATTRIBUTION", "language": "en", "question": "On the title page of the Illustrated Aupapatik Sutra in this corpus, who is listed as Editor-in-Chief?", "expected_answer_or_reference": "Shri Amar Muni.", "provenance": {"role": "grounding_unit", "unit_ids": ["SVK-2029:u096137"], "source_id": "SVK-2029", "dapt_split": "test", "dapt_seen_at_train": false}, "scoring": [{"all_of": ["amar", "muni"]}], "source_contains": ["Editor-in-Chief", "Shri Amar Muni"], "abstention_case": false, "notes": ""}
{"example_id": "DAPT01EVAL-036", "category": "ABSTENTION", "language": "en", "question": "In what year was 'Sthanakvasi Jain Itihas' by Kesrichand Bhandari published?", "expected_answer_or_reference": "NOT MEASURED / abstention: neither the manifest publication_year nor any text in the source states a publication year.", "provenance": {"role": "manifest", "source_id": "SVK-2027", "manifest_field": "publication_year", "source_title": "Sthanakvasi Jain Itihas", "dapt_split": "test", "dapt_seen_at_train": false}, "scoring": [{"abstention_markers": ["not stated", "unknown", "not available", "cannot", "no year", "unspecified", "do not know", "don't know", "not mentioned", "not mention", "not given", "nowhere", "doesn't state", "does not state", "unable to determine", "not recorded", "not specified", "not know", "not have", "couldn't find", "could not find", "no record", "no information"], "forbidden_claims": ["(18|19|20)\\d{2}"]}], "source_contains": [], "abstention_case": true, "notes": "Absence verified: manifest publication_year empty; no real 18xx/19xx/20xx year token in SVK-2027 text (only the boilerplate string 'JainQQ source SVK-2027')."}
{"example_id": "DAPT01EVAL-037", "category": "ABSTENTION", "language": "en", "question": "In which year exactly was the Terapanth founded?", "expected_answer_or_reference": "NOT MEASURED / abstention: Stevenson gives only 'about 150 years ago' (relative to 1910); no exact founding year is stated in the corpus.", "provenance": {"role": "grounding_unit", "unit_ids": ["SVK-0038:u01198"], "source_id": "SVK-0038", "dapt_split": "train", "dapt_seen_at_train": true}, "scoring": [{"abstention_markers": ["about", "approximately", "circa", "around", "150 years", "19th century", "not stated", "unknown", "cannot", "do not know", "don't know", "not mentioned", "exact", "no exact", "unclear", "unsure", "earlier", "1910"], "forbidden_claims": ["in (17|18|19|20)\\d{2}", "founded in (17|18|19|20)\\d{2}(?!\\s*(or|to))", "\\b(17|18)\\d{2}\\b"]}], "source_contains": ["about 150 years ago"], "abstention_case": true, "notes": "Correct behaviour: qualify ('about 150 years ago') or state that no exact year is given. Forbidden: an unqualified bare 15th-20th-century year."}
{"example_id": "DAPT01EVAL-038", "category": "ABSTENTION", "language": "en", "question": "Who published 'Notes on Modern Jainism' (1910)?", "expected_answer_or_reference": "NOT MEASURED / abstention: the manifest publisher field is 'unknown' and no publisher statement appears in the source text.", "provenance": {"role": "manifest", "source_id": "SVK-0038", "manifest_field": "publisher", "source_title": "Notes on Modern Jainism (1910)", "dapt_split": "train", "dapt_seen_at_train": true}, "scoring": [{"abstention_markers": ["not stated", "unknown", "not available", "cannot", "do not know", "don't know", "not mentioned", "not given", "nowhere", "does not state", "doesn't state", "unable", "not recorded", "not specified", "no information", "no record"], "forbidden_claims": ["(?:publisher is|published by|issued by)\\s+(?!not\\b|unknown|no\\b|none)"]}], "source_contains": [], "abstention_case": true, "notes": "Absence verified: manifest publisher='unknown'; 0 hits for publish/printed/press/imprint within 300 chars of any 'Notes on Modern Jainism' mention in SVK-0038 text."}
{"example_id": "DAPT01EVAL-039", "category": "ABSTENTION", "language": "en", "question": "How many Agams do the Digambara tradition accept?", "expected_answer_or_reference": "NOT MEASURED / abstention: the governed corpus states the Sthanakavasi/Svetambara enumeration but never states a Digambara Agam count.", "provenance": {"role": "corpus_absence", "unit_ids": [], "dapt_split": "train", "dapt_seen_at_train": true, "absence_check": "no unit co-occurs 'Digambara' with a number + Agam/Anga/scripture pattern in data/release/training_corpus.jsonl (0 hits)"}, "scoring": [{"abstention_markers": ["not stated", "unknown", "not available", "cannot", "do not know", "don't know", "not mentioned", "not given", "does not state", "doesn't state", "unable", "not recorded", "not specified", "no information", "no record", "corpus", "sources"], "forbidden_claims": ["\\b(24|36|45|64|72)\\s*(agam|aagam)"]}], "source_contains": [], "abstention_case": true, "notes": "Absence verified corpus-wide: 0 hits for number+Agam/Anga near 'Digambara'."}
{"example_id": "DAPT01EVAL-040", "category": "PRACTICE", "language": "en", "question": "According to Stevenson, how long must a layman spend over Samayika?", "expected_answer_or_reference": "Forty-eight minutes.", "provenance": {"role": "grounding_unit", "unit_ids": ["SVK-0038:u01132"], "source_id": "SVK-0038", "dapt_split": "train", "dapt_seen_at_train": true}, "scoring": [{"any_of": ["forty-eight", "forty eight", "48"]}, {"any_of": ["minute"]}], "source_contains": ["fbrty-oight minutes over Samayika"], "abstention_case": false, "notes": "Source has OCR 'fbrty-oight'; reference transcription is forty-eight (confirmed by the same figure in u01125 'about forty-eight minutes')."}
{"example_id": "DAPT01EVAL-041", "category": "PRACTICE", "language": "en", "question": "According to Stevenson, into how many parts does Samayika consist?", "expected_answer_or_reference": "Eight parts.", "provenance": {"role": "grounding_unit", "unit_ids": ["SVK-0038:u01125"], "source_id": "SVK-0038", "dapt_split": "train", "dapt_seen_at_train": true}, "scoring": [{"any_of": ["eight", "8"]}, {"any_of": ["part"]}], "source_contains": ["consists of eight parts"], "abstention_case": false, "notes": ""}
{"example_id": "DAPT01EVAL-042", "category": "PRACTICE", "language": "en", "question": "According to the Pratikraman source in this corpus, how many essential acts (Avashyaka) are there, and what is Pratikraman used as for them?", "expected_answer_or_reference": "Six Avashyaka (essential acts); Pratikraman is used as a common noun covering all six.", "provenance": {"role": "grounding_unit", "unit_ids": ["SVK-2024:u091510"], "source_id": "SVK-2024", "dapt_split": "val", "dapt_seen_at_train": false}, "scoring": [{"any_of": ["six", "6"]}, {"any_of": ["avashyaka", "avasayika", "essential act"]}], "source_contains": ["common noun for all six essential acts (six Avashyaka)"], "abstention_case": false, "notes": ""}
{"example_id": "DAPT01EVAL-043", "category": "PRACTICE", "language": "en", "question": "In the Sthanang Sutra material of this corpus, in which direction(s) and for how long per direction is the Sarvatobhadra pratima kayotsarga practised?", "expected_answer_or_reference": "It faces all ten directions (four cardinal, four intermediate, zenith and nadir), for at least one ahoratra (24 hours) per direction.", "provenance": {"role": "grounding_unit", "unit_ids": ["SVK-2025:u092214"], "source_id": "SVK-2025", "dapt_split": "val", "dapt_seen_at_train": false}, "scoring": [{"any_of": ["ten", "10"]}, {"any_of": ["24", "ahoratra", "day and night", "one day", "a day and a night"]}], "source_contains": ["Sarvatobhadraa pratima", "facing ten directions", "ahoratra"], "abstention_case": false, "notes": ""}
{"example_id": "DAPT01EVAL-044", "category": "MULTILINGUAL_MAPPING", "language": "en", "question": "In the Sacred Books of the East Acaranga translation, the Prakrit word 'sthana' is explained by which Sanskrit/Jain technical term?", "expected_answer_or_reference": "Kayotsarga.", "provenance": {"role": "grounding_unit", "unit_ids": ["SVK-1001:u01494"], "source_id": "SVK-1001", "dapt_split": "train", "dapt_seen_at_train": true}, "scoring": [{"any_of": ["kayotsarga", "kayotsarga", "kāyotsarga", "kayotsarg"]}], "source_contains": ["sthana is explained kayotsarga"], "abstention_case": false, "notes": ""}
{"example_id": "DAPT01EVAL-045", "category": "MULTILINGUAL_MAPPING", "language": "gu", "question": "સ્ટીવેન્સનના કલ્પ સૂત્ર અનુવાદમાં પશ્ચાતાપ/અભય માટેનો ગુજરાતી શબ્દ શું છે? (સંસ્કૃત શબ્દ પ્રતિક્રમણ સાથે)", "expected_answer_or_reference": "આલવણ (Alavan).", "provenance": {"role": "grounding_unit", "unit_ids": ["SVK-1002:u00101"], "source_id": "SVK-1002", "dapt_split": "train", "dapt_seen_at_train": true}, "scoring": [{"any_of": ["alavan", "આલવણ"]}], "source_contains": ["The Gujarathi word that expresses the priestly absolution, is Alavan"], "abstention_case": false, "notes": "Same source unit as case 022 but a different (Gujarati-language) question and a different required key term."}
{"example_id": "DAPT01EVAL-046", "category": "MULTILINGUAL_MAPPING", "language": "en", "question": "In Woolner's Introduction to Prakrit, what does Sanskrit 'n' generally become in Prakrit?", "expected_answer_or_reference": "It is generally represented in Prakrit by 'n' (with the dental n occurring before other dentals).", "provenance": {"role": "grounding_unit", "unit_ids": ["SVK-2008:u00111"], "source_id": "SVK-2008", "dapt_split": "train", "dapt_seen_at_train": true}, "scoring": [{"all_of": ["sanskrit"]}, {"any_of": ["represented", "written", "correspond", "become"]}, {"any_of": ["prakrit"]}], "source_contains": ["Sanskrit n is generally represented in Prakrit by n"], "abstention_case": false, "notes": ""}
{"example_id": "DAPT01EVAL-047", "category": "MULTILINGUAL_MAPPING", "language": "hi", "question": "पाइय-सद्द-महान्नवो में प्राकृत शब्द 'मोक्क' के लिए क्या दिया गया है?", "expected_answer_or_reference": "मुक्त (mukta / liberation).", "provenance": {"role": "grounding_unit", "unit_ids": ["SVK-2007:u32618"], "source_id": "SVK-2007", "dapt_split": "train", "dapt_seen_at_train": true}, "scoring": [{"any_of": ["मुक्त", "mukta"]}], "source_contains": ["मोक्क", "मुक्त"], "abstention_case": false, "notes": ""}
"""


SYSTEM_PROMPT = (
    "You are a careful assistant for Jain studies. "
    "Answer the user's question concisely (in 1-3 sentences). "
    "If you are unsure or the information is not available, say so."
)
MAX_NEW_TOKENS = 192
SEED = 42


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def load_cases() -> list[dict]:
    text = CASES_JSON
    if "__CASES__" in text:
        raise SystemExit("kernel was packed without eval cases")
    lines = [ln for ln in text.splitlines() if ln.strip()]
    payload = ("\n".join(lines) + "\n").encode()
    digest = hashlib.sha256(payload).hexdigest()
    if digest != EXPECTED["cases_sha256"]:
        raise SystemExit(f"frozen cases hash mismatch: {digest}")
    return [json.loads(ln) for ln in lines]


def build_prompt(tokenizer, question: str) -> tuple[str, str]:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    if getattr(tokenizer, "chat_template", None):
        prompt = tokenizer.apply_chat_template(
            messages, add_generation_prompt=True, tokenize=False
        )
        return prompt, "chat_template"
    prompt = f"{SYSTEM_PROMPT}\n\nQuestion: {question}\nAnswer concisely:\n"
    return prompt, "plain_fallback"


def build_eval_prompt(tokenizer, messages: list[dict]) -> tuple[str, str]:
    # Training format: user+assistant turns, no system prompt
    # (mirror experiments/sft_01/kaggle/train.py build_example).
    prompt_msgs = messages[:-1]
    if getattr(tokenizer, "chat_template", None):
        prompt = tokenizer.apply_chat_template(
            prompt_msgs, add_generation_prompt=True, tokenize=False
        )
        return prompt, "chat_template"
    q = prompt_msgs[-1]["content"]
    return f"Question: {q}\nAnswer concisely:\n", "plain_fallback"


def generate(model, tokenizer, prompt: str) -> dict:
    inputs = tokenizer(prompt, return_tensors="pt")
    inputs = {k: v.to(model.device) for k, v in inputs.items()}
    t0 = time.time()
    with torch.no_grad():
        out = model.generate(
            **inputs,
            max_new_tokens=MAX_NEW_TOKENS,
            do_sample=False,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )
    new_ids = out[0][inputs["input_ids"].shape[1]:]
    text = tokenizer.decode(new_ids, skip_special_tokens=True)
    return {
        "answer": text.strip(),
        "new_tokens": int(new_ids.shape[0]),
        "decode_seconds": round(time.time() - t0, 3),
    }


def run_cases(model, tokenizer, cases: list[dict]) -> list[dict]:
    rows = []
    for i, c in enumerate(cases, 1):
        prompt, style = build_prompt(tokenizer, c["question"])
        gen = generate(model, tokenizer, prompt)
        row = {
            "example_id": c["example_id"],
            "category": c["category"],
            "language": c["language"],
            "question": c["question"],
            "answer": gen["answer"],
            "prompt_style": style,
            "system_prompt": SYSTEM_PROMPT,
            "decoding": "greedy",
            "max_new_tokens": MAX_NEW_TOKENS,
            "new_tokens": gen["new_tokens"],
            "decode_seconds": gen["decode_seconds"],
            "seed": SEED,
        }
        rows.append(row)
        log(
            f"  [A {i}/{len(cases)}] {c['example_id']} {c['category']} "
            f"({gen['new_tokens']} tok) {gen['answer'][:110]!r}"
        )
    return rows


def run_eval(model, tokenizer, rows_in: list[dict]) -> list[dict]:
    rows = []
    for i, r in enumerate(rows_in, 1):
        msgs = r["messages"]
        if msgs[-1]["role"] != "assistant":
            raise SystemExit(f"eval row {r.get('example_id')} does not end with assistant")
        prompt, style = build_eval_prompt(tokenizer, msgs)
        gen = generate(model, tokenizer, prompt)
        row = {
            "example_id": r["example_id"],
            "category": r.get("category"),
            "source_id": r.get("source_id"),
            "question": r["question"],
            "reference_answer": r.get("answer"),
            "answer": gen["answer"],
            "prompt_style": style,
            "system_prompt": None,
            "decoding": "greedy",
            "max_new_tokens": MAX_NEW_TOKENS,
            "new_tokens": gen["new_tokens"],
            "decode_seconds": gen["decode_seconds"],
            "seed": SEED,
        }
        rows.append(row)
        log(
            f"  [B {i}/{len(rows_in)}] {r['example_id']} "
            f"({gen['new_tokens']} tok) {gen['answer'][:110]!r}"
        )
    return rows


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    log(f"wrote {path} ({len(rows)} rows)")


def main() -> None:
    torch.manual_seed(SEED)
    cases = load_cases()
    log(f"{len(cases)} frozen cases (hash ok)")

    adapter_dir = resolve_adapter_dir()
    adapter_sha = sha256_file(adapter_dir / "adapter_model.safetensors")
    if adapter_sha != EXPECTED["adapter_sha256"]:
        raise SystemExit(f"adapter sha256 mismatch: {adapter_sha}")
    log(f"adapter={adapter_dir} sha256 ok")

    eval_path = resolve_eval_path()
    eval_sha = sha256_file(eval_path)
    if eval_sha != EXPECTED["eval_sha256"]:
        raise SystemExit(f"eval.jsonl sha256 mismatch: {eval_sha}")
    eval_rows = [json.loads(ln) for ln in
                 Path(eval_path).read_text(encoding="utf-8").splitlines() if ln.strip()]
    if len(eval_rows) != 13:
        raise SystemExit(f"expected 13 eval rows, got {len(eval_rows)}")
    log(f"eval={eval_path} rows={len(eval_rows)} sha256 ok")

    if not (adapter_dir / "adapter_model.safetensors").exists():
        raise FileNotFoundError(f"adapter files not found under {adapter_dir}")

    bnb = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
    )

    log(f"loading tokenizer {MODEL_ID}")
    tok = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    log(f"loading base model {MODEL_ID} (4-bit nf4)")
    t_load = time.time()
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        quantization_config=bnb,
        device_map="auto",
        trust_remote_code=True,
        torch_dtype=torch.float16,
    )
    load_s = time.time() - t_load

    log("attaching SFT-02 adapter (no merge)")
    t0 = time.time()
    model = PeftModel.from_pretrained(model, str(adapter_dir), is_trainable=False)
    model.eval()
    adapter_s = time.time() - t0

    log("=== ARM: BASE + DAPT-01 + SFT-02 (SFT-02 final adapter) ===")
    t0 = time.time()
    sft_rows = run_cases(model, tok, cases)
    frozen_s = time.time() - t0
    write_jsonl(WORK / "dapt01_sft02_results.jsonl", sft_rows)

    log("=== sft_eval_v2 per-example generations ===")
    t0 = time.time()
    gen_rows = run_eval(model, tok, eval_rows)
    eval_s = time.time() - t0
    write_jsonl(WORK / "sft02_eval_results.jsonl", gen_rows)

    gpu = torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
    metadata = {
        "task": "TASK 68 SFT-02 EVALUATION (SFT-02 arm on frozen Task-60 set)",
        "model": MODEL_ID,
        "adapter_dataset": SFT_ADAPTER_DATASET,
        "adapter_dir": str(adapter_dir),
        "training_experiment": "SFT-02",
        "adapter_sha256": adapter_sha,
        "adapter_merged": False,
        "quantization": "4bit-nf4-double, compute dtype fp16 (identical to Task 60)",
        "system_prompt": SYSTEM_PROMPT,
        "prompt_style": "chat_template if available else plain_fallback",
        "decoding": "greedy (do_sample=False)",
        "max_new_tokens": MAX_NEW_TOKENS,
        "seed": SEED,
        "n_cases": len(cases),
        "n_eval_rows": len(gen_rows),
        "cases_sha256": EXPECTED["cases_sha256"],
        "eval_file_sha256": eval_sha,
        "eval_dataset": DATA_DATASET,
        "gpu": gpu,
        "torch": torch.__version__,
        "python": platform.python_version(),
        "transformers": __import__("transformers").__version__,
        "peft": __import__("peft").__version__,
        "bitsandbytes": __import__("bitsandbytes").__version__,
        "model_load_seconds": round(load_s, 1),
        "adapter_attach_seconds": round(adapter_s, 1),
        "frozen_infer_seconds": round(frozen_s, 1),
        "eval_infer_seconds": round(eval_s, 1),
        "env_KAGGLE_KERNEL": os.environ.get("KAGGLE_KERNEL_RUN_TYPE"),
        "finished_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "arms_note": (
            "Only the SFT-02 arm is generated here; BASE, DAPT-01 and SFT-01 arms "
            "are the frozen result files dapt01_base_results.jsonl, "
            "dapt01_dapt_results.jsonl and dapt01_sft_results.jsonl "
            "(same cases, prompts, decoding)."
        ),
    }
    (WORK / "task68_sft02_infer_metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    log(f"metadata: {json.dumps(metadata)}")
    log("TASK 68 INFER KERNEL DONE")


if __name__ == "__main__":
    main()
