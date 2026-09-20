"""Admission policy: what may enter which released corpus.

The licence gate answers "may we use this at all". This module answers the
separate question "may it enter this particular release product", which is where
the provenance bar lives.

THREE GATES, NOT ONE
    gate state        -- legal permission          (licensing/gate.py)
    threshold checks  -- evidential quality        (this module)
    product routing   -- training vs retrieval vs neither

WHAT 'PROVENANCE QUALITY' MEASURES HERE, AND WHAT IT MUST NOT MEASURE
A first revision of this module gated the release on a hand-curated
`provenance_quality` column and on the manifest's `license_confidence`. Run over
the real corpus, that revision excluded every pre-1930 Internet Archive item
admitted by the date rule (R70) and every item whose licensing basis is a
publication date rather than a licence — including the only Sthānakavāsī-published
text in the whole candidate set.

That was a category error worth recording, because it is an easy one to repeat:
both columns describe *how thin the rights record is*, which is precisely what the
gate already decides through R70's `verification_required` flag. Using a
provenance field to re-litigate a rights decision means the pipeline quietly
becomes stricter than its own documented ruleset, and it does so in a way that
looks like rigour while actually being unreviewable.

So this revision separates the two questions cleanly:

  * RIGHTS  -> the gate's decision and the gate's own confidence, which is the
    confidence attached to the legal basis actually being relied on. A date-based
    public-domain conclusion is a medium-confidence basis and is admitted as such.
  * PROVENANCE -> can we identify this artifact, re-fetch it, and prove what we
    distributed? This is COMPUTED from the artifact record (repository +
    identifier + url + sha256 + timestamp + licence evidence url) rather than
    hand-asserted, and it is the same test `quality.provenance_completeness`
    applies to release records. A source with a full artifact trail passes even if
    its rights metadata is thin, because rights are not what this bar is for.

Anything admitted while the gate still demands human verification is not silently
trusted: it carries `verification_outstanding: true` on its admission decision and
is listed in a dedicated section of the ingest report, so the outstanding licence
checks are a work item rather than an invisible property.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from svk_corpus.schemas.records import GateState, SourceRecord

CORPUS_TRAINING = "training"
CORPUS_RAG = "rag"

# Reason codes, so the report can be grouped and audited.
R_GATE = "P10_GATE_STATE"
R_CONFIDENCE = "P20_GATE_CONFIDENCE"
R_PROVENANCE = "P30_ARTIFACT_PROVENANCE"
R_NOT_ACQUIRED = "P40_NOT_ACQUIRED"
R_SHAREALIKE = "P50_SHAREALIKE_TRAINING_BLOCK"
R_CONTRADICTION = "P60_CONTRADICTS_RESEARCH_PHASE"
R_ADMITTED = "P00_ADMITTED"

# Not an exclusion: an outstanding work item, surfaced in the report.
F_VERIFICATION = "P70_VERIFICATION_OUTSTANDING"

_LADDER = {"none": 0, "low": 1, "medium": 2, "high": 3, "unverified": 0, "": 0}


def _rank(value: str) -> int:
    return _LADDER.get((value or "").strip().lower(), 0)


def sync_training_permission(sources: list[Any], decisions: list[Any]) -> None:
    """Mirror each gate decision into the manifest's `training_permission` column.

    That column began life as research-phase free text and could contradict the
    licence manifest (SVK-0002 carried TRAINING_ALLOWED_WITH_CONDITIONS while
    the gate said NEEDS_PERMISSION). The gate is authoritative for what we may
    DO with a source, so this sync makes the manifest echo the decision plus
    the rule that produced it. Run as part of `cmd_gate`.
    """
    by_id = {d.source_id: d for d in decisions}
    for source in sources:
        decision = by_id.get(source.source_id)
        if decision is None:
            continue
        source.values["training_permission"] = (
            f"{decision.state.value} ({decision.rule_id})")


@dataclass
class AdmissionDecision:
    source_id: str
    corpora: set[str] = field(default_factory=set)
    excluded: bool = True
    reasons: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    checks: dict[str, Any] = field(default_factory=dict)
    verification_outstanding: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "corpora": sorted(self.corpora),
            "admitted": bool(self.corpora),
            "reasons": self.reasons,
            "flags": self.flags,
            "checks": self.checks,
            "verification_outstanding": self.verification_outstanding,
        }


# ---------------------------------------------------------------------------
# computed artifact provenance
# ---------------------------------------------------------------------------
PROVENANCE_COMPONENTS = (
    "repository",          # which repository the artifact came from
    "identifier",          # the item id inside that repository
    "source_url",          # a resolvable landing page
    "artifact_sha256",     # the hash of the artifact we hold
    "download_timestamp",  # when we fetched it
    "license_evidence_url",# where the rights basis is documented
)


def provenance_quality(source: SourceRecord,
                       artifact: dict[str, str] | None) -> tuple[str, dict[str, Any]]:
    """Grade the artifact trail, not the rights record. Returns (grade, detail).

    high   : hash + repository + identifier + url + timestamp present
    medium : at least four of the six components present
    low    : fewer than four
    """
    detail: dict[str, Any] = {}
    present = 0
    for component in PROVENANCE_COMPONENTS:
        if component == "repository":
            value = source.get("repository") or source.get("acquisition_repository")
        elif component == "identifier":
            value = source.get("acquisition_identifier")
        elif component == "license_evidence_url":
            value = source.get("license_evidence_url") or source.get("source_url")
        elif component in ("source_url",):
            value = source.get("source_url")
        else:
            value = (artifact or {}).get(component, "")
        ok = bool(str(value or "").strip())
        detail[component] = ok
        present += 1 if ok else 0

    has_hash = bool(str((artifact or {}).get("artifact_sha256") or
                        (artifact or {}).get("sha256") or "").strip())
    detail["components_present"] = present
    detail["components_total"] = len(PROVENANCE_COMPONENTS)

    if present >= 5 and has_hash:
        grade = "high"
    elif present >= 4:
        grade = "medium"
    else:
        grade = "low"
    detail["grade"] = grade
    return grade, detail


def route_by_gate(state: GateState) -> set[str]:
    if state is GateState.TRAINING_ALLOWED:
        return {CORPUS_TRAINING, CORPUS_RAG}
    if state is GateState.RAG_ALLOWED:
        return {CORPUS_RAG}
    if state is GateState.WITH_CONDITIONS:
        return set()   # conditions unmet by definition when requirements_met is false
    return set()


def admit(source: SourceRecord, gate, config, *, acquired: bool,
          artifact: dict[str, str] | None = None) -> AdmissionDecision:
    """Decide product routing for one source. Deterministic; no LLM involved."""
    decision = AdmissionDecision(source_id=source.source_id)
    corpora = route_by_gate(gate.state)
    prov_grade, prov_detail = provenance_quality(source, artifact)

    checks: dict[str, Any] = {
        "gate_state": gate.state.value,
        "gate_rule": gate.rule_id,
        "gate_confidence": gate.confidence,
        "computed_provenance": prov_detail,
        "curated_provenance_quality": source.get("provenance_quality", ""),
        "license_confidence": source.get("license_confidence", ""),
        "source_quality": source.get("source_quality", ""),
        "acquired": acquired,
        "research_phase_use": source.get("recommended_use", ""),
    }
    decision.checks = checks

    if not corpora:
        decision.reasons.append(
            f"{R_GATE}: gate state {gate.state.value} permits no release product"
        )
        return decision

    if gate.state is GateState.WITH_CONDITIONS and not gate.requirements_met:
        decision.reasons.append(f"{R_GATE}: conditions not satisfied")
        return decision

    # The confidence that counts is the one attached to the legal basis actually
    # being relied on, which the gate records. A pre-1930 publication-date basis is
    # a medium-confidence basis; a permissive licence is a high-confidence one.
    min_conf = str(config.get("release", "min_license_confidence", "medium"))
    basis_confidence = gate.confidence or source.get("license_confidence", "")
    if _rank(basis_confidence) < _rank(min_conf):
        decision.reasons.append(
            f"{R_CONFIDENCE}: the confidence in the legal basis being relied on "
            f"({gate.rule_id}) is '{basis_confidence}', below the release minimum "
            f"'{min_conf}'"
        )
        return decision

    min_prov = str(config.get("release", "min_provenance_quality_for_release", "medium"))
    if _rank(prov_grade) < _rank(min_prov):
        decision.reasons.append(
            f"{R_PROVENANCE}: only {prov_detail['components_present']}/"
            f"{prov_detail['components_total']} artifact provenance components are "
            f"present (grade '{prov_grade}'), below the release minimum '{min_prov}'"
        )
        return decision

    if not acquired:
        decision.reasons.append(
            f"{R_NOT_ACQUIRED}: passed the gate but no artifact was acquired in "
            f"this milestone (reported explicitly so that 'absent' is not read as "
            f"'rejected')"
        )
        return decision

    # ShareAlike may never enter the training product.
    if gate.sharealike:
        corpora.discard(CORPUS_TRAINING)
        if not corpora:
            decision.reasons.append(f"{R_SHAREALIKE}: no permitted product remains")
            return decision

    # Contradiction with the research phase is REPORTED, never silently resolved.
    research_use = (source.get("recommended_use") or "").strip().upper()
    if research_use in ("NEEDS_PERMISSION", "DO_NOT_USE", "UNKNOWN") and \
            gate.state is GateState.TRAINING_ALLOWED:
        decision.flags.append(
            f"{R_CONTRADICTION}: the research-phase manifest recommended "
            f"'{research_use}' while the licence gate admits it as "
            f"'{gate.state.value}' via {gate.rule_id}. Both records are kept; a "
            f"human licence review is outstanding."
        )

    # An admitted source whose basis still needs a human check is not excluded;
    # it is labelled, and the report lists it as an open licence work item.
    if gate.verification_required or \
            str(source.get("verification_required", "")).strip().lower() == "true":
        decision.verification_outstanding = True
        decision.flags.append(
            f"{F_VERIFICATION}: admitted via {gate.rule_id} subject to a documented "
            f"human licence check (gate confidence '{gate.confidence}'). The text is "
            f"released with this flag recorded per record, not silently trusted."
        )

    decision.corpora = corpora
    decision.excluded = False
    decision.reasons.append(
        f"{R_ADMITTED}: {gate.rule_id} (confidence {gate.confidence}, provenance "
        f"{prov_grade}) -> {sorted(corpora)}"
    )
    return decision


def admit_all(sources, gates: dict[str, Any], config, *,
              acquired_ids: set[str],
              artifact_index: dict[str, dict[str, str]] | None = None) \
        -> list[AdmissionDecision]:
    artifact_index = artifact_index or {}
    out = []
    for source in sources:
        gate = gates.get(source.source_id)
        if gate is None:
            decision = AdmissionDecision(source_id=source.source_id)
            decision.reasons.append(f"{R_GATE}: no gate decision recorded")
            out.append(decision)
            continue
        out.append(admit(source, gate, config,
                         acquired=source.source_id in acquired_ids,
                         artifact=artifact_index.get(source.source_id)))
    return out
