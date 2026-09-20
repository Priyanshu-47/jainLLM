# Task 26 — Jainebooks MCP Discovery Report

**Date:** 2026-09-19 · **Status:** COMPLETE (discovery only)

---

## 1. MCP Capabilities Discovered

| Capability | Value |
|------------|-------|
| Endpoint | `https://jainebooks.org/mcp` |
| Transport | Streamable HTTP |
| Authentication | None (free, read-only) |
| Rate limit | 120 requests/minute |
| Tools | `search_books`, `get_book`, `list_filters` |
| Content access | Catalogue metadata via MCP; full text readable/downloadable via jainebooks.org with free account |

**Key limitation:** MCP provides catalogue search and metadata only. Full text requires signing in to jainebooks.org. No bulk export via MCP.

---

## 2. Searches Performed

| Search | Platform | Results |
|--------|----------|---------|
| "sthanakvasi" books | Jainebooks | 10+ titles found |
| "pratikraman" books | Jainebooks | 10+ titles found |
| "samayik" books | Jainebooks | 3+ titles found |
| "anand rishi" / "praveen rishi" | Jainebooks | 0 direct results |
| "kanji swami" sthanakvasi | Jainebooks | 157 books found |
| "namramuni" samayik | Jainebooks | Practice guides found |
| "avashyak" / "vandana" / "pratyakhyan" | Jainebooks | Multiple results |
| Sthanakvasi teachers | JainQQ | 7 teachers identified |

---

## 3. Candidates Found

**14 Jainebooks candidates** identified:

| Priority | Count | Description |
|----------|-------|-------------|
| P0 | **4** | Confirmed Sthanakvasi practice/history material |
| P1 | **5** | Strong contextual material |
| P2 | **3** | Supplementary material |
| P3 | **2** | Reference/background |

---

## 4. Top P0 Sources

| ID | Title | Author | Practice | Language | Tradition |
|----|-------|--------|----------|----------|-----------|
| JB-001 | Look-N-Learn Samayik | Namramuni Maharaj | SAMAYIK | English | STHANAKAVASI ✓ |
| JB-002 | Shravak Pratikraman | Nathmal | PRATIKRAMAN | English | UNKNOWN |
| JB-003 | Sarvasamanya Pratikraman Avashyak | Sankalit | PRATIKRAMAN;AVASHYAKA | English | UNKNOWN |
| JB-004 | Sthanakvasi Jain Parampara ka Itihas | Sagarmal Jain | HISTORY | Hindi | STHANAKAVASI ✓ |

---

## 5. Strongest Sthanakavasi Teacher Sources

| Teacher | Books | Evidence | Priority |
|---------|-------|----------|----------|
| **Namramuni Maharaj** | 177 | Jainebooks confirms Sthanakvasi Muni | P0 |
| **Amarmuni** | 3 | JainQQ Sthanakvasi Agam commentator | P0 |
| **Acharya Ghanshilalji Maharaj** | 2 | Priydarshini commentary, Sthanakvasi | P0 |
| **Sagarmal Jain** | 2 | Tradition's own historian | P1 |
| **Kanji Swami** | 157 | Originally Sthanakvasi, later Digambara-influenced | P3 |
| **Anand Rishi** | 0 | No digital texts found | P1 |
| **Praveen Rishi** | 1 | eLibrary listing only | P1 |

---

## 6. Strongest Practice Sources

| Practice | Best Source | Platform | Language |
|----------|-------------|----------|----------|
| SAMAYIK | JB-001 (Namramuni Maharaj) | Jainebooks | English |
| PRATIKRAMAN | JB-002 + JAINQQ-002489 | Both | English + Prakrit/Hindi |
| AVASHYAKA | JB-003/010/011 (trilingual) + JAINQQ-002489 | Both | Eng+Hin+Guj+Prakrit |
| KAYOTSARGA | JAINQQ-002489 only | JainQQ | Prakrit/Hindi |
| VANDANA | JAINQQ-002489 only | JainQQ | Prakrit/Hindi |
| PRATYAKHYAN | JAINQQ-002489 only | JainQQ | Prakrit/Hindi |
| CHAUVISANTHO | JAINQQ-002489 only | JainQQ | Prakrit/Hindi |
| PARYUSHAN | **NO SOURCE FOUND** | — | — |

---

## 7. Remaining Practice Gaps

| Practice | Status | Gap |
|----------|--------|-----|
| SAMAYIK | STRONG | Teacher commentary beyond educational guide |
| PRATIKRAMAN | STRONG | Sthanakvasi-specific pravachan |
| KAYOTSARGA | WEAK | No standalone guide, no teacher commentary |
| VANDANA | WEAK | No standalone explanation |
| PRATYAKHYAN | WEAK | No standalone explanation |
| CHAUVISANTHO | WEAK | No standalone text |
| AVASHYAKA | STRONG | Part 2 may exist |
| PARYUSHAN | **CRITICAL** | No source found anywhere |

---

## 8. Rights/Access Limitations

- **All Jainebooks content requires free account** to read/download
- **Rights status UNKNOWN** for all candidates
- **No explicit training permission** granted by any source
- Jainebooks is a free library but **does not claim copyright clearance**
- Must identify actual rights holders before any training use

---

## 9. Recommended Acquisition Batch

### Tier 1 (acquire immediately):

1. **JAINQQ-002489** — Avashyak Sutra Sthanakvasi (fills 7/8 practice gaps)
2. **JB-001** — Look-N-Learn Samayik (confirmed Sthanakvasi teacher)
3. **JB-004** — Sthanakvasi Jain Parampara ka Itihas (tradition's own history)

### Tier 2 (acquire after Tier 1):

4. **JB-002** — Shravak Pratikraman (practice guide)
5. **JB-003** — Sarvasamanya Pratikraman Avashyak English
6. **JAINQQ-002494** — Uttaradhyayana Sthanakvasi edition

### Total recommended: 6 sources

---

## 10. What Can Realistically Become Training Data

After verification:
- JB-001 (Namramuni Maharaj Samayik) — HIGH suitability
- JB-004 (Sthanakvasi history) — HIGH suitability
- JAINQQ-002489 (Avashyak Sutra) — HIGHEST suitability
- JB-002/003 (Pratikraman guides) — MODERATE (tradition unverified)

---

## 11. What Still Requires Verification

- Sthanakvasi association for JB-002, JB-003, JB-007, JB-008, JB-009
- Rights/permission status for all sources
- Anand Rishi / Praveen Rishi digital text availability
- Paryushan practice material (not found anywhere)
- Kayotsarga standalone practice guide (not found)

---

## Files Created

- `data/acquisition/jainebooks_candidate_inventory_v1.json` — 14 candidates
- `data/acquisition/sthanakavasi_practice_gap_v2.json` — updated gap matrix
- `data/acquisition/sthanakavasi_teacher_source_inventory_v2.json` — 9 teachers
- `data/reports/task26_jainebooks_mcp_discovery.md` — this report
