"""The deterministic licence gate.

RULES OF THIS MODULE
  1. No LLM ever makes a release decision. An LLM may help a human research a
     source, but the decision recorded here comes from explicit manifest fields
     and explicit ordered rules.
  2. Fail closed. Missing evidence produces UNKNOWN or WITH_CONDITIONS, never
     TRAINING_ALLOWED.
  3. Platform metadata is not proof. An uploader-applied CC0 tag on a work first
     published after the copyright term began is treated as an unverified claim.
  4. Determinism. Same inputs -> same decision, always. Every decision records
     the rule id, the fields it read, a human reason, a confidence, and any
     outstanding requirements.

The two axes that matter:
  state           -> may we release it, and may it update model weights?
  basis_strength  -> how good is the documentary basis for that decision?
                     (strong | moderate | weak)
`state` answers the release question; `basis_strength` plus `confidence` answer
the audit question. Both are written to the licence manifest.
"""

from __future__ import annotations

import csv
import datetime as _dt
import json
from pathlib import Path
from typing import Any, Callable, Iterable

from svk_corpus import CONFIDENCE_LEVELS
from svk_corpus.config import Config
from svk_corpus.schemas.records import (
    LICENSE_MANIFEST_FIELDS,
    GateDecision,
    GateState,
    SourceRecord,
)

# Licences that grant training and redistribution unconditionally.
PERMISSIVE_LICENSES = (
    "apache-2.0",
    "apache 2.0",
    "mit",
    "bsd-3-clause",
    "bsd-2-clause",
)

# Licence strings that mean "no licence granted".
NO_LICENSE_TOKENS = (
    "",
    "none",
    "none declared",
    "noassertion",
    "unknown",
    "n/a",
    "null",
)

BASIS_STRENGTHS = ("strong", "moderate", "weak", "none")

# India's copyright term: author's life + 60 years (Copyright Act 1957).
INDIA_TERM_YEARS = 60
# United States: works published before this year are in the public domain by
# publication date, regardless of the author's death year. (Cutoff advances
# annually; the value is pinned so that decisions are reproducible.)
US_PD_PUBLICATION_CUTOFF = 1929
# The boundary year exported from the research phase: a work first published in
# 1966 or later cannot be public domain under a life+60 term in 2026.
LIFE_PLUS_60_FLOOR_YEAR = 1966


# ---------------------------------------------------------------------------
# field helpers
# ---------------------------------------------------------------------------
def _norm_license(raw: str) -> str:
    return (raw or "").strip().lower()


def _as_int(raw: Any) -> int | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text or text.lower() in ("unknown", "none", "n/a", "null"):
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def _as_bool(raw: Any) -> bool:
    return str(raw).strip().lower() in ("true", "yes", "1", "y")


def _is_permissive(lic: str, uploader_asserted: bool) -> bool:
    """True only for licences that impose no NC / ND / ShareAlike obligation."""
    if _is_sharealike(lic) or _is_noncommercial(lic) or _is_nd(lic):
        return False
    if lic in PERMISSIVE_LICENSES:
        return True
    # CC0 is permissive only when the dedicator is plausibly a rights holder.
    if lic.startswith("cc0") and not uploader_asserted:
        return True
    if lic.startswith("cc-by-") or lic == "cc-by" or lic.startswith("cc-by 4"):
        return True
    if lic.startswith("creative commons attribution"):
        return True
    return False


def _is_sharealike(lic: str) -> bool:
    return "-sa" in lic or "sharealike" in lic


def _is_noncommercial(lic: str) -> bool:
    return "-nc" in lic or "noncommercial" in lic or "non-commercial" in lic


def _is_nd(lic: str) -> bool:
    return "-nd" in lic or "noderiv" in lic or "no-deriv" in lic


