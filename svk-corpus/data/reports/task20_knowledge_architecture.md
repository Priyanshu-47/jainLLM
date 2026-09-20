# Task 20: JainLLM Knowledge Architecture

## Goal

Design and implement the metadata architecture for the JainLLM knowledge system: ontology, source registry, Agam inventory, and knowledge coverage matrix. This is a **metadata-only** task — no downloads, ingestion, SFT generation, model selection, or retrieval changes.

## Architecture Decision

JainLLM is **NOT** a RAG-only system. The target architecture is:

```
External Jain sources
    ↓
Source Registry / Provenance
    ↓
Corpus ingestion + normalization
    ↓
Jain Knowledge Ontology
    ↓
Retrieval corpus + Training corpus
    ↓
Existing open-weight foundation model
    ↓
SFT/QLoRA adaptation
    ↓
JainLLM orchestrator
    ↓
retrieval + adapted model + evidence-grounded answer
```

External source platforms:
- **JainQQ**: Agam/canonical source discovery, Sthanakavasi editions, multilingual textual editions
- **Jainebooks**: Broad Jain literature discovery (books, magazines, pravachan, teacher material, practice material). MCP is an **ACQUISITION/RESEARCH interface**, NOT the inference backend.

---

## Files Created

| File | Description |
|------|-------------|
| `data/knowledge/jain_knowledge_ontology_v1.json` | Controlled vocabularies: traditions, layers, roles, practices, entities, relationships |
| `data/knowledge/agam_inventory_v1.json` | 32-entry Agam inventory schema with sample entries |
| `data/knowledge/source_registry_v1.json` | Source registry schema with 2 initial entries (JainQQ, Jainebooks) |
| `data/knowledge/knowledge_coverage_v1.json` | 23-topic coverage matrix across all knowledge areas |
| `src/svk_corpus/knowledge/__init__.py` | Validators for all knowledge contracts |
| `tests/test_knowledge_contract.py` | 55 tests for knowledge architecture validation |
| `data/reports/task20_knowledge_architecture.md` | This report |

---

## Ontology Design

The ontology (`jain_knowledge_ontology_v1.json`) defines 11 controlled vocabularies:

| Vocabulary | Count | Purpose |
|-----------|-------|---------|
| `traditions` | 7 | Sectarian identification (STHANAKAVASI is primary target) |
| `knowledge_layers` | 14 | What type of knowledge a source contains |
| `content_roles` | 12 | Functional role of content |
| `practices` | 9 | Jain practice types (samayik, pratikraman, etc.) |
| `canonical_statuses` | 6 | Whether text is canonical, commentary, etc. |
| `entity_types` | 18 | Types of entities for future knowledge graph linking |
| `relationship_types` | 11 | Relationships between entities |
| `rights_statuses` | 5 | Rights clearance state |
| `verification_statuses` | 4 | How thoroughly a claim has been verified |

### Design rationale

- **Tradition granularity**: STHANAKAVASI is separated from SVETAMBARA_GENERIC because the project's goal is sect-specific training. DIGAMBARA is included for cross-tradition distinction.
- **Knowledge layer vs content role**: Layer describes *what* the knowledge IS (canonical, commentary, lexicon); role describes *what it does* in the system (primary scripture, teaching, reference). A single source may have both.
- **Practice taxonomy**: The 8 named practices + OTHER cover the Avashyaka obligations and major Sthanakavasi practice forms.
- **Entity types**: Defined for future knowledge graph construction. Includes teacher roles (ACHARYA, MUNI, SADHVI), source types (BOOK, MAGAZINE, PRAVACHAN), and conceptual entities (CONCEPT, TIRTHANKARA, PLACE, HISTORICAL_EVENT, LINEAGE).

---

## Source Registry Design

The source registry (`source_registry_v1.json`) is a structured metadata store for all external Jain sources. Every source must be registered here before acquisition, ingestion, or training.

### Key fields

| Field | Purpose |
|-------|---------|
| `source_id` | Unique EXT-NNNN identifier |
| `platform` | Where the source is hosted (JAINQQ, JAINEBOOKS, etc.) |
| `rights_status` | CLEAR / PERMISSION_REQUIRED / UNCLEAR / RESTRICTED / UNKNOWN |
| `retrieval_candidate` | Whether this source is a retrieval candidate |
| `sft_candidate` | Whether this source is an SFT candidate (requires CLEAR rights) |
| `verification_status` | How thoroughly metadata has been verified |

### Critical rules enforced by validators

1. **`download_available` does NOT imply `rights_status=CLEAR`**: A source being downloadable does not mean training is permitted.
2. **`sft_candidate=true` requires `rights_status=CLEAR`**: No SFT training without verified rights.
3. **`VERIFIED` canonical status requires evidence**: A source cannot claim VERIFIED canonical status without a license or license_evidence_url.
4. **Platform availability ≠ training permission**: JainQQ and Jainebooks are discovery platforms, not training grants.

### Initial entries

Two entries registered:
- **EXT-0001**: JainQQ — Sthanakavasi Agam discovery platform
- **EXT-0002**: Jainebooks MCP — Broad Jain literature discovery (catalogue interface only, NOT inference backend)

---

## Agam Inventory Design

The Agam inventory (`agam_inventory_v1.json`) records the Jain canonical text landscape across traditions.

### Structure

