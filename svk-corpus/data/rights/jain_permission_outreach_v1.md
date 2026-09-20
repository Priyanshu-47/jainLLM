# Permission Outreach Package — JainQQ / Padma Prakashan Sources

**Status:** DRAFT — NOT SENT
**Prepared:** 2026-09-20
**Task:** 31 (Rights / Access / Source-Use Audit)

---

## 1. Sources Requiring Permission

All 8 JainQQ sources (SVK-2022 through SVK-2029) carry identical restrictive terms:

> "JAIN EDUCATION INTERNATIONAL FOR PRIVATE AND PERSONAL USE ONLY"

Additionally, SVK-2022 carries a publisher copyright notice:

> "(c) All rights reserved: Padma Prakashan, Delhi"
> Publisher: Padma Prakashan, Padma Dham, Narela Mandi, Delhi-110040

### Source Inventory

| Source ID | Title | Author/Commentator | Language | Tradition | Units Processed |
|-----------|-------|-------------------|----------|-----------|-----------------|
| SVK-2022 | Avashyak Sutra Sthanakvasi | Amarmuni | Prakrit+Hindi | Sthānakavāsī | 866 |
| SVK-2023 | Uttaradhyayana Sutra Sthanakvasi | Amarmuni | Prakrit+Hindi | Sthānakavāsī | 1,742 |
| SVK-2024 | Pratikraman - Self Reflection | Pravin K Shah | English | Unknown | 17 |
| SVK-2025 | Sthanang Sutra Sthanakvasi | Amarmuni, Shreechand Surana | Prakrit+Hindi | Sthānakavāsī | 2,969 |
| SVK-2026 | Dasvaikalik Sutra Sthanakvasi | Shayyambhavsuri, Amarmuni, Shreechand Surana | Prakrit+Hindi | Sthānakavāsī | 991 |
| SVK-2027 | Sthanakvasi Jain Itihas | Kesrichand Bhandari | Gujarati | Sthānakavāsī | 313 |
| SVK-2028 | Inner Journey Part 01 | Namramuni | Hindi+English | Sthānakavāsī | 326 |
| SVK-2029 | Aupapatik Sutra Sthanakvasi | Amarmuni, Shreechand Surana | Prakrit+Hindi | Sthānakavāsī | 1,798 |

**Total processed units:** 9,022
**Total characters:** ~6.1M

### Why These Sources Matter

These are the **only confirmed Sthānakavāsī Agam/commentary sources** in the entire corpus. They contain:

- Complete Prakrit mūla (root text) of 5 Agams
- Hindi commentary by Amarmuni (confirmed Sthānakavāsī commentator)
- Sthānakavāsī-specific practice explanations (Avashyaka, Samayik, Pratikraman)
- Institutional history of the Sthānakavāsī tradition
- Modern teaching material by confirmed Sthānakavāsī teachers

Without permission, the project cannot include any Sthānakavāsī-specific primary material in training.

---

## 2. Proposed Recipients

### Primary: Padma Prakashan

- **Address:** Padma Dham, Narela Mandi, Delhi-110040
- **Evidence:** Copyright notice on SVK-2022 printed edition
- **Confidence:** HIGH — publisher is named on the physical book
- **Note:** No website, email, or phone found in online search

### Secondary: Jain Education International

- **Source:** jainqq.org platform terms
- **Evidence:** Platform-wide "JAIN EDUCATION INTERNATIONAL FOR PRIVATE AND PERSONAL USE ONLY" stamp
- **Confidence:** MEDIUM — may be the platform operator, not necessarily the rights holder
- **Contact:** Through jainqq.org platform (if accessible)

### Tertiary: Akhil Bharatiya Svetambar Sthanakvasi Jain Conference

- **Evidence:** Publisher of several historical Sthānakavāsī works (SVK-0002, SVK-0009)
- **Confidence:** LOW for JainQQ sources specifically — no direct link established
- **Contact route:** IMJM/Siddhachalam (verified route from Task 7)

---

## 3. Permission Request Scope

We request permission for the following uses, each independently:

### A. Reading / Research Use
That the project may access, read, and study the texts for internal research purposes.

### B. Corpus Storage
That the project may store digitized text copies for processing and analysis.

### C. RAG Indexing
That the project may include the texts in a retrieval-augmented generation index, where users can search and retrieve passages with full attribution to the source, edition, and page.