def basis_strength(source: SourceRecord, current_year: int) -> str:
    """How strong is the documentary basis for using this source?

    strong   : an explicit licence from a rights-holder channel, OR a documented
               author death year that has already run the life+60 term out.
    moderate : a US publication-date basis (pre-1930), OR a positive rights
               statement issued by the holding institution for that item.
    weak     : a date or licence claim that we cannot corroborate.
    none     : nothing to go on.
    """
    lic = _norm_license(source["license"])
    uploader_asserted = _as_bool(source.get("uploader_asserted"))
    death = _as_int(source.get("author_death_year"))
    year = _as_int(source.get("publication_year")) or _year_from_text(source["copyright_status"])
    ia_statement = _as_bool(source.get("ia_rights_statement"))

    if _is_sharealike(lic) or _is_noncommercial(lic):
        # Permitted for retrieval under conditions, never an unconditional grant.
        return "moderate" if _is_sharealike(lic) else "weak"
    if _is_permissive(lic, uploader_asserted):
        return "strong"
    if death is not None and death + INDIA_TERM_YEARS < current_year:
        return "strong"
    if lic.startswith("cc0") and uploader_asserted:
        # A third-party dedication is only as good as the underlying rights.
        if year is None:
            return "weak"
        if year >= LIFE_PLUS_60_FLOOR_YEAR:
            return "none"
        return "weak"
    if ia_statement:
        return "moderate"
    if year is not None and year <= US_PD_PUBLICATION_CUTOFF:
        return "moderate"
    if year is not None and year < LIFE_PLUS_60_FLOOR_YEAR:
        return "weak"
    if year is not None and year >= LIFE_PLUS_60_FLOOR_YEAR and lic in NO_LICENSE_TOKENS:
        return "none"
    return "none"


def _year_from_text(text: str) -> int | None:
    """Read a 4-digit year out of a free-text status field (e.g. '1923; pre-1966').

    Only used as a fallback when `publication_year` is empty. It never invents a
    value: if no 4-digit year is present, it returns None.
    """
    if not text:
        return None
    for token in text.replace(";", " ").replace(",", " ").split():
        token = token.strip("().")
        if len(token) == 4 and token.isdigit():
            year = int(token)
            if 1500 <= year <= 2100:
                return year
    return None


# ---------------------------------------------------------------------------
# rules
# ---------------------------------------------------------------------------
GateRule = Callable[[SourceRecord, dict[str, Any], int], GateDecision | None]


def _make(source: SourceRecord, state: GateState, rule_id: str, reason: str,
          evidence: dict[str, Any], confidence: str = "low",
          requirements: Iterable[str] = (), requirements_met: bool = False,
          noncommercial: bool = False, sharealike: bool = False,
          verification_required: bool = False, now: str = "") -> GateDecision:
    return GateDecision(
        source_id=source.source_id,
        state=state,
        rule_id=rule_id,
        reason=reason,
        evidence=evidence,
        confidence=confidence,
        requirements=list(requirements),
        requirements_met=requirements_met,
        noncommercial=noncommercial,
        sharealike=sharealike,
        verification_required=verification_required,
        evaluated_at=now,
    )


def rule_r10_noderivatives(source, ctx, now):
    lic = _norm_license(source["license"])
    if _is_nd(lic):
        return _make(source, GateState.NOT_ALLOWED, "R10_NODERIVATIVES",
                     "The licence forbids derivative works, and every stage of this pipeline "
                     "(normalisation, segmentation, OCR correction, tokenisation) creates a "
                     "derivative.",
                     {"license": source["license"]}, "high", now=now)
    return None


def rule_r20_permissive_licence(source, ctx, now):
    lic = _norm_license(source["license"])
    uploader_asserted = _as_bool(source.get("uploader_asserted"))
    if not _is_permissive(lic, uploader_asserted):
        return None
    confidence = source.get("license_confidence") or "medium"
    if confidence == "low":
        return _make(source, GateState.WITH_CONDITIONS, "R20_PERMISSIVE_LICENCE_UNVERIFIED",
                     "The licence is permissive but our own confidence in the licence record is "
                     "low, so it must be verified before release.",
                     {"license": source["license"], "license_confidence": confidence},
                     "low",
                     requirements=["verify the licence against the primary source, then record "
                                   "license_confidence = medium or high"],
                     requirements_met=False, now=now)
    return _make(source, GateState.TRAINING_ALLOWED, "R20_PERMISSIVE_LICENCE",
                 "An explicit permissive licence was declared for this source.",
                 {"license": source["license"], "license_confidence": confidence},
                 confidence, now=now)


def rule_r25_life_plus_60_expired(source, ctx, now):
    death = _as_int(source.get("author_death_year"))
    if death is None:
        return None
    if death + INDIA_TERM_YEARS < now:
        return _make(source, GateState.TRAINING_ALLOWED, "R25_LIFE_PLUS_60_EXPIRED",
                     f"The author's death year is documented ({death}) and the Indian life+60 "
                     f"term has expired ({death + INDIA_TERM_YEARS} < {now}).",
                     {"author_death_year": death, "term_expired": death + INDIA_TERM_YEARS},
                     "high", now=now)
    return None


