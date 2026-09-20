"""Configuration loading.

Reads configs/policy.toml with stdlib `tomllib` (Python 3.11+). No YAML, no
third-party parsers — see policy.toml for the rationale.
"""

from __future__ import annotations

import csv
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def find_repo_root(start: Path | None = None) -> Path:
    """Walk up from this file (or `start`) until configs/policy.toml is found."""
    here = (start or Path(__file__)).resolve()
    for candidate in [here, *here.parents]:
        if (candidate / "configs" / "policy.toml").is_file():
            return candidate
    raise FileNotFoundError("could not locate repo root (configs/policy.toml not found)")


@dataclass
class Config:
    root: Path
    data: dict[str, Any] = field(default_factory=dict)

    # ---- section accessors -------------------------------------------------
    def section(self, name: str) -> dict[str, Any]:
        value = self.data.get(name, {})
        if not isinstance(value, dict):
            raise TypeError(f"config section [{name}] is not a table")
        return value

    def get(self, section: str, key: str, default: Any = None) -> Any:
        return self.section(section).get(key, default)

    def path(self, section: str, key: str) -> Path:
        raw = self.section(section)[key]
        p = Path(raw)
        return p if p.is_absolute() else (self.root / p)

    # ---- well-known paths --------------------------------------------------
    @property
    def parent_manifest(self) -> Path:
        raw = Path(self.section("paths")["parent_manifest"])
        return raw if raw.is_absolute() else (self.root / raw).resolve()

    @property
    def manifests_dir(self) -> Path:
        return self.path("paths", "manifests")

    @property
    def reports_dir(self) -> Path:
        return self.path("paths", "reports")

    def ensure_dirs(self) -> None:
        for name in ("manifests", "raw", "quarantine", "extracted", "normalized",
                     "deduplicated", "release", "reports", "cache"):
            self.path("paths", name).mkdir(parents=True, exist_ok=True)
        (self.root / "data" / "cache" / "tokenizers").mkdir(parents=True, exist_ok=True)

    # ---- helpers -----------------------------------------------------------
    def load_csv(self, relative: str) -> list[dict[str, str]]:
        p = self.root / relative
        if not p.is_file():
            raise FileNotFoundError(p)
        with p.open("r", encoding="utf-8", newline="") as fh:
            return [dict(row) for row in csv.DictReader(fh)]


def load_config(root: Path | None = None) -> Config:
    root = root or find_repo_root()
    with (root / "configs" / "policy.toml").open("rb") as fh:
        data = tomllib.load(fh)
    return Config(root=root, data=data)
