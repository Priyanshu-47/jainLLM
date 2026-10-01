# TASK 62 SFT REVIEW — Queue C
**Queue**: QUEUE C - ABSTENTION
**Reason**: Task 60: abstention_correct 0/4 for both arms; the model never declines.
**Candidates**: 22

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

### T61-CAND-0232 (pos 1)
- Category: ABSTENTION/INSUFFICIENT_EVIDENCE | Priority: abstention, no_fabrication, qa_alignment
- Source: Notes on Modern Jainism (1910) (SVK-0038)
- Sect: UNKNOWN (HIGH) | Layer: MIXED
- Rights: TRAINING_ALLOWED | Split: train

**Q**: In which year was the Terapanth sector of Jain monastics founded?

**A**: What the corpus does say: "They are recruited from all three sei-ts, though their founder was a Sthfinakavasi, who about 150 years ago, in Sojat ( Marwar ), entertained doubts about certain current practices, and founded a sect of his own. They are called Terapantha, because the number of Sadhus who joined was originally thirteen. Their ascetics wear the same dress, etc., as the Sthanakavasi Sadhu, but will not stay in an U" (Notes on Modern Jainism (1910) (Mrs. Sinclair Stevenson, 1910)). The corpus does not record a founding year for Terapanth, so this question cannot be answered from the available sources. Evidence needed first: a dated Terapanth foundation record.