def rule_r30_cc0_uploader_asserted(source, ctx, now):
    lic = _norm_license(source["license"])
    uploader_asserted = _as_bool(source.get("uploader_asserted"))
    if not (lic.startswith("cc0") and uploader_asserted):
        return None
    year = _as_int(source.get("publication_year"))
    death = _as_int(source.get("author_death_year"))
    evidence = {"license": source["license"], "uploader_asserted": True,
                "publication_year": year, "author_death_year": death}
    if year is not None and year >= LIFE_PLUS_60_FLOOR_YEAR:
        return _make(source, GateState.NEEDS_PERMISSION, "R30_CC0_ASSERTED_TOO_RECENT",
                     f"A CC0 tag was applied by a third-party uploader to a work first published "
                     f"in {year}. A work published in {LIFE_PLUS_60_FLOOR_YEAR} or later cannot "
                     f"be public domain under the Indian life+60 term, so the dedication is not "
                     f"credible as a rights-holder grant.",
                     evidence, "high", now=now)
    if year is None:
        return _make(source, GateState.UNKNOWN, "R30_CC0_ASSERTED_UNDATED",
                     "A third-party CC0 tag is present but the publication year is not documented, "
                     "so the credibility of the dedication cannot be assessed.",
                     evidence, "low", now=now)
    if death is not None:
        # A documented death year makes the CC0 tag irrelevant either way: the
        # term rules decide (R25 if expired, R92 if not). Staying here would let
        # an unverified uploader tag shadow a documented chronological fact.
        return None
    return _make(source, GateState.WITH_CONDITIONS, "R30_CC0_ASSERTED_PRE_1966",
                 f"A third-party CC0 tag was applied to a work published in {year}. That is "
                 f"consistent with public-domain status, but the author's death year is not "
                 f"documented, so the basis is unverified.",
                 evidence, "low",
                 requirements=["document the author's death year, or obtain a dated statement "
                               "from the rights holder for the CC0 dedication"],
                 requirements_met=False, verification_required=True, now=now)


def rule_r40_sharealike(source, ctx, now):
    lic = _norm_license(source["license"])
    if not _is_sharealike(lic):
        return None
    return _make(source, GateState.RAG_ALLOWED, "R40_SHAREALIKE",
                 "ShareAlike material may be redistributed with attribution, but its ShareAlike "
                 "condition would propagate to a derived training set, so it is admitted to "
                 "retrieval only and never to the training corpus.",
                 {"license": source["license"]}, "high",
                 sharealike=True, verification_required=False, now=now)


def rule_r50_noncommercial(source, ctx, now):
    lic = _norm_license(source["license"])
    if not _is_noncommercial(lic):
        return None
    include = bool(ctx.get("include_noncommercial_in_rag", False))
    if not include:
        return _make(source, GateState.NEEDS_PERMISSION, "R50_NONCOMMERCIAL_EXCLUDED",
                     "The licence is non-commercial and this release does not carry a "
                     "non-commercial lane, so the source is excluded rather than mislabelled.",
                     {"license": source["license"],
                      "include_noncommercial_in_rag": include}, "high", now=now)
    return _make(source, GateState.RAG_ALLOWED, "R50_NONCOMMERCIAL_RAG_LANE",
                 "Non-commercial material admitted to a clearly labelled non-commercial "
                 "retrieval lane only.",
                 {"license": source["license"]}, "medium",
                 noncommercial=True, now=now)


def rule_r60_holding_institution_statement(source, ctx, now):
    if not _as_bool(source.get("ia_rights_statement")):
        return None
    lic = _norm_license(source["license"])
    if lic not in NO_LICENSE_TOKENS and not lic.startswith(("public domain", "pd")):
        return None
    year = _as_int(source.get("publication_year"))
    return _make(source, GateState.TRAINING_ALLOWED, "R60_INSTITUTION_RIGHTS_STATEMENT",
                 "The holding institution states that the item is not in copyright. This is a "
                 "positive rights statement about the item, but it is not a licence, so the "
                 "residual Indian life+60 term is recorded as unverified.",
                 {"ia_rights_statement": True, "publication_year": year,
                  "license": source["license"]}, "medium",
                 verification_required=True, now=now)