Each entry carries:
- `agam_id` (AGAM-NNN)
- `traditional_name` + `alternate_names`
- `sequence_number` (varies by tradition)
- `group` (ANGA, UPANGA, MULASUTRA, CHEDASUTRA, PRATIYANUYOGA)
- `tradition` (which tradition recognizes this Agam)
- `canonical_status` + `verification_status`
- `source_id` (link to source registry)
- `rights_status` of the specific text we have

### Key design decisions

1. **No authoritative 32-Agam assertion**: The inventory does NOT take a position on which Agam count is "correct." Different traditions enumerate differently (Sthanakavasi: ~32, Murtipujaka: 45, Digambara: different set).
2. **Tradition field per entry**: Each entry records which tradition recognizes it. An entry with `tradition=MULTI_TRADITION` means the text is recognized across traditions.
3. **Verification states**: VERIFIED, PROVISIONAL, CONTESTED, UNKNOWN. Most entries start as UNKNOWN and are promoted as sources are acquired.
4. **32 entries provided as samples**: These represent the traditional Sthanakavasi/Murtipujaka enumeration. Entries with `source_id=null` have no text acquired yet.

### Current coverage

| Status | Count |
|--------|-------|
| Has source_id (text acquired) | 5 (AGAM-001, 002, 013, 015, plus SVK-1001 covers 2) |
| No source (UNKNOWN) | 27 |
| VERIFIED | 0 (all PROVISIONAL or UNKNOWN) |

---

## Knowledge Coverage Matrix

The coverage matrix (`knowledge_coverage_v1.json`) maps 23 knowledge areas against the current corpus.

### Coverage summary

| Status | Count | Topics |
|--------|-------|--------|
| STRONG | 1 | Prakrit terminology |
| PARTIAL | 6 | 24 Tirthankaras, Mahavira, Agamas, Philosophy, Gujarati, English |
| WEAK | 2 | Sthanakavasi doctrine, Sthanakavasi history |
| MISSING | 14 | All practices, Acharyas, Munis, Sadhvis, modern teachers, cross-tradition |

### Critical gaps

1. **All 8 named practices**: MISSING (no practice material in training)
2. **Sthanakavasi-specific content**: WEAK to MISSING (only SVK-2010 provides doctrinal content)
3. **Teacher/Acharya biography**: MISSING (no teacher commentaries or biographies)
4. **Cross-tradition distinction**: MISSING (no comparative material)

---

## How JainQQ Will Be Used

JainQQ serves as the **primary platform for Agam/canonical source discovery**:

1. **Discovery**: Identify which Sthanakavasi Agam texts exist and where they are hosted
2. **Acquisition**: Download or copy text for rights clearance
3. **Rights gate**: Each acquired text must pass the rights gate (CLEAR status) before training
4. **Registration**: Acquired texts are registered in the source registry with full metadata
5. **Ingestion**: Texts that pass all gates enter the corpus pipeline

JainQQ is **NOT** an inference backend. It is a source discovery and acquisition platform.

---

## How Jainebooks/MCP Will Be Used

Jainebooks MCP serves as a **broad literature discovery and catalogue interface**:

1. **Catalogue search**: Discover books, magazines, pravachan, teacher material, practice material, biographies, secondary literature
2. **Rights research**: Use catalogue metadata to assess publication dates and rights status
3. **Acquisition planning**: Identify which texts to acquire for the corpus
4. **MCP is NOT part of model inference**: The MCP interface provides catalogue data. It does NOT feed into the trained model's inference pipeline.

**Why MCP is not part of inference:**
- MCP provides catalogue metadata, not source text
- Training requires verified rights — MCP availability ≠ permission
- The model must answer from its trained knowledge + retrieval, not from live MCP queries
- MCP is a research/acquisition tool, not a runtime dependency

---

## How This Supports Future SFT + Retrieval

### For retrieval

- Source registry provides metadata for retrieval filtering (tradition, knowledge_layer, content_role)
- Agam inventory enables canonical text retrieval by name, group, and tradition
- Coverage matrix identifies retrieval-ready topics vs. gaps

### For SFT

- Source registry's `sft_candidate` flag pre-screens sources for training eligibility
- Knowledge layers and content roles enable task-specific SFT example generation
- Practice taxonomy enables practice-specific Q&A training
- Entity types and relationships enable future knowledge graph construction

### For evaluation

- Coverage matrix identifies which topics can generate evaluation questions
- JainBench-v0 categories align with ontology's knowledge layers
- Abstention training is informed by MISSING/WEAK coverage areas

---

## Unresolved Canonical Questions

1. **Sthanakavasi Agam count**: The traditional count is ~32, but the exact enumeration varies by source. This inventory does not take a position.
2. **Murtipujaka 45-Agama set**: SVK-0029 (Jainaagam) references this set. Whether to include Murtipujaka-specific Agams in a Sthanakavasi-focused system is unresolved.
3. **Drastivad Sutra**: Lost text. Should it be marked CANONICAL with `translation_available=false` or excluded?
4. **Practice material sourcing**: Where to find Sthanakavasi-specific practice texts (samayik, pratikraman guides) — JainQQ or Jainebooks is the likely source.
5. **Teacher lineage mapping**: No Sthanakavasi acharya lineage data exists in the current corpus. JainQQ/Jainebooks discovery needed.
6. **Rights for practice texts**: Many practice texts are modern publications (post-1960). Rights clearance will be required.
