"""Pack data/evaluation/dapt01_eval_cases.jsonl into the Task-65 inference kernel.

Rewrites the CASES_JSON placeholder inside kaggle_infer/infer.py.
Run after any change to the eval cases file (the kernel aborts on hash
mismatch, so packed bytes must equal the frozen file).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
CASES = REPO / "data" / "evaluation" / "dapt01_eval_cases.jsonl"
KERNEL = REPO / "experiments" / "sft_01" / "kaggle_infer" / "infer.py"

MARKER_START = 'CASES_JSON = r"""'
MARKER_END = '"""\n\n\nSYSTEM_PROMPT'


def main() -> int:
    raw = CASES.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    lines = [ln.rstrip("\n") for ln in raw.decode("utf-8").splitlines() if ln.strip()]
    payload = "\n".join(lines)
    for bad in ('"""', "\\\\" + '"""'):
        if bad in payload:
            raise SystemExit(f"cases payload contains {bad!r}; cannot embed safely")
    # packed bytes (payload + newline) must equal the frozen file bytes
    if (payload + "\n").encode() != raw:
        raise SystemExit("cases payload does not reproduce the frozen file bytes")

    src = KERNEL.read_text(encoding="utf-8")
    start = src.index(MARKER_START) + len(MARKER_START)
    end = src.index(MARKER_END, start) + len('"""')
    new_src = src[:start] + "\n" + payload + "\n" + src[end - len('"""'):]
    KERNEL.write_text(new_src, encoding="utf-8")

    # sanity: reload-able and hash-stable
    embedded = new_src.split(MARKER_START, 1)[1].split('"""', 1)[0].strip()
    parsed = [json.loads(ln) for ln in embedded.splitlines()]
    assert len(parsed) == len(lines), (len(parsed), len(lines))
    packed_sha = hashlib.sha256((embedded + "\n").encode()).hexdigest()
    assert packed_sha == digest, (packed_sha, digest)
    print(f"packed {len(parsed)} cases into {KERNEL.relative_to(REPO)} (sha256 {digest})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