def rule_r70_pre_1930_publication(source, ctx, now):
    year = _as_int(source.get("publication_year"))
    if year is None or year > US_PD_PUBLICATION_CUTOFF:
        return None
    lic = _norm_license(source["license"])
    if lic.startswith(("cc0", "cc-by-nc", "cc-by-nd")):
        return None
    return _make(source, GateState.TRAINING_ALLOWED, "R70_PRE_1930_PUBLICATION",
                 f"Published in {year}. A work published in {US_PD_PUBLICATION_CUTOFF} or "
                 f"earlier is in the public domain by publication date, independent of the "
                 f"author's death year. The Indian life+60 term has not been separately verified.",
                 {"publication_year": year,
                  "cutoff": US_PD_PUBLICATION_CUTOFF}, "medium",
                 verification_required=True, now=now)


def rule_r90_modern_in_copyright(source, ctx, now):
    year = _as_int(source.get("publication_year"))
    lic = _norm_license(source["license"])
    if year is None or year < LIFE_PLUS_60_FLOOR_YEAR:
        return None
    if lic not in NO_LICENSE_TOKENS and not lic.startswith("public domain"):
        return None
    return _make(source, GateState.NEEDS_PERMISSION, "R90_MODERN_IN_COPYRIGHT",
                 f"First published in {year} and no licence or rights statement is recorded. "
                 f"The work is in copyright and permission from the rights holder would be "
                 f"required.",
                 {"publication_year": year, "license": source["license"]}, "high", now=now)


def rule_r92_living_author_in_copyright(source, ctx, now):
    """Chronology RESOLVED against PD: known facts prove the term unexpired.

    R95 covers the ambiguous case (publication 1930-1965, death year unknown).
    This rule covers the case where the facts ARE known and they settle the
    question: publication inside the floor window and death+60 not yet reached
    means the work is in copyright today. That is a determination, not a gap,
    so it must not fall through to R99 UNKNOWN (fail-closed must still be
    correct-closed when the evidence is actually sufficient).
    """
    year = _as_int(source.get("publication_year"))
    death = _as_int(source.get("author_death_year"))
    # Only the ambiguous window 1930..1965 reaches here: >=1966 is R90's
    # territory (in copyright by modernity) and <=1929 is R70's (PD by
    # publication). Both of those rules run earlier in the chain, but the
    # guard keeps R92 honest if the chain is ever reordered.
    if year is None or year <= US_PD_PUBLICATION_CUTOFF:
        return None
    if death is None:
        return None
    if death + INDIA_TERM_YEARS < now:
        return None  # R25 already handled the expired-term case.
    return _make(source, GateState.NEEDS_PERMISSION, "R92_TERM_UNEXPIRED",
                 f"Published in {year} and the author's death year is documented ({death}); "
                 f"the Indian life+60 term runs to {death + INDIA_TERM_YEARS}, so the work "
                 f"is in copyright and permission from the rights holder is required.",
                 {"publication_year": year, "author_death_year": death,
                  "term_expires": death + INDIA_TERM_YEARS}, "high",
                 verification_required=False, now=now)


def rule_r95_chronology_unresolved(source, ctx, now):
    year = _as_int(source.get("publication_year"))
    death = _as_int(source.get("author_death_year"))
    if year is None or year >= LIFE_PLUS_60_FLOOR_YEAR:
        return None
    if death is not None:
        return None
    return _make(source, GateState.WITH_CONDITIONS, "R95_CHRONOLOGY_UNRESOLVED",
                 f"Published in {year}, which is inside the window where public-domain status "
                 f"turns on the author's death year, and no death year is documented.",
                 {"publication_year": year, "author_death_year": None}, "low",
                 requirements=["document the author's or translator's death year",
                               "or obtain a rights-holder statement"],
                 requirements_met=False, verification_required=True, now=now)


# Task 29: the JainQQ / Jain eLibrary pages carry the holder's own stamp on
# every page: 'JAIN EDUCATION INTERNATIONAL FOR SMALL AND PERSONAL USE ONLY'.
# A restrictive terms statement is EVIDENCE, not the absence of evidence:
# whatever the publication date, anything beyond private reading —
# redistribution, ML training — requires explicit permission. R99 would
# mislabel that situation as 'no evidence'; this rule records the truth.
_RESTRICTIVE_TERM_SIGNATURES = ("private and personal use", "personal use only")


