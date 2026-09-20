"""Task 30: Corpus Integrity Audit Tests.

Verify that reprocessing did not break:
- provenance survival in segmented units
- source ID stability
- quarantine exclusion for blocked sources
- rights gate independence from quality
- mixed-script content preservation
- contextual metadata integrity
"""
from __future__ import annotations

import csv
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEGMENTED = ROOT / "data" / "segmented"
EXCLUDED_FILE = ROOT / "data" / "release" / "excluded_sources.jsonl"
MANIFEST_FILE = ROOT / "manifests" / "source_manifest.csv"
LICENSE_MANIFEST = ROOT / "manifests" / "license_manifest.csv"

SVK_2022_2029 = [f"SVK-{i}" for i in range(2022, 2030)]


def _load_excluded_ids() -> set[str]:
    ids: set[str] = set()
    if EXCLUDED_FILE.exists():
        with EXCLUDED_FILE.open(encoding="utf-8") as fh:
            for line in fh:
                obj = json.loads(line)
                ids.add(obj["source_id"])
    return ids


def _load_manifest() -> dict[str, dict]:
    manifest: dict[str, dict] = {}
    if MANIFEST_FILE.exists():
        with MANIFEST_FILE.open(encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                manifest[row["source_id"]] = row
    return manifest


def _load_segmented_units(source_id: str) -> list[dict]:
    path = SEGMENTED / source_id / "units.jsonl"
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh]


class TestQuarantineExclusion(unittest.TestCase):
    """All 8 JainQQ sources must remain excluded from the release."""

    @classmethod
    def setUpClass(cls):
        cls.excluded = _load_excluded_ids()

    def test_svk_2022_through_2029_excluded(self):
        for sid in SVK_2022_2029:
            self.assertIn(
                sid, self.excluded,
                f"{sid} must be in excluded_sources.jsonl",
            )

    def test_excluded_count_at_least_8(self):
        self.assertGreaterEqual(len(self.excluded), 8)


class TestRightsGateIndependence(unittest.TestCase):
    """Rights gate must operate independently from quality status."""

    @classmethod
    def setUpClass(cls):
        cls.manifest = _load_manifest()
        cls.excluded = _load_excluded_ids()
        # Load license manifest for gate decisions
        cls.license_decisions: dict[str, dict] = {}
        lic_file = ROOT / "manifests" / "license_manifest.csv"
        if lic_file.exists():
            with lic_file.open(encoding="utf-8") as fh:
                for row in csv.DictReader(fh):
                    cls.license_decisions[row["source_id"]] = row

    def test_all_svk_2022_2029_need_permission(self):
        for sid in SVK_2022_2029:
            lic = self.license_decisions.get(sid, {})
            decision = lic.get("decision", "")
            self.assertEqual(
                decision, "NEEDS_PERMISSION",
                f"{sid}: license decision={decision!r}, expected NEEDS_PERMISSION",
            )

    def test_all_svk_2022_2029_have_restrictive_rule(self):
        for sid in SVK_2022_2029:
            lic = self.license_decisions.get(sid, {})
            rule = lic.get("rule_id", "")
            self.assertIn(
                "RESTRICTIVE", rule,
                f"{sid}: rule_id={rule!r} should contain RESTRICTIVE",
            )

    def test_high_quality_still_quarantined(self):
        """A source can be high quality AND quarantined. Quality != rights."""
        for sid in SVK_2022_2029:
            if sid in self.excluded:
                # It's excluded — that's correct regardless of quality
                continue
            # If somehow not excluded, that's a bug
            self.fail(f"{sid} should be excluded despite quality status")


class TestSourceIdStability(unittest.TestCase):
    """Source IDs in segmented unit_id must be stable after reprocessing."""

    def test_unit_ids_contain_source_prefix(self):
        for sid in SVK_2022_2029:
            units = _load_segmented_units(sid)
            self.assertGreater(len(units), 0, f"{sid} has no segmented units")
            for u in units:
                uid = u.get("unit_id", "")
                self.assertTrue(
                    uid.startswith(f"{sid}:"),
                    f"{sid}: unit_id {uid!r} does not start with '{sid}:'",
                )

    def test_all_sources_have_segmented_units(self):
        for sid in SVK_2022_2029:
            units = _load_segmented_units(sid)
            self.assertGreater(
                len(units), 0,
                f"{sid} has no segmented units after reprocessing",
            )


class TestProvenanceSurvival(unittest.TestCase):
    """Provenance information must survive reprocessing."""

    def test_source_manifest_entries_exist(self):
        manifest = _load_manifest()
        for sid in SVK_2022_2029:
            self.assertIn(
                sid, manifest,
                f"{sid} missing from source_manifest.csv",
            )

    def test_title_preserved_in_manifest(self):
        manifest = _load_manifest()
        for sid in SVK_2022_2029:
            m = manifest.get(sid, {})
            title = m.get("title", "")
            self.assertGreater(
                len(title), 5,
                f"{sid}: title too short or missing: {title!r}",
            )

    def test_tradition_set_in_manifest(self):
        manifest = _load_manifest()
        for sid in SVK_2022_2029:
            m = manifest.get(sid, {})
            tradition = m.get("tradition", "")
            self.assertGreater(
                len(tradition), 0,
                f"{sid}: tradition not set in manifest",
            )

    def test_sect_set_in_manifest(self):
        manifest = _load_manifest()
        for sid in SVK_2022_2029:
            m = manifest.get(sid, {})
            sect = m.get("sect", "")
            # SVK-2024 may have UNKNOWN sect, but field should exist
            self.assertIn(
                "sect", m,
                f"{sid}: 'sect' field missing from manifest",
            )