**Evidence**: They are recruited from all three sei-ts, though their founder was a Sthfinakavasi, who about 150 years ago, in Sojat ( Marwar ), entertained doubts about certain current practices, and founded a sect of his own. They are called Terapantha, because the number of Sadhus who joined was originally thirteen. Their ascetics wear the same dress, etc., as the Sthanakavasi Sadhu, but will not stay in an U
**Source text**: They are recruited from all three sei-ts, though their founder was a Sthfinakavasi, who about 150 years ago, in Sojat ( Marwar ), entertained doubts about certain current practices, and founded a sect of his own. They are called Terapantha, because the number of Sadhus who joined was originally thirteen. Their ascetics wear the same dress, etc., as the Sthanakavasi Sadhu, but will not stay in an U
- Citation: [They are recruited from all three sei-ts, though their founder was a Sthfinakavasi, who about 150 years ago, in Sojat ( Marwar ), entertained doubts a](https://archive.org/details/notesonmodernjai00steviala)

---

### T61-CAND-0233 (pos 2)
- Category: ABSTENTION/INSUFFICIENT_EVIDENCE | Priority: abstention, no_fabrication, qa_alignment
- Source: Notes on Modern Jainism (1910) (SVK-0038)
- Sect: UNKNOWN (HIGH) | Layer: MIXED
- Rights: TRAINING_ALLOWED | Split: train

**Q**: In which year was the Sthanakavasi sect established as a separate tradition?

**A**: What the corpus does say: "The following is the Canon of Scriptures held by the Jaina of Western India, together with brief notes as to their contents. Various sects and sub-sects differ very much with regard to the Chedagrantha, Mulagrantha and Payanna, but all Svetambara and Sthanakavasi practically agree with regard to the Anga and Upaiiga. They hold that originally there were Twelve Anga, but that one, the Dris'tivada A" (Notes on Modern Jainism (1910) (Mrs. Sinclair Stevenson, 1910)). The corpus does not record a founding year for the Sthanakavasi sect, so this question cannot be answered from the available sources. Evidence needed first: a dated historical record of the Sthanakavasi split.

**Evidence**: The following is the Canon of Scriptures held by the Jaina of Western India, together with brief notes as to their contents. Various sects and sub-sects differ very much with regard to the Chedagrantha, Mulagrantha and Payanna, but all Svetambara and Sthanakavasi practically agree with regard to the Anga and Upaiiga. They hold that originally there were Twelve Anga, but that one, the Dris'tivada A
**Source text**: The following is the Canon of Scriptures held by the Jaina of Western India, together with brief notes as to their contents. Various sects and sub-sects differ very much with regard to the Chedagrantha, Mulagrantha and Payanna, but all Svetambara and Sthanakavasi practically agree with regard to the Anga and Upaiiga. They hold that originally there were Twelve Anga, but that one, the Dris'tivada A
- Citation: [The following is the Canon of Scriptures held by the Jaina of Western India, together with brief notes as to their contents. Various sects and sub-sec](https://archive.org/details/notesonmodernjai00steviala)

---

### T61-CAND-0234 (pos 3)
- Category: ABSTENTION/INSUFFICIENT_EVIDENCE | Priority: abstention, no_fabrication, qa_alignment
- Source: Notes on Modern Jainism (1910) (SVK-0038)
- Sect: UNKNOWN (HIGH) | Layer: MIXED
- Rights: TRAINING_ALLOWED | Split: train

**Q**: How many Agam texts do the Digambara Jains accept?

**A**: What the corpus does say: "the °rder into the white clothed Svetam- bara and the nude or " sky clothed " Digambara. A great famine arose in 310 B. c., some two centuries after the death of Mahavira, in Magadha fBihar), and, as sometimes happens in India at the present day, under pressure of the famine a great part of the population emigrated, amongst them Bhadrabahu, the then head of the Jaina community, and a number of his" (Notes on Modern Jainism (1910) (Mrs. Sinclair Stevenson, 1910)). The corpus does not record a count of Digambara Agam texts, so this question cannot be answered from the available sources. Evidence needed first: a Digambara canonical list in this corpus.

**Evidence**: the °rder into the white clothed Svetam- bara and the nude or " sky clothed " Digambara. A great famine arose in 310 B. c., some two centuries after the death of Mahavira, in Magadha fBihar), and, as sometimes happens in India at the present day, under pressure of the famine a great part of the population emigrated, amongst them Bhadrabahu, the then head of the Jaina community, and a number of his
**Source text**: the °rder into the white clothed Svetam- bara and the nude or " sky clothed " Digambara. A great famine arose in 310 B. c., some two centuries after the death of Mahavira, in Magadha fBihar), and, as sometimes happens in India at the present day, under pressure of the famine a great part of the population emigrated, amongst them Bhadrabahu, the then head of the Jaina community, and a number of his
- Citation: [the °rder into the white clothed Svetam- bara and the nude or " sky clothed " Digambara. A great famine arose in 310 B. c., some two centuries after t](https://archive.org/details/notesonmodernjai00steviala)

---

### T61-CAND-0235 (pos 4)
- Category: ABSTENTION/INSUFFICIENT_EVIDENCE | Priority: abstention, no_fabrication, qa_alignment
- Source: Notes on Modern Jainism (1910) (SVK-0038)
- Sect: UNKNOWN (HIGH) | Layer: MIXED
- Rights: TRAINING_ALLOWED | Split: train

**Q**: How many Sthanakavasi monasteries (upasaras) exist today?

**A**: What the corpus does say: "The following is the Canon of Scriptures held by the Jaina of Western India, together with brief notes as to their contents. Various sects and sub-sects differ very much with regard to the Chedagrantha, Mulagrantha and Payanna, but all Svetambara and Sthanakavasi practically agree with regard to the Anga and Upaiiga. They hold that originally there were Twelve Anga, but that one, the Dris'tivada A" (Notes on Modern Jainism (1910) (Mrs. Sinclair Stevenson, 1910)). The corpus does not record a count of Sthanakavasi monasteries, so this question cannot be answered from the available sources. Evidence needed first: a contemporary institutional survey.

**Evidence**: The following is the Canon of Scriptures held by the Jaina of Western India, together with brief notes as to their contents. Various sects and sub-sects differ very much with regard to the Chedagrantha, Mulagrantha and Payanna, but all Svetambara and Sthanakavasi practically agree with regard to the Anga and Upaiiga. They hold that originally there were Twelve Anga, but that one, the Dris'tivada A
**Source text**: The following is the Canon of Scriptures held by the Jaina of Western India, together with brief notes as to their contents. Various sects and sub-sects differ very much with regard to the Chedagrantha, Mulagrantha and Payanna, but all Svetambara and Sthanakavasi practically agree with regard to the Anga and Upaiiga. They hold that originally there were Twelve Anga, but that one, the Dris'tivada A
- Citation: [The following is the Canon of Scriptures held by the Jaina of Western India, together with brief notes as to their contents. Various sects and sub-sec](https://archive.org/details/notesonmodernjai00steviala)

---

### T61-CAND-0236 (pos 5)
- Category: ABSTENTION/INSUFFICIENT_EVIDENCE | Priority: abstention, no_fabrication, qa_alignment
- Source: Notes on Modern Jainism (1910) (SVK-0038)
- Sect: UNKNOWN (HIGH) | Layer: MIXED
- Rights: TRAINING_ALLOWED | Split: train

**Q**: How many verses does the Uttaradhyayana Sutra contain?

**A**: What the corpus does say: "2. Uttaradhyayana ( (§Tfti^<H ). A very famous and important book, containing the lives of eminent saints,. and teaching that a man is raised by his Karma and not his birth. It deals too with celibacy, discipline and character, and also records the advice given by Mahavira to his disciples two days before he entered Moksa. Its last chapters are devoted to an important and lengthy discussion on Sou" (Notes on Modern Jainism (1910) (Mrs. Sinclair Stevenson, 1910)). The corpus does not record a verse count for the Uttaradhyayana Sutra, so this question cannot be answered from the available sources. Evidence needed first: a metrical colophon or critical edition count.

**Evidence**: 2. Uttaradhyayana ( (§Tfti^<H ). A very famous and important book, containing the lives of eminent saints,. and teaching that a man is raised by his Karma and not his birth. It deals too with celibacy, discipline and character, and also records the advice given by Mahavira to his disciples two days before he entered Moksa. Its last chapters are devoted to an important and lengthy discussion on Sou
**Source text**: 2. Uttaradhyayana ( (§Tfti^<H ). A very famous and important book, containing the lives of eminent saints,. and teaching that a man is raised by his Karma and not his birth. It deals too with celibacy, discipline and character, and also records the advice given by Mahavira to his disciples two days before he entered Moksa. Its last chapters are devoted to an important and lengthy discussion on Sou
- Citation: [2. Uttaradhyayana ( (§Tfti^<H ). A very famous and important book, containing the lives of eminent saints,. and teaching that a man is raised by his K](https://archive.org/details/notesonmodernjai00steviala)

---

### T61-CAND-0237 (pos 6)
- Category: ABSTENTION/INSUFFICIENT_EVIDENCE | Priority: abstention, no_fabrication, qa_alignment
- Source: Notes on Modern Jainism (1910) (SVK-0038)
- Sect: UNKNOWN (HIGH) | Layer: MIXED
- Rights: TRAINING_ALLOWED | Split: train

**Q**: In which year was the Kalpa Sutra composed?

**A**: What the corpus does say: "Mahavira, the founder, or vas it would perhaps be more accurate to call him ) the reformer, of Jainism, was born about 599 B. c. His antagonism to Brahmanism was marked even before his birth, for we are told in one of the most famous of the Jaina sacred books, the Kalpa Sutra/ that his embryo was removed from the Brahmuni Devananda to the Ksatriyani Tris'ala." (Notes on Modern Jainism (1910) (Mrs. Sinclair Stevenson, 1910)). The corpus does not record a composition year for the Kalpa Sutra, so this question cannot be answered from the available sources. Evidence needed first: a dated composition record.

**Evidence**: Mahavira, the founder, or vas it would perhaps be more accurate to call him ) the reformer, of Jainism, was born about 599 B. c. His antagonism to Brahmanism was marked even before his birth, for we are told in one of the most famous of the Jaina sacred books, the Kalpa Sutra/ that his embryo was removed from the Brahmuni Devananda to the Ksatriyani Tris'ala.
**Source text**: Mahavira, the founder, or vas it would perhaps be more accurate to call him ) the reformer, of Jainism, was born about 599 B. c. His antagonism to Brahmanism was marked even before his birth, for we are told in one of the most famous of the Jaina sacred books, the Kalpa Sutra/ that his embryo was removed from the Brahmuni Devananda to the Ksatriyani Tris'ala.
- Citation: [Mahavira, the founder, or vas it would perhaps be more accurate to call him ) the reformer, of Jainism, was born about 599 B. c. His antagonism to Bra](https://archive.org/details/notesonmodernjai00steviala)

---

### T61-CAND-0239 (pos 7)
- Category: ABSTENTION/INSUFFICIENT_EVIDENCE | Priority: abstention, no_fabrication, qa_alignment
- Source: Notes on Modern Jainism (1910) (SVK-0038)
- Sect: UNKNOWN (HIGH) | Layer: MIXED
- Rights: TRAINING_ALLOWED | Split: train

**Q**: How many Jains live in Gujarat according to official statistics?

**A**: What the corpus does say: "THESE notes on Jain ism have been compiled mainly from information supplied to me by Gujarati speaking Jaina, so it has seemed advisable to use the Gujarati forms of their technical terms." (Notes on Modern Jainism (1910) (Mrs. Sinclair Stevenson, 1910)). The corpus does not record a Jain population figure for Gujarat, so this question cannot be answered from the available sources. Evidence needed first: a state census tabulation.

**Evidence**: THESE notes on Jain ism have been compiled mainly from information supplied to me by Gujarati speaking Jaina, so it has seemed advisable to use the Gujarati forms of their technical terms.
**Source text**: THESE notes on Jain ism have been compiled mainly from information supplied to me by Gujarati speaking Jaina, so it has seemed advisable to use the Gujarati forms of their technical terms.
- Citation: [THESE notes on Jain ism have been compiled mainly from information supplied to me by Gujarati speaking Jaina, so it has seemed advisable to use the Gu](https://archive.org/details/notesonmodernjai00steviala)

---

### T61-CAND-0240 (pos 8)
- Category: ABSTENTION/INSUFFICIENT_EVIDENCE | Priority: abstention, no_fabrication, qa_alignment
- Source: Notes on Modern Jainism (1910) (SVK-0038)
- Sect: UNKNOWN (HIGH) | Layer: MIXED
- Rights: TRAINING_ALLOWED | Split: train

**Q**: Is the Dṛṣṭivāda (Drastivada) Agam text available in this corpus?

**A**: What the corpus does say: "His father Siddhartha was a petty Raja, the head of the Ksatriya clan of the Nata, who lived in Kollaga, a suburb of Vaisali ( the modern Besar ;, about 27 miles north of Patna. Dr. Hoernlet gives a most interesting account of the government of this place, which seems to have been a sort of oligarchic republic ; " its government was vested in a Senate, composed of the heads of the resident Ksatriy" (Notes on Modern Jainism (1910) (Mrs. Sinclair Stevenson, 1910)). The corpus does not record any Dṛṣṭivāda text, so this question cannot be answered from the available sources. Evidence needed first: a Dṛṣṭivāda source with text.

**Evidence**: His father Siddhartha was a petty Raja, the head of the Ksatriya clan of the Nata, who lived in Kollaga, a suburb of Vaisali ( the modern Besar ;, about 27 miles north of Patna. Dr. Hoernlet gives a most interesting account of the government of this place, which seems to have been a sort of oligarchic republic ; " its government was vested in a Senate, composed of the heads of the resident Ksatriy
**Source text**: His father Siddhartha was a petty Raja, the head of the Ksatriya clan of the Nata, who lived in Kollaga, a suburb of Vaisali ( the modern Besar ;, about 27 miles north of Patna. Dr. Hoernlet gives a most interesting account of the government of this place, which seems to have been a sort of oligarchic republic ; " its government was vested in a Senate, composed of the heads of the resident Ksatriy
- Citation: [His father Siddhartha was a petty Raja, the head of the Ksatriya clan of the Nata, who lived in Kollaga, a suburb of Vaisali ( the modern Besar ;, abo](https://archive.org/details/notesonmodernjai00steviala)

---

### T61-CAND-0241 (pos 9)
- Category: ABSTENTION/INSUFFICIENT_EVIDENCE | Priority: abstention, no_fabrication, qa_alignment
- Source: Notes on Modern Jainism (1910) (SVK-0038)
- Sect: UNKNOWN (HIGH) | Layer: MIXED
- Rights: TRAINING_ALLOWED | Split: train

**Q**: Does this corpus contain the original Prakrit text of the Acharanga Sutra?

**A**: What the corpus does say: "* For the comparison of Jainism with Buddhism generally see Jacobi's Introduction to the Jaina Sutras, S. B. E. xxii. pp. xix if. t Acaranga Sutra. S. B. E. Vol. xxii. p. 202. £ Cp. Bombay Gazetteer. Vol. ix. Part i. p. 99." (Notes on Modern Jainism (1910) (Mrs. Sinclair Stevenson, 1910)). The corpus does not record an original-language Acharanga source, so this question cannot be answered from the available sources. Evidence needed first: a Prakrit Acharanga source in the manifest/corpus.

**Evidence**: * For the comparison of Jainism with Buddhism generally see Jacobi's Introduction to the Jaina Sutras, S. B. E. xxii. pp. xix if. t Acaranga Sutra. S. B. E. Vol. xxii. p. 202. £ Cp. Bombay Gazetteer. Vol. ix. Part i. p. 99.
**Source text**: * For the comparison of Jainism with Buddhism generally see Jacobi's Introduction to the Jaina Sutras, S. B. E. xxii. pp. xix if. t Acaranga Sutra. S. B. E. Vol. xxii. p. 202. £ Cp. Bombay Gazetteer. Vol. ix. Part i. p. 99.
- Citation: [* For the comparison of Jainism with Buddhism generally see Jacobi's Introduction to the Jaina Sutras, S. B. E. xxii. pp. xix if. t Acaranga Sutra. S.](https://archive.org/details/notesonmodernjai00steviala)

---

### T61-CAND-0242 (pos 10)
- Category: ABSTENTION/INSUFFICIENT_EVIDENCE | Priority: abstention, no_fabrication, qa_alignment
- Source: Pratikraman - Observance of Self Reflection (SVK-2024)
- Sect: UNKNOWN (MEDIUM) | Layer: REFERENCE
- Rights: TRAINING_ALLOWED_WITH_PERMISSION_EVIDENCE | Split: validation

**Q**: What is the exact publication year of the JainQQ Pratikraman guide by Pravin K. Shah?

**A**: The corpus does not record a publication year for the JainQQ Pratikraman guide, so this question cannot be answered from the available sources. Evidence needed first: a dated imprint for that source.

- Citation: [](https://jainqq.org/explore/200026)
**Rights flags**: MANIFEST_RIGHTS_STALE: manifest training_permission='NEEDS_PERMISSION (R93_RESTRICTIVE_TERMS)' but permission evidence file reports PERMISSION_GRANTED

---

### T61-CAND-0243 (pos 11)
- Category: ABSTENTION/INSUFFICIENT_EVIDENCE | Priority: abstention, no_fabrication, qa_alignment
- Source: Sthanakvasi Jain Itihas (SVK-2027)
- Sect: STHANAKAVASI (HIGH) | Layer: MIXED
- Rights: TRAINING_ALLOWED_WITH_PERMISSION_EVIDENCE | Split: test

**Q**: What is the exact publication year of the Sthanakvasi Jain Itihas volume?

**A**: The corpus does not record a publication year for the Sthanakvasi Jain Itihas volume, so this question cannot be answered from the available sources. Evidence needed first: a dated imprint for that source.

- Citation: [](https://jainqq.org/explore/020753)
**Rights flags**: MANIFEST_RIGHTS_STALE: manifest training_permission='NEEDS_PERMISSION (R93_RESTRICTIVE_TERMS)' but permission evidence file reports PERMISSION_GRANTED

---

### T61-CAND-0244 (pos 12)
- Category: ABSTENTION/INSUFFICIENT_EVIDENCE | Priority: abstention, no_fabrication, qa_alignment
- Source: Agam 12 Upang 01 Aupapatik Sutra Sthanakvasi (SVK-2029)
- Sect: STHANAKAVASI (HIGH) | Layer: CANONICAL_SCRIPTURE
- Rights: TRAINING_ALLOWED_WITH_PERMISSION_EVIDENCE | Split: test

**Q**: What is the exact publication year of the Aupapatik Sutra JainQQ edition?

**A**: The corpus does not record a publication year for the Aupapatik Sutra JainQQ edition, so this question cannot be answered from the available sources. Evidence needed first: a dated imprint for that source.

- Citation: [](https://jainqq.org/explore/002910)
**Rights flags**: MANIFEST_RIGHTS_STALE: manifest training_permission='NEEDS_PERMISSION (R93_RESTRICTIVE_TERMS)' but permission evidence file reports PERMISSION_GRANTED

---

### T61-CAND-0245 (pos 13)
- Category: ABSTENTION/INSUFFICIENT_EVIDENCE | Priority: abstention, no_fabrication, qa_alignment
- Source: Jaina Psychology (1929) (SVK-1006)
- Sect: UNKNOWN (UNKNOWN) | Layer: SECONDARY_SCHOLARSHIP
- Rights: TRAINING_ALLOWED | Split: train

**Q**: Who wrote the work titled 'Jaina Psychology'?

**A**: The corpus does not record an author name for 'Jaina Psychology', so this question cannot be answered from the available sources. Evidence needed first: a title page or bibliographic record naming the author.

- Citation: [](https://archive.org/details/jaina-psychology)

---

### T61-CAND-0246 (pos 14)
- Category: ABSTENTION/INSUFFICIENT_EVIDENCE | Priority: abstention, no_fabrication, qa_alignment
- Source: Notes on the Jainas (1911) (SVK-1008)
- Sect: MULTI_TRADITION (UNKNOWN) | Layer: SECONDARY_SCHOLARSHIP
- Rights: TRAINING_ALLOWED | Split: train

**Q**: Who wrote 'Notes on the Jainas' (1911)?

**A**: The corpus does not record an author name for 'Notes on the Jainas', so this question cannot be answered from the available sources. Evidence needed first: a bibliographic record naming the author.

- Citation: [](https://archive.org/details/in.gov.ignca.19947)

---

### T61-CAND-0247 (pos 15)
- Category: ABSTENTION/INSUFFICIENT_EVIDENCE | Priority: abstention, no_fabrication, qa_alignment
- Source: Shri Utradhyayan Sutar (Agam Seva) (1920) (SVK-0016)
- Sect: UNKNOWN (UNKNOWN) | Layer: CANONICAL_SCRIPTURE
- Rights: TRAINING_ALLOWED | Split: train

**Q**: Who compiled 'Shri Utradhyayan Sutar' (1920)?

**A**: The corpus does not record a compiler name for 'Shri Utradhyayan Sutar', so this question cannot be answered from the available sources. Evidence needed first: a title page naming the compiler.

- Citation: [](https://archive.org/details/in.ernet.dli.2015.545305)

---

### T61-CAND-0248 (pos 16)
- Category: ABSTENTION/INSUFFICIENT_EVIDENCE | Priority: abstention, no_fabrication, qa_alignment
- Source: Jain Shvetambar Conference Herald, Varsh 13 (1917) (SVK-1010)
- Sect: UNKNOWN (UNKNOWN) | Layer: MIXED
- Rights: TRAINING_ALLOWED | Split: train

**Q**: Who is the author of the Jain Shvetambar Conference Herald, Varsh 13?

**A**: The corpus does not record an author for the Herald, so this question cannot be answered from the available sources. Evidence needed first: a masthead naming the author.

- Citation: [](https://archive.org/details/in.ernet.dli.2015.543343)

---

### T61-CAND-0249 (pos 17)
- Category: ABSTENTION/INSUFFICIENT_EVIDENCE | Priority: abstention, no_fabrication, qa_alignment
- Source: Notes on Modern Jainism (1910) (SVK-0038)
- Sect: UNKNOWN (HIGH) | Layer: MIXED
- Rights: TRAINING_ALLOWED | Split: train

**Q**: Does the Sthanakavasi tradition permit idol worship in temples?

**A**: What the corpus does say: "in Ahmedabad a certain Svetambara Jaina* was asked to copy certain sacred Svetambara books, and whilst making the close study of them necessary for the work, he realized that there was no mention of idolatry in thern. He eventually founded a reformed and non-idolatrous sectt which rejects any of the Svetambara Scriptures that treat of idols or idol worship, and allows the common people. to read th" (Notes on Modern Jainism (1910) (Mrs. Sinclair Stevenson, 1910)). The corpus does not record a stated Sthanakavasi position on idol worship, so this question cannot be answered from the available sources. Evidence needed first: a passage stating that position.

**Evidence**: in Ahmedabad a certain Svetambara Jaina* was asked to copy certain sacred Svetambara books, and whilst making the close study of them necessary for the work, he realized that there was no mention of idolatry in thern. He eventually founded a reformed and non-idolatrous sectt which rejects any of the Svetambara Scriptures that treat of idols or idol worship, and allows the common people. to read th
**Source text**: in Ahmedabad a certain Svetambara Jaina* was asked to copy certain sacred Svetambara books, and whilst making the close study of them necessary for the work, he realized that there was no mention of idolatry in thern. He eventually founded a reformed and non-idolatrous sectt which rejects any of the Svetambara Scriptures that treat of idols or idol worship, and allows the common people. to read th
- Citation: [in Ahmedabad a certain Svetambara Jaina* was asked to copy certain sacred Svetambara books, and whilst making the close study of them necessary for th](https://archive.org/details/notesonmodernjai00steviala)

---

### T61-CAND-0250 (pos 18)
- Category: ABSTENTION/INSUFFICIENT_EVIDENCE | Priority: abstention, no_fabrication, qa_alignment
- Source: Notes on Modern Jainism (1910) (SVK-0038)
- Sect: UNKNOWN (HIGH) | Layer: MIXED
- Rights: TRAINING_ALLOWED | Split: train

**Q**: How many years did Mahavira undertake penance before enlightenment?

**A**: What the corpus does say: "Mahavira, the founder, or vas it would perhaps be more accurate to call him ) the reformer, of Jainism, was born about 599 B. c. His antagonism to Brahmanism was marked even before his birth, for we are told in one of the most famous of the Jaina sacred books, the Kalpa Sutra/ that his embryo was removed from the Brahmuni Devananda to the Ksatriyani Tris'ala." (Notes on Modern Jainism (1910) (Mrs. Sinclair Stevenson, 1910)). The corpus does not record a duration for Mahavira's final penance, so this question cannot be answered from the available sources. Evidence needed first: a canonical passage giving the duration.

**Evidence**: Mahavira, the founder, or vas it would perhaps be more accurate to call him ) the reformer, of Jainism, was born about 599 B. c. His antagonism to Brahmanism was marked even before his birth, for we are told in one of the most famous of the Jaina sacred books, the Kalpa Sutra/ that his embryo was removed from the Brahmuni Devananda to the Ksatriyani Tris'ala.
**Source text**: Mahavira, the founder, or vas it would perhaps be more accurate to call him ) the reformer, of Jainism, was born about 599 B. c. His antagonism to Brahmanism was marked even before his birth, for we are told in one of the most famous of the Jaina sacred books, the Kalpa Sutra/ that his embryo was removed from the Brahmuni Devananda to the Ksatriyani Tris'ala.
- Citation: [Mahavira, the founder, or vas it would perhaps be more accurate to call him ) the reformer, of Jainism, was born about 599 B. c. His antagonism to Bra](https://archive.org/details/notesonmodernjai00steviala)

---

### T61-CAND-0251 (pos 19)
- Category: ABSTENTION/INSUFFICIENT_EVIDENCE | Priority: abstention, no_fabrication, qa_alignment
- Source: Gaina Sutras (Sacred Books of the East): Acaranga and Sutrakrtanga (SVK-1001)
- Sect: SVETAMBARA (LOW) | Layer: CANONICAL_SCRIPTURE
- Rights: TRAINING_ALLOWED | Split: train

**Q**: What is the total number of pages in the source titled 'Aupapatik Sutra'?

**A**: What the corpus does say: "3 The same passage occurs in the Aupapatika Sutra (ed. Leu- mann, § 87), but without an indication that it is not complete." (Gaina Sutras (Sacred Books of the East): Acaranga and Sutrakrtanga (Hermann Jacobi (translator), 1884)). The corpus does not record a page count for that source, so this question cannot be answered from the available sources. Evidence needed first: a collation record.

**Evidence**: 3 The same passage occurs in the Aupapatika Sutra (ed. Leu- mann, § 87), but without an indication that it is not complete.
**Source text**: 3 The same passage occurs in the Aupapatika Sutra (ed. Leu- mann, § 87), but without an indication that it is not complete.
- Citation: [3 The same passage occurs in the Aupapatika Sutra (ed. Leu- mann, § 87), but without an indication that it is not complete.](https://archive.org/details/gainastras01aco)

---

### T61-CAND-0252 (pos 20)
- Category: ABSTENTION/INSUFFICIENT_EVIDENCE | Priority: abstention, no_fabrication, qa_alignment
- Source: Notes on the Religious Literature of India (1920) (SVK-1005)
- Sect: MULTI_TRADITION (UNKNOWN) | Layer: SECONDARY_SCHOLARSHIP
- Rights: TRAINING_ALLOWED | Split: train

**Q**: Which modern Jain organisation is the largest by membership?

**A**: What the corpus does say: "§ 23. There are a number of hymns in the tenth book of the Rik^ which seem to have been taught in the schools with a view to being used in the contests of wit which closed the sacrifices. There are two collections of riddles, and about a dozen dialogues ; but the largest and most interesting group are speculative pieces springing from the new religious situation. One is a hymn in praise of faith, " (Notes on the Religious Literature of India (1920) (J. N. Farquhar, 1920)). The corpus does not record any membership ranking of Jain organisations, so this question cannot be answered from the available sources. Evidence needed first: a comparative membership study.

**Evidence**: § 23. There are a number of hymns in the tenth book of the Rik^ which seem to have been taught in the schools with a view to being used in the contests of wit which closed the sacrifices. There are two collections of riddles, and about a dozen dialogues ; but the largest and most interesting group are speculative pieces springing from the new religious situation. One is a hymn in praise of faith, 
**Source text**: § 23. There are a number of hymns in the tenth book of the Rik^ which seem to have been taught in the schools with a view to being used in the contests of wit which closed the sacrifices. There are two collections of riddles, and about a dozen dialogues ; but the largest and most interesting group are speculative pieces springing from the new religious situation. One is a hymn in praise of faith, 
- Citation: [§ 23. There are a number of hymns in the tenth book of the Rik^ which seem to have been taught in the schools with a view to being used in the contest](https://archive.org/details/anoutlinereligi00farqgoog)

---

### T61-CAND-0253 (pos 21)
- Category: ABSTENTION/INSUFFICIENT_EVIDENCE | Priority: abstention, no_fabrication, qa_alignment
- Source: Gaina Sutras (Sacred Books of the East): Acaranga and Sutrakrtanga (SVK-1001)
- Sect: SVETAMBARA (LOW) | Layer: CANONICAL_SCRIPTURE
- Rights: TRAINING_ALLOWED | Split: train

**Q**: What is the exact date of Mahavira's nirvana?

**A**: What the corpus does say: "1 These twelve years of penance were indeed always thought essential for obtaining perfection, and every ascetic who endeavours to quit this life with the best claims to enter one of the highest heavens, or even Nirvana, has to undergo a similar course of preparatory penance, which lasts twelve years." (Gaina Sutras (Sacred Books of the East): Acaranga and Sutrakrtanga (Hermann Jacobi (translator), 1884)). The corpus does not record an exact dated record of Mahavira's nirvana in this corpus, so this question cannot be answered from the available sources. Evidence needed first: a dated record.

**Evidence**: 1 These twelve years of penance were indeed always thought essential for obtaining perfection, and every ascetic who endeavours to quit this life with the best claims to enter one of the highest heavens, or even Nirvana, has to undergo a similar course of preparatory penance, which lasts twelve years.
**Source text**: 1 These twelve years of penance were indeed always thought essential for obtaining perfection, and every ascetic who endeavours to quit this life with the best claims to enter one of the highest heavens, or even Nirvana, has to undergo a similar course of preparatory penance, which lasts twelve years.
- Citation: [1 These twelve years of penance were indeed always thought essential for obtaining perfection, and every ascetic who endeavours to quit this life with](https://archive.org/details/gainastras01aco)

---

### T61-CAND-0254 (pos 22)
- Category: ABSTENTION/INSUFFICIENT_EVIDENCE | Priority: abstention, no_fabrication, qa_alignment
- Source: Notes on Modern Jainism (1910) (SVK-0038)
- Sect: UNKNOWN (HIGH) | Layer: MIXED
- Rights: TRAINING_ALLOWED | Split: train

**Q**: What is the population of Jain monks and nuns today?

**A**: What the corpus does say: "THESE notes on Jain ism have been compiled mainly from information supplied to me by Gujarati speaking Jaina, so it has seemed advisable to use the Gujarati forms of their technical terms." (Notes on Modern Jainism (1910) (Mrs. Sinclair Stevenson, 1910)). The corpus does not record a current count of Jain monks and nuns, so this question cannot be answered from the available sources. Evidence needed first: a contemporary ordination census.

**Evidence**: THESE notes on Jain ism have been compiled mainly from information supplied to me by Gujarati speaking Jaina, so it has seemed advisable to use the Gujarati forms of their technical terms.
**Source text**: THESE notes on Jain ism have been compiled mainly from information supplied to me by Gujarati speaking Jaina, so it has seemed advisable to use the Gujarati forms of their technical terms.
- Citation: [THESE notes on Jain ism have been compiled mainly from information supplied to me by Gujarati speaking Jaina, so it has seemed advisable to use the Gu](https://archive.org/details/notesonmodernjai00steviala)

---