def rule_r93_restrictive_terms(source, ctx, now):
    lic = _norm_license(source["license"])
    if not any(sig in lic for sig in _RESTRICTIVE_TERM_SIGNATURES):
        return None
    year = _as_int(source.get("publication_year"))
    detail = (f" First published {year}." if year else
              " Publication date not evidenced; the terms restriction alone is decisive.")
    return _make(source, GateState.NEEDS_PERMISSION, "R93_RESTRICTIVE_TERMS",
                 "The holder's stated terms restrict use to 'Private and Personal Use "
                 "Only', so redistribution and machine-learning training require "
                 "explicit permission." + detail,
                 {"license": source["license"], "publication_year": year},
                 "high", now=now)


def rule_r99_insufficient_evidence(source, ctx, now):
    return _make(source, GateState.UNKNOWN, "R99_INSUFFICIENT_EVIDENCE",
                 "No licence, no rights statement and no usable publication date are recorded, "
                 "so no permission decision can be made.",
                 {"license": source["license"],
                  "publication_year": source.get("publication_year"),
                  "ia_rights_statement": source.get("ia_rights_statement")},
                 "low", now=now)


GATE_RULES: tuple[tuple[str, GateRule], ...] = (
    ("R10_NODERIVATIVES", rule_r10_noderivatives),
    # ShareAlike / NonCommercial / NoDerivatives obligations are checked BEFORE
    # the permissive-licence rule, so that a CC-BY-SA work can never be read as
    # an unconditional grant.
    ("R40_SHAREALIKE", rule_r40_sharealike),
    ("R50_NONCOMMERCIAL", rule_r50_noncommercial),
    ("R20_PERMISSIVE_LICENCE", rule_r20_permissive_licence),
    ("R25_LIFE_PLUS_60_EXPIRED", rule_r25_life_plus_60_expired),
    ("R30_CC0_ASSERTED", rule_r30_cc0_uploader_asserted),
    ("R60_INSTITUTION_RIGHTS_STATEMENT", rule_r60_holding_institution_statement),
    ("R70_PRE_1930_PUBLICATION", rule_r70_pre_1930_publication),
    ("R90_MODERN_IN_COPYRIGHT", rule_r90_modern_in_copyright),
    ("R92_TERM_UNEXPIRED", rule_r92_living_author_in_copyright),
    ("R95_CHRONOLOGY_UNRESOLVED", rule_r95_chronology_unresolved),
    ("R93_RESTRICTIVE_TERMS", rule_r93_restrictive_terms),
    ("R99_INSUFFICIENT_EVIDENCE", rule_r99_insufficient_evidence),
)


# ---------------------------------------------------------------------------
# public API
# ---------------------------------------------------------------------------
def license_gate(source: SourceRecord, ctx: dict[str, Any] | None = None,
                 current_year: int | None = None,
                 now: str | None = None) -> GateDecision:
    """Evaluate one source. First matching rule wins; the rule set is total."""
    ctx = dict(ctx or {})
    year_now = current_year or _dt.date.today().year
    stamp = now or _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()
    for rule_id, rule in GATE_RULES:
        decision = rule(source, ctx, year_now)
        if decision is not None:
            decision.evaluated_at = stamp
            decision.confidence = (
                decision.confidence if decision.confidence in CONFIDENCE_LEVELS else "low"
            )
            return decision
    raise AssertionError("gate rule set is not total (R99 must always match)")


def evaluate_all_sources(sources: Iterable[SourceRecord],
                         config: Config) -> list[GateDecision]:
    ctx = {
        "include_noncommercial_in_rag": bool(
            config.get("release", "include_noncommercial_in_rag", False)
        ),
    }
    return [license_gate(s, ctx) for s in sources]


def write_license_manifest(decisions: Iterable[GateDecision], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [d.to_row() for d in decisions]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(LICENSE_MANIFEST_FIELDS),
                                quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows)
    return path


def load_license_manifest(path: Path) -> dict[str, dict[str, str]]:
    if not path.is_file():
        return {}
    with path.open("r", encoding="utf-8", newline="") as fh:
        return {row["source_id"]: row for row in csv.DictReader(fh)}
