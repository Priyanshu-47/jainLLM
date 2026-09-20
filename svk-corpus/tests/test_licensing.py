"""Licensing gate tests.

The gate is the component that must never err toward inclusion. Every rule here
is a documented decision from the research phase: platform metadata is not
proof, chronology can create PD status, and missing evidence means exclusion.
"""

from __future__ import annotations

import unittest

from svk_corpus.schemas.records import GateState, SourceRecord
from svk_corpus.licensing.gate import license_gate


def _source(**overrides) -> SourceRecord:
    base = {
        "source_id": "TEST-0001",
        "title": "Test source",
        "license": "",
        "publication_year": "",
        "author_death_year": "",
        "uploader_asserted": "",
        "ia_rights_statement": "",
        "license_confidence": "",
    }
    base.update(overrides)
    return SourceRecord(values=base)


class TestExcludedStates(unittest.TestCase):
    """UNKNOWN / NOT_ALLOWED / NEEDS_PERMISSION must all exclude."""

    def test_unknown_no_evidence_is_excluded(self):
        d = license_gate(_source(license=""))
        self.assertIs(d.state, GateState.UNKNOWN)
        self.assertEqual(d.rule_id, "R99_INSUFFICIENT_EVIDENCE")
        self.assertFalse(d.releasable)

    def test_unlicensed_modern_work_needs_permission(self):
        d = license_gate(_source(license="NOASSERTION", publication_year="1985"))
        self.assertIs(d.state, GateState.NEEDS_PERMISSION)
        self.assertEqual(d.rule_id, "R90_MODERN_IN_COPYRIGHT")
        self.assertFalse(d.releasable)

    def test_uploader_asserted_cc0_on_modern_work_needs_permission(self):
        # The SVK-1010 pattern: platform CC0 tag on a 1990 publication.
        d = license_gate(_source(license="cc0", publication_year="1990",
                                 uploader_asserted="true"))
        self.assertIs(d.state, GateState.NEEDS_PERMISSION)
        self.assertEqual(d.rule_id, "R30_CC0_ASSERTED_TOO_RECENT")
        self.assertFalse(d.releasable)

    def test_undated_uploader_cc0_is_unknown(self):
        d = license_gate(_source(license="cc0", uploader_asserted="true"))
        self.assertIs(d.state, GateState.UNKNOWN)
        self.assertFalse(d.releasable)

    def test_nd_licence_is_not_allowed(self):
        d = license_gate(_source(license="CC-BY-ND-4.0"))
        self.assertIs(d.state, GateState.NOT_ALLOWED)
        self.assertEqual(d.rule_id, "R10_NODERIVATIVES")
        self.assertFalse(d.releasable)

    def test_sharealike_never_reaches_training(self):
        d = license_gate(_source(license="CC-BY-SA-4.0", license_confidence="high"))
        self.assertIs(d.state, GateState.RAG_ALLOWED)
        self.assertTrue(d.sharealike)
        self.assertTrue(d.releasable)  # RAG corpus: yes
        # Training corpus: no. ShareAlike would propagate to derived weights.
        self.assertNotEqual(d.state, GateState.TRAINING_ALLOWED)

    def test_noncommercial_excluded_without_nc_lane(self):
        d = license_gate(_source(license="CC-BY-NC-4.0"))
        self.assertIs(d.state, GateState.NEEDS_PERMISSION)
        self.assertFalse(d.releasable)

    def test_noncommercial_rag_lane_when_enabled(self):
        d = license_gate(_source(license="CC-BY-NC-4.0"),
                         ctx={"include_noncommercial_in_rag": True})
        self.assertIs(d.state, GateState.RAG_ALLOWED)
        self.assertTrue(d.noncommercial)


class TestIncludedStates(unittest.TestCase):
    def test_permissive_licence_allows_training(self):
        d = license_gate(_source(license="Apache-2.0", license_confidence="high"))
        self.assertIs(d.state, GateState.TRAINING_ALLOWED)
        self.assertEqual(d.rule_id, "R20_PERMISSIVE_LICENCE")
        self.assertTrue(d.releasable)

    def test_permissive_low_confidence_becomes_conditions(self):
        d = license_gate(_source(license="Apache-2.0", license_confidence="low"))
        self.assertIs(d.state, GateState.WITH_CONDITIONS)
        self.assertFalse(d.releasable)  # until requirements_met
        self.assertTrue(d.requirements)

    def test_pre1930_publication_is_training_allowed(self):
        d = license_gate(_source(license="NOASSERTION", publication_year="1923"))
        self.assertIs(d.state, GateState.TRAINING_ALLOWED, d.reason)
        self.assertEqual(d.rule_id, "R70_PRE_1930_PUBLICATION")
        # The Indian life+60 term is not separately verified for this basis.
        self.assertTrue(d.verification_required)

    def test_pre1966_cc0_asserted_needs_death_year(self):
        d = license_gate(_source(license="cc0", publication_year="1923",
                                 uploader_asserted="true"))
        self.assertIs(d.state, GateState.WITH_CONDITIONS)
        self.assertFalse(d.releasable)
        self.assertIn("death year", d.requirements[0])

    def test_author_death_plus_60_expired_allows_training(self):
        d = license_gate(_source(license="NOASSERTION", author_death_year="1940"))
        self.assertIs(d.state, GateState.TRAINING_ALLOWED)
        self.assertEqual(d.rule_id, "R25_LIFE_PLUS_60_EXPIRED")
        self.assertTrue(d.releasable)

    def test_institution_rights_statement_takes_precedence(self):
        # R60 precedes R70 in GATE_RULES: a positive institutional rights
        # statement is stronger evidence than publication-date inference alone.
        d = license_gate(_source(license="NOASSERTION", ia_rights_statement="true",
                                 publication_year="1923"))
        self.assertEqual(d.rule_id, "R60_INSTITUTION_RIGHTS_STATEMENT")
        self.assertIs(d.state, GateState.TRAINING_ALLOWED)

    def test_pre1966_with_death_year_inside_term_needs_permission(self):
        # 1940 publication, author died 1970: 1970+60=2030 >= now, so R25 does
        # not fire; publication is after the 1929 US cutoff, so R70 does not
        # fire. Because the death year IS documented, the chronology is RESOLVED
        # against public domain: R92 determines in-copyright, not R95-unknown.
        d = license_gate(_source(license="", publication_year="1940",
                                 author_death_year="1970"))
        self.assertIs(d.state, GateState.NEEDS_PERMISSION)
        self.assertEqual(d.rule_id, "R92_TERM_UNEXPIRED")

    def test_pre1966_without_death_year_stays_conditions(self):
        # The genuinely ambiguous case: same window, no death year documented.
        d = license_gate(_source(license="", publication_year="1940"))
        self.assertIs(d.state, GateState.WITH_CONDITIONS)
        self.assertEqual(d.rule_id, "R95_CHRONOLOGY_UNRESOLVED")

    def test_gate_is_deterministic(self):
        # Determinism contract: same INPUTS -> same decision. `now` is an input,
        # so two calls with the same stamp must produce identical rows.
        s = _source(license="Apache-2.0", license_confidence="high")
        d1 = license_gate(s, now="2026-01-01T00:00:00+00:00")
        s2 = _source(license="Apache-2.0", license_confidence="high")
        d2 = license_gate(s2, now="2026-01-01T00:00:00+00:00")
        self.assertEqual(d1.to_row(), d2.to_row())


if __name__ == "__main__":
    unittest.main()