### D. Model Training (SFT / QLoRA)
That the project may use the texts as training data for supervised fine-tuning or QLoRA adaptation of an open-weight language model, specifically to improve the model's understanding of Sthānakavāsī Jain tradition.

### E. Dataset Redistribution
That the project may redistribute the processed text as a structured dataset (with full provenance, source attribution, and license metadata) under terms compatible with the original.

### F. Model Redistribution
That the project may distribute the resulting adapted model, which contains learned patterns from the texts but does not reproduce the texts verbatim.

---

## 4. Project Description (For Outreach)

### JainLLM — An AI Study and Research Assistant for the Śvetāmbara Sthānakavāsī Jain Tradition

**Purpose:** Build a non-commercial AI system that helps students and researchers study and understand the Sthānakavāsī Jain tradition. The system:

- Always cites the source, edition, page, and teacher/commentator for every answer
- Preserves full provenance for every passage
- Distinguishes between canonical texts, commentaries, and modern teachings
- Is not intended to replace religious authorities or the living tradition
- Is designed for educational and research use

**Technology:**
- Uses existing open-weight foundation models (not trained from scratch)
- Adapts the model through supervised fine-tuning (SFT) and QLoRA
- Maintains a retrieval corpus for evidence-grounded answers
- Preserves complete source attribution and provenance

**Scope:**
- Focus: Śvetāmbara Sthānakavāsī tradition specifically
- Languages: Prakrit, Hindi, Gujarati, English
- Non-commercial: The project is open-source and non-commercial

**Team:**
- Volunteer-driven research project
- No commercial backing
- Open-source codebase

---

## 5. What We Are NOT Requesting

- We are NOT requesting to claim authorship of the original texts
- We are NOT requesting to remove attribution or provenance
- We are NOT requesting exclusive rights
- We are NOT requesting commercial use rights
- We are NOT requesting to replace the original publications

---

## 6. Attribution Guarantee

If permission is granted, the project will:

1. **Always attribute** the source, author/commentator, publisher, edition, and page for every passage used
2. **Never present** the adapted model as a replacement for the original texts
3. **Maintain provenance** chains: source → teacher → Agam → tradition → passage
4. **Include license metadata** in any released dataset
5. **Respect any additional attribution requirements** specified by the rights holder

---

## 7. Rights Holder Response Template

Any response should ideally address:

| Question | Yes/No/Partial |
|----------|----------------|
| Are you the rights holder or can you identify them? | |
| May we read/study these texts for research? | |
| May we store digitized copies for processing? | |
| May we include texts in a retrieval index (with attribution)? | |
| May we use texts for model training (SFT/QLoRA)? | |
| May we redistribute the processed dataset? | |
| May we distribute the resulting adapted model? | |
| Are there additional attribution requirements? | |
| Are there usage restrictions we should know about? | |

---

## 8. Important Notes

### This Package Is NOT Sent

This document is a preparation for potential outreach. No permission has been requested, implied, or granted.

### Rights Holder Identification Is Uncertain

The JainQQ platform terms say "JAIN EDUCATION INTERNATIONAL" but this may be the platform operator rather than the rights holder of individual texts. The actual publisher (Padma Prakashan) is named only on SVK-2022's printed edition.

### Rights Are Not Assumed

The fact that texts were publicly accessible on jainqq.org does not constitute permission for ML training or redistribution.

### Religious Sensitivity

The project respects the Sthānakavāsī tradition and its authorities. Permission requests should be framed as an invitation to participate in making the tradition more accessible through AI, not as a demand or entitlement.

---

## 9. Additional Sources Requiring Permission

Beyond the 8 JainQQ sources, these sources also require permission:

| Source | Reason | Priority |
|--------|--------|----------|
| SVK-0002 | Jain Dharma (1958) - in copyright, death year 1994 | HIGH - already has draft letter |
| SVK-0011 | Acharrang Sutra (1966) - boundary year | MEDIUM |
| SVK-0036 | Jainendra Siddhanta Kosa (1990) - modern, uploader CC0 not credible | LOW |

---

## 10. Recommended Next Steps

1. **Identify the actual rights holder** of the JainQQ texts (Padma Prakashan vs Jain Education International vs individual authors)
2. **Attempt contact** through available channels (jainqq.org if accessible, or physical address for Padma Prakashan)
3. **Send the permission request** if a valid contact is found
4. **Record any response** in the rights outreach register
5. **Do not use the texts** for training until permission is explicitly granted
