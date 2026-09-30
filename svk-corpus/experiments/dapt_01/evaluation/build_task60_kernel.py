"""Pack data/evaluation/dapt01_eval_cases.jsonl into the Kaggle inference kernel.

Rewrites the CASES_JSON placeholder inside kaggle/task60_infer_kaggle.py.
Run after any change to the eval cases file.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
CASES = REPO / "data" / "evaluation" / "dapt01_eval_cases.jsonl"
KERNEL = REPO / "experiments" / "dapt_01" / "evaluation" / "kaggle" / "task60_infer_kaggle.py"

MARKER_START = 'CASES_JSON = r"""'
MARKER_END = '"""\n\n\ndef log'


def main() -> int:
    lines = [ln.rstrip("\n") for ln in CASES.read_text(encoding="utf-8").splitlines() if ln.strip()]
    payload = "\n".join(lines)
    for bad in ('"""', "\\\\" + '"""'):
        if bad in payload:
            raise SystemExit(f"cases payload contains {bad!r}; cannot embed safely")

    src = KERNEL.read_text(encoding="utf-8")
    start = src.index(MARKER_START) + len(MARKER_START)
    end = src.index(MARKER_END, start) + len('"""')
    new_src = src[:start] + "\n" + payload + "\n" + src[end - len('"""'):]
    KERNEL.write_text(new_src, encoding="utf-8")

    # sanity: reload-able
    embedded = new_src.split(MARKER_START, 1)[1].split('"""', 1)[0].strip()
    parsed = [json.loads(ln) for ln in embedded.splitlines()]
    assert len(parsed) == len(lines), (len(parsed), len(lines))
    print(f"packed {len(parsed)} cases into {KERNEL.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