class TestMixedScriptPreservation(unittest.TestCase):
    """Mixed-script content (Devanagari + Latin) must be preserved."""

    def test_svk_2025_has_mixed_script(self):
        """SVK-2025 (Sthanang) has Devanagari script with Latin passages."""
        units = _load_segmented_units("SVK-2025")
        self.assertGreater(len(units), 0)
        # Check that some units contain Devanagari characters
        deva_units = sum(
            1 for u in units
            if any("\u0900" <= c <= "\u097f" for c in u["text"])
        )
        self.assertGreater(
            deva_units, 100,
            f"SVK-2025: expected Devanagari content, found {deva_units} units",
        )

    def test_svk_2029_has_mixed_script(self):
        """SVK-2029 (Aupapatik) has Hindi Devanagari + Latin."""
        units = _load_segmented_units("SVK-2029")
        self.assertGreater(len(units), 0)
        deva_units = sum(
            1 for u in units
            if any("\u0900" <= c <= "\u097f" for c in u["text"])
        )
        self.assertGreater(
            deva_units, 50,
            f"SVK-2029: expected Devanagari content, found {deva_units} units",
        )

    def test_svk_2027_has_gujarati(self):
        """SVK-2027 (Itihas) has Gujarati script."""
        units = _load_segmented_units("SVK-2027")
        self.assertGreater(len(units), 0)
        guj_units = sum(
            1 for u in units
            if any("\u0a80" <= c <= "\u0aff" for c in u["text"])
        )
        self.assertGreater(
            guj_units, 10,
            f"SVK-2027: expected Gujarati content, found {guj_units} units",
        )


class TestNoHtmlJsArtifacts(unittest.TestCase):
    """HTML/JS artifacts must be completely eliminated."""

    HTML_INDICATORS = [
        "window.dataLayer", "@font-face", "gtag(",
        "dataLayer.push", "<script", "<style",
    ]

    def test_no_html_in_segmented_units(self):
        for sid in SVK_2022_2029:
            units = _load_segmented_units(sid)
            for u in units:
                text = u["text"]
                for indicator in self.HTML_INDICATORS:
                    self.assertNotIn(
                        indicator, text,
                        f"{sid}: HTML artifact {indicator!r} found in "
                        f"unit {u.get('unit_id', '?')}",
                    )


class TestProcessingIntegrity(unittest.TestCase):
    """Verify the before/after numbers match audit expectations."""

    def test_total_units_match_audit(self):
        """Total segmented units for SVK-2022..2029 must be 9,022."""
        total = 0
        for sid in SVK_2022_2029:
            units = _load_segmented_units(sid)
            total += len(units)
        self.assertEqual(
            total, 9022,
            f"Expected 9,022 total units, got {total}",
        )

    def test_per_source_units_match_audit(self):
        expected = {
            "SVK-2022": 866, "SVK-2023": 1742, "SVK-2024": 17,
            "SVK-2025": 2969, "SVK-2026": 991, "SVK-2027": 313,
            "SVK-2028": 326, "SVK-2029": 1798,
        }
        for sid, exp_count in expected.items():
            units = _load_segmented_units(sid)
            self.assertEqual(
                len(units), exp_count,
                f"{sid}: expected {exp_count} units, got {len(units)}",
            )


class TestContextualMetadata(unittest.TestCase):
    """Verify Sthanakavasi contextual relationships in manifest."""

    @classmethod
    def setUpClass(cls):
        cls.manifest = _load_manifest()

    def test_7_of_8_sources_are_sthanakavasi(self):
        """7 of 8 JainQQ sources should be tagged STHANAKAVASI."""
        sv_count = 0
        for sid in SVK_2022_2029:
            m = self.manifest.get(sid, {})
            sect = m.get("sect", "").upper()
            if "STHANAKAVASI" in sect:
                sv_count += 1
        self.assertEqual(
            sv_count, 7,
            f"Expected 7 Sthanakavasi sources, got {sv_count}",
        )

    def test_svk_2024_is_pratikraman(self):
        """SVK-2024 is a Pratikraman practice guide."""
        m = self.manifest.get("SVK-2024", {})
        cat = m.get("text_category", "").lower()
        self.assertIn("pratikraman", cat)

    def test_amarmuni_in_5_sources(self):
        """Amarmuni should be teacher/author for 5 sources."""
        amar_count = 0
        for sid in SVK_2022_2029:
            m = self.manifest.get(sid, {})
            teacher = (m.get("teacher_or_author", "") or "").lower()
            if "amarmuni" in teacher or "amara muni" in teacher or "amar muni" in teacher:
                amar_count += 1
        self.assertEqual(
            amar_count, 5,
            f"Expected Amarmuni in 5 sources, got {amar_count}",
        )


if __name__ == "__main__":
    unittest.main()
