# TASK 62 SFT REVIEW — Queue R
**Queue**: QUEUE R - RE-ADJUDICATE PRIOR VERIFIED ROWS
**Reason**: Prior HUMAN_VERIFIED rows whose recorded decision history does not stand on its own (Task 61 gap: 2025 REVISE, 2029 REJECT, 0038 conflicting).
**Candidates**: 3

## CRITERIA (check EACH candidate)
| # | Criterion | What to check | Priority |
|---|-----------|---------------|----------|
| 1 | qa_alignment | Answer actually answers the question? | Normal |
| 2 | source_grounding | Every factual claim supported by source quote? | HIGH |
| 3 | attribution | No commentary→Mahavira, teacher→canonical confusion? | HIGH |
| 4 | sect_distinction | No Sthanakavasi claim turned into universal Jain claim? | Normal |
| 5 | knowledge_layer | Canonical vs commentary preserved? | Normal |
| 6 | abstention | For evidence gaps, declines instead of inventing? | Normal |
| 7 | practice | Practice identity/tradition attribution correct? | Normal |
| 8 | language | Prakrit/Sanskrit terminology sound? | Normal |
| 9 | language_quality | Natural, grammatical phrasing? | Normal |
| 10 | no_fabrication | No invented citations/teachers/dates? | HIGH |
| 11 | pedagogy | Teaches source-aware behaviour? | Normal |

## OUTPUT FORMAT
Return JSONL, one line per candidate:
```json
{"review_id": "T61-CAND-0001", "decision": "APPROVE|REVISE|REJECT", "failed_criteria": ["name"], "notes": "reason", "revised_answer": ""}
```
- **APPROVE**: passes all HIGH criteria, no critical issues
- **REVISE**: fixable issues (specify failed criteria + revised_answer)
- **REJECT**: fundamentally flawed (fabrication, wrong sect, wrong attribution)

---

### T61-RECON-SFT-SEED-CAND-SVK-2025-SVK-2025 (pos 1)
- Category: AGAM_EXPLANATION | Priority: 
- Source: Sthanang Sutra (SVK-2025)
- Sect: STHANAKAVASI (HIGH) | Layer: CANONICAL_SCRIPTURE
- Rights: TRAINING_ALLOWED_WITH_PERMISSION_EVIDENCE | Split: validation

**Q**: What does the Sthanang Sutra teach about Allustrated?

**A**: The concept of Allustrated is central to Jain philosophy. According to Sthanang Sutra (AGAM-003), the text explains: "सचित्र स्थानांग सूत्र प्रवर्त्तक अमर मुनि G D Allustrated STHANANGA SUTRA 1 Pravartak Amar Muni."


---

### T61-RECON-SFT-SEED-CAND-SVK-2029-SVK-2029 (pos 2)
- Category: CONCEPT_EXPLANATION | Priority: 
- Source: Aupapatik Sutra (SVK-2029)
- Sect: STHANAKAVASI (HIGH) | Layer: CANONICAL_SCRIPTURE
- Rights: TRAINING_ALLOWED_WITH_PERMISSION_EVIDENCE | Split: test

**Q**: What is Karma in Jain teaching?

**A**: The concept of Karma is central to Jain philosophy. According to Aupapatik Sutra (AGAM-012), the text explains: "Upapat means reincarnation of a being or soul. What conduct and action leads to reincarnation at which specific genus or place? The Agam that contains answers and explanations to such questions about rebirth is called Aupapatik Sutra. It contains detailed description of a city, garden, kings assembly, king, the physical excellence of Bhagavan Mahavir s body, his Shraman disciples, his sermon, and many other topics This also contains detailed information about Ambad Parivrajak and the Tapas and P..."


---

### T61-RECON-SFT-SEED-CAND-SVK-0038-unknown (pos 3)
- Category: CONCEPT_EXPLANATION | Priority: 
- Source: Notes on Jainism (SVK-0038)
- Sect: UNKNOWN (HIGH) | Layer: MIXED
- Rights: TRAINING_ALLOWED | Split: train

**Q**: What is Jain in Jain teaching?

**A**: The concept of Jain is central to Jain philosophy. According to this Jain source, the text explains: "THESE notes on Jain ism have been compiled mainly from information supplied to me by Gujarati speaking Jaina, so it has seemed advisable to use the Gujarati forms of their technical terms."


---
