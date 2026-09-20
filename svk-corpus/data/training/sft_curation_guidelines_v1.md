# SFT Curation Guidelines v1

**Date:** 2026-09-20
**Status:** DRAFT

---

## 1. Purpose

These guidelines define the rules for human-curated, source-grounded SFT dataset construction for JainLLM.

**Critical principle:** Every example must be traceable to source material. No facts from model memory.

---

## 2. SFT Categories

| Code | Category | Description |
|------|----------|-------------|
| A | STHANAKAVASI_DOCTRINE | Sthanakavasi-specific doctrinal interpretation |
| B | AGAM_EXPLANATION | Explanation of Agam content |
| C | PRACTICE_EXPLANATION | Explanation of Jain practices |
| D | TEACHER_ATTRIBUTION | Content attributed to specific teachers |
| E | PRAKRIT_TERM_EXPLANATION | Explanation of Prakrit/Sanskrit terms |
| F | TRADITION_DISTINCTION | Comparisons between traditions |
| G | HISTORY_LINEAGE | Historical and lineage information |
| H | SOURCE_CITATION | Direct source citation questions |
| I | ABSTENTION | Questions where model should abstain |
| J | GENERAL_JAIN | General Jain knowledge |

---

## 3. Curation Rules

### Rule 1: Source Grounding
Every factual claim in the answer must be traceable to one or more source units.

**Do:** "According to the Acharanga Sutra commentary by Amarmuni (SVK-2030), ahimsa is defined as..."
**Don't:** "Ahimsa is the most important principle in Jainism."

### Rule 2: No Model Memory
Do not add facts from model memory or general knowledge.

### Rule 3: No Silent Tradition Merging
If sources disagree, represent the disagreement and attribute it.

**Do:** "The Sthanakavasi tradition interprets this as X, while the Murtipujak tradition interprets it as Y."
**Don't:** "Jain tradition interprets this as X."

### Rule 4: Evidence-Based Abstention
If the source does not answer the question, answer with an explicit evidence-based abstention.

**Do:** "The available source material does not contain information about [topic]."
**Don't:** Make up an answer.

### Rule 5: Teacher Attribution
Teacher attribution must be supported by provenance evidence.

### Rule 6: Sthanakavasi Classification
Sthanakavasi classification must require passage-level evidence. Source title alone is insufficient.

### Rule 7: No Generic-to-STH Promotion
Generic Jain/Śvetāmbara material cannot become Sthanakavasi simply through wording.

### Rule 8: Citation Required
Every example must have citation/provenance.

### Rule 9: Question Quality
Questions must not contain information that makes the answer trivial.

**Do:** "What is the Sthanakavasi position on idol worship?"
**Don't:** "The Sthanakavasi tradition rejects idol worship. Is this correct?"

### Rule 10: Avoid Templates
Avoid repetitive question templates.

### Rule 11: Preserve Terminology
Preserve original terminology where appropriate.

---

## 4. Curation Workflow

```
Source passage → Proposed question → Human-written answer → Source citation → Validation → Approval
```

### Steps:

1. **Select source passage** from corpus
2. **Propose question** based on passage content
3. **Write answer** using only information from the passage
4. **Add citation** with source_id, unit_id, text excerpt
5. **Validate** against curation rules
6. **Approve** or send back for revision

---

## 5. Example Format

```json
{
  "example_id": "EX-000001",
  "messages": [
    {
      "role": "user",
      "content": "What is the Sthanakavasi view on idol worship?"
    },
    {
      "role": "assistant",
      "content": "According to the Jinvani Pratikraman Special Issue (SVK-2037), the Sthanakavasi tradition does not practice idol worship. The text states that Sthanakavasi temples do not contain idols, unlike the Murtipujak tradition."
    }
  ],
  "question_type": "factual",
  "source_ids": ["SVK-2037"],
  "source_units": ["SVK-2037_unit_1234"],
  "citations": [
    {
      "source_id": "SVK-2037",
      "unit_id": "SVK-2037_unit_1234",
      "text_excerpt": "स्थानकवासी परम्परा में मूर्ति पूजा नहीं होती",
      "page_or_section": "Page 15"
    }
  ],
  "tradition": "SVETAMBARA",
  "lineage": "STHANAKAVASI",
  "knowledge_layer": "COMMENTARY",
  "content_role": "TEACHING",
  "teacher": "",
  "agam_id": "",
  "practice": "",
  "language": "Hindi",
  "verification_status": "SOURCE_GROUNDED",
  "reviewer_status": "APPROVED"
}
```

---

## 6. Quality Checklist

Before approving an example, verify:

- [ ] All factual claims traceable to source
- [ ] No facts from model memory
- [ ] Citation complete and accurate
- [ ] Question does not give away answer
- [ ] Answer uses source terminology
- [ ] No silent tradition merging
- [ ] Sthanakavasi classification has evidence
- [ ] Teacher attribution has provenance
- [ ] Abstention used when appropriate
- [ ] No repetitive template

---

## 7. Evaluation Separation

**TRAINING SFT DATA ≠ JAINBENCH EVALUATION DATA**

- Evaluation examples must be held out
- No source leakage between train and evaluation splits
- Evaluation set should be created separately
- Minimum 20% of curated examples held out for evaluation

---

## 8. Hard Stop

These guidelines are STRATEGY + CONTRACT ONLY.

Do NOT:
- Generate SFT Q&A
- Generate synthetic answers
- Train a model
- Select a foundation model
- Download a model
- Run QLoRA
- Run CPT
- Acquire new sources
