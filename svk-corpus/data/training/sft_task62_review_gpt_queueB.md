# TASK 62 SFT REVIEW — Queue B
**Queue**: QUEUE B - STHANAKAVASI DISTINCTION
**Reason**: Task 60: sect_confusion cases 1 -> 4; category keyterm -0.25.
**Candidates**: 20

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

### T61-CAND-0041 (pos 1)
- Category: STHANAKAVASI_DISTINCTION | Priority: qa_alignment, sect_distinction, source_grounding
- Source: Notes on Modern Jainism (1910) (SVK-0038)
- Sect: UNKNOWN (HIGH) | Layer: MIXED
- Rights: TRAINING_ALLOWED | Split: train

**Q**: How do Sthanakavasi Jains differ from Svetambara Jains on chedagrantha according to Notes on Modern Jainism (1910) (Mrs. Sinclair Stevenson, 1910)?

**A**: On chedagrantha, Notes on Modern Jainism (1910) (Mrs. Sinclair Stevenson, 1910) states: "but all Svetambara and Sthanakavasi practically agree" This is that source's account (manifest scope HIGH_STHANAKAVASI_RELEVANCE); other Jain traditions may describe the same point differently, and this passage does not say so.

**Evidence**: but all Svetambara and Sthanakavasi practically agree
**Source text**: The following is the Canon of Scriptures held by the
Jaina of Western India, together with brief notes as to
their contents. Various sects and sub-sects differ very much
with regard to the Chedagrantha, Mulagrantha and Payanna,
but all Svetambara and Sthanakavasi practically agree
with regard to the Anga and Upaiiga. They hold that
originally there were Twelve Anga, but that one, the
Dris'tivada A...
- Citation: [but all Svetambara and Sthanakavasi practically agree](https://archive.org/details/notesonmodernjai00steviala)

---

### T61-CAND-0042 (pos 2)
- Category: STHANAKAVASI_DISTINCTION | Priority: qa_alignment, sect_distinction, source_grounding
- Source: Notes on Modern Jainism (1910) (SVK-0038)
- Sect: UNKNOWN (HIGH) | Layer: MIXED
- Rights: TRAINING_ALLOWED | Split: train

**Q**: What difference between Sthanakavasi and Svetambara practice regarding scriptures does Notes on Modern Jainism (1910) (Mrs. Sinclair Stevenson, 1910) describe?

**A**: On scriptures, Notes on Modern Jainism (1910) (Mrs. Sinclair Stevenson, 1910) states: "Sthanakavasi do not thus restrict the use of the scriptures," This is that source's account (manifest scope HIGH_STHANAKAVASI_RELEVANCE); other Jain traditions may describe the same point differently, and this passage does not say so.

**Evidence**: Sthanakavasi do not thus restrict the use of the scriptures,
**Source text**: As we have already seen, the Svetambara hardly ever
allow their books to be read by laymen, and although the
Sthanakavasi do not thus restrict the use of the scriptures,
even they do not like the laity to see these four books,
which, they say, are meant for monks only.
- Citation: [Sthanakavasi do not thus restrict the use of the scriptures,](https://archive.org/details/notesonmodernjai00steviala)
**Near dups**: 3

---

### T61-CAND-0043 (pos 3)
- Category: STHANAKAVASI_DISTINCTION | Priority: qa_alignment, sect_distinction, source_grounding
- Source: Notes on Modern Jainism (1910) (SVK-0038)
- Sect: UNKNOWN (HIGH) | Layer: MIXED
- Rights: TRAINING_ALLOWED | Split: train

**Q**: In Notes on Modern Jainism (1910) (Mrs. Sinclair Stevenson, 1910), what is said about mulagrantha for Sthanakavasi Jains as distinct from Svetambara Jains?

**A**: On mulagrantha, Notes on Modern Jainism (1910) (Mrs. Sinclair Stevenson, 1910) states: "Of these four the Sthanakavasi accept only the first" This is that source's account (manifest scope HIGH_STHANAKAVASI_RELEVANCE); other Jain traditions may describe the same point differently, and this passage does not say so.

**Evidence**: Of these four the Sthanakavasi accept only the first
**Source text**: Of these four the Sthanakavasi accept only the first
two as Mulagrantha and consider the A'vas'yaka to be not
a Mulagrantha but the last of all the scriptures.
- Citation: [Of these four the Sthanakavasi accept only the first](https://archive.org/details/notesonmodernjai00steviala)

---

### T61-CAND-0044 (pos 4)
- Category: STHANAKAVASI_DISTINCTION | Priority: qa_alignment, sect_distinction, source_grounding
- Source: Notes on Modern Jainism (1910) (SVK-0038)
- Sect: UNKNOWN (HIGH) | Layer: MIXED
- Rights: TRAINING_ALLOWED | Split: train

**Q**: How do Sthanakavasi Jains differ from Svetambara Jains on ascetics according to Notes on Modern Jainism (1910) (Mrs. Sinclair Stevenson, 1910)?

**A**: On ascetics, Notes on Modern Jainism (1910) (Mrs. Sinclair Stevenson, 1910) states: "strings, and when lay people talk to Sthanakavasi ascetics" This is that source's account (manifest scope HIGH_STHANAKAVASI_RELEVANCE); other Jain traditions may describe the same point differently, and this passage does not say so.

**Evidence**: strings, and when lay people talk to Sthanakavasi ascetics
**Source text**: piece of cloth to wear over his mouth. A Sthanakavasi
sadhu must keep his mouth covered night and day, so he
wears this mouth cloth or mumati ( >j>lcfl )* tied on with
strings, and when lay people talk to Sthanakavasi ascetics
they must cover their mouths. It is sufficient for the Sve-
tambara sadhus to keep their mouth cloth in their hands.
- Citation: [strings, and when lay people talk to Sthanakavasi ascetics](https://archive.org/details/notesonmodernjai00steviala)
**Near dups**: 1

---

### T61-CAND-0045 (pos 5)
- Category: STHANAKAVASI_DISTINCTION | Priority: qa_alignment, sect_distinction, source_grounding
- Source: Notes on Modern Jainism (1910) (SVK-0038)
- Sect: UNKNOWN (HIGH) | Layer: MIXED
- Rights: TRAINING_ALLOWED | Split: train

**Q**: What difference between Sthanakavasi and Digambara practice regarding whisk does Notes on Modern Jainism (1910) (Mrs. Sinclair Stevenson, 1910) describe?

**A**: On whisk, Notes on Modern Jainism (1910) (Mrs. Sinclair Stevenson, 1910) states: "wool, and the Sthanakavasi, who sweep more carefully than" This is that source's account (manifest scope HIGH_STHANAKAVASI_RELEVANCE); other Jain traditions may describe the same point differently, and this passage does not say so.

**Evidence**: wool, and the Sthanakavasi, who sweep more carefully than
**Source text**: Besides his cloth the monk generally has a long rod,
which must not be hollow lest it should entrap and kill an
insect, and a brush (Rajono ^MQll)> which is used to protect
insects by sweeping them out of danger. Its whisk is of
wool, and the Sthanakavasi, who sweep more carefully than
the Svetambara, have a bigger brush with a longer handle-
The Digambara Sadhu who live in the jungle frequently
u...
- Citation: [wool, and the Sthanakavasi, who sweep more carefully than](https://archive.org/details/notesonmodernjai00steviala)

---

### T61-CAND-0046 (pos 6)
- Category: STHANAKAVASI_DISTINCTION | Priority: qa_alignment, sect_distinction, source_grounding
- Source: Notes on Modern Jainism (1910) (SVK-0038)
- Sect: UNKNOWN (HIGH) | Layer: MIXED
- Rights: TRAINING_ALLOWED | Split: train

**Q**: In Notes on Modern Jainism (1910) (Mrs. Sinclair Stevenson, 1910), what is said about new name for Sthanakavasi Jains as distinct from Digambara Jains?

**A**: On new name, Notes on Modern Jainism (1910) (Mrs. Sinclair Stevenson, 1910) states: "take a new name ; if he be a Sthanakavasi, however, he" This is that source's account (manifest scope HIGH_STHANAKAVASI_RELEVANCE); other Jain traditions may describe the same point differently, and this passage does not say so.

**Evidence**: take a new name ; if he be a Sthanakavasi, however, he
**Source text**: If the ascetic be a Digambara or Svetambara, he will
take a new name ; if he be a Sthanakavasi, however, he
will still retain his old one.
- Citation: [take a new name ; if he be a Sthanakavasi, however, he](https://archive.org/details/notesonmodernjai00steviala)

---

### T61-CAND-0047 (pos 7)
- Category: STHANAKAVASI_DISTINCTION | Priority: qa_alignment, sect_distinction, source_grounding
- Source: Notes on Modern Jainism (1910) (SVK-0038)
- Sect: UNKNOWN (HIGH) | Layer: MIXED
- Rights: TRAINING_ALLOWED | Split: train

**Q**: How do Sthanakavasi Jains differ from Svetambara Jains on food according to Notes on Modern Jainism (1910) (Mrs. Sinclair Stevenson, 1910)?

**A**: On food, Notes on Modern Jainism (1910) (Mrs. Sinclair Stevenson, 1910) states: "Neither a Svetambara nor a Sthanakavasi will accept" This is that source's account (manifest scope HIGH_STHANAKAVASI_RELEVANCE); other Jain traditions may describe the same point differently, and this passage does not say so.

**Evidence**: Neither a Svetambara nor a Sthanakavasi will accept
**Source text**: Neither a Svetambara nor a Sthanakavasi will accept
food taken to the Upasaro for them by a layman. The
Svetambara, however, will accept an invitation to go to
a layman's house in order to fetch food and to take it back
to the Upasaro ; this a Sthanakavasi will not do.
- Citation: [Neither a Svetambara nor a Sthanakavasi will accept](https://archive.org/details/notesonmodernjai00steviala)
**Near dups**: 1

---

### T61-CAND-0048 (pos 8)
- Category: STHANAKAVASI_DISTINCTION | Priority: qa_alignment, sect_distinction, source_grounding
- Source: Notes on Modern Jainism (1910) (SVK-0038)
- Sect: UNKNOWN (HIGH) | Layer: MIXED
- Rights: TRAINING_ALLOWED | Split: train

**Q**: What difference between Sthanakavasi and Svetambara practice regarding jaina ascetics. 39 does Notes on Modern Jainism (1910) (Mrs. Sinclair Stevenson, 1910) describe?

**A**: On jaina ascetics. 39, Notes on Modern Jainism (1910) (Mrs. Sinclair Stevenson, 1910) states: "Sthanakavasi ) friends assure me is unfortunately not the" This is that source's account (manifest scope HIGH_STHANAKAVASI_RELEVANCE); other Jain traditions may describe the same point differently, and this passage does not say so.

**Evidence**: Sthanakavasi ) friends assure me is unfortunately not the
**Source text**: In the Bombay Gazetteer* it is stated that the Dhun-
<lhia priests do not beg ; this however my Dhundhia ( i. e.
Sthanakavasi ) friends assure me is unfortunately not the
case.
- Citation: [Sthanakavasi ) friends assure me is unfortunately not the](https://archive.org/details/notesonmodernjai00steviala)
**Near dups**: 2

---

### T61-CAND-0049 (pos 9)
- Category: STHANAKAVASI_DISTINCTION | Priority: qa_alignment, sect_distinction, source_grounding
- Source: Notes on Modern Jainism (1910) (SVK-0038)
- Sect: UNKNOWN (HIGH) | Layer: MIXED
- Rights: TRAINING_ALLOWED | Split: train

**Q**: In Notes on Modern Jainism (1910) (Mrs. Sinclair Stevenson, 1910), what is said about age for marriage for Sthanakavasi Jains as distinct from Svetambara Jains?

**A**: On age for marriage, Notes on Modern Jainism (1910) (Mrs. Sinclair Stevenson, 1910) states: "the Sthanakavasi and Svetambara generally marry their" This is that source's account (manifest scope HIGH_STHANAKAVASI_RELEVANCE); other Jain traditions may describe the same point differently, and this passage does not say so.

**Evidence**: the Sthanakavasi and Svetambara generally marry their
**Source text**: The customary age for marriage differs with the sects :
the Sthanakavasi and Svetambara generally marry their
daughters at about fourteen or fifteen to boys of about
nineteen or twenty. There is however no special religious
sanction amongst them for any particular age.t
- Citation: [the Sthanakavasi and Svetambara generally marry their](https://archive.org/details/notesonmodernjai00steviala)

---

### T61-CAND-0050 (pos 10)
- Category: STHANAKAVASI_DISTINCTION | Priority: qa_alignment, sect_distinction, source_grounding
- Source: Notes on Modern Jainism (1910) (SVK-0038)
- Sect: UNKNOWN (HIGH) | Layer: MIXED
- Rights: TRAINING_ALLOWED | Split: train

**Q**: How do Sthanakavasi Jains differ from Digambara Jains on followed almost completely in the case according to Notes on Modern Jainism (1910) (Mrs. Sinclair Stevenson, 1910)?

**A**: On followed almost completely in the case, Notes on Modern Jainism (1910) (Mrs. Sinclair Stevenson, 1910) states: "Svetambara, Digambara and Sthanakavasi will all" This is that source's account (manifest scope HIGH_STHANAKAVASI_RELEVANCE); other Jain traditions may describe the same point differently, and this passage does not say so.

**Evidence**: Svetambara, Digambara and Sthanakavasi will all
**Source text**: Svetambara, Digambara and Sthanakavasi will all
intermarry if they are of the same caste. They will also
intermarry with Hindus of their own caste. Curiously
enough, certain Svetambara in Ahmedabad will intermarry,
but will not dine with, Sthanakavasi.
- Citation: [Svetambara, Digambara and Sthanakavasi will all](https://archive.org/details/notesonmodernjai00steviala)

---

### T61-CAND-0051 (pos 11)
- Category: STHANAKAVASI_DISTINCTION | Priority: qa_alignment, sect_distinction, source_grounding
- Source: Notes on Modern Jainism (1910) (SVK-0038)
- Sect: UNKNOWN (HIGH) | Layer: MIXED
- Rights: TRAINING_ALLOWED | Split: train

**Q**: What difference between Sthanakavasi and Svetambara practice regarding vow does Notes on Modern Jainism (1910) (Mrs. Sinclair Stevenson, 1910) describe?

**A**: On vow, Notes on Modern Jainism (1910) (Mrs. Sinclair Stevenson, 1910) states: "Sthanakavasi, as we have seen, say that it might be reached" This is that source's account (manifest scope HIGH_STHANAKAVASI_RELEVANCE); other Jain traditions may describe the same point differently, and this passage does not say so.

**Evidence**: Sthanakavasi, as we have seen, say that it might be reached
**Source text**: A monk who faithfully performs his vows, etc., can
reach this thirteenth stage. A layman could reach it, but
it would be very hard for him. The S'vetambara and
Sthanakavasi, as we have seen, say that it might be reached
by a woman, but it would be hardest of all for her. They
say that for every 108 men who attain Moksa, at most only
twenty women do so, and ten neuters.
- Citation: [Sthanakavasi, as we have seen, say that it might be reached](https://archive.org/details/notesonmodernjai00steviala)
**Near dups**: 4

---

### T61-CAND-0052 (pos 12)
- Category: STHANAKAVASI_DISTINCTION | Priority: qa_alignment, sect_distinction, source_grounding
- Source: Notes on Modern Jainism (1910) (SVK-0038)
- Sect: UNKNOWN (HIGH) | Layer: MIXED
- Rights: TRAINING_ALLOWED | Split: train

**Q**: In Notes on Modern Jainism (1910) (Mrs. Sinclair Stevenson, 1910), what is said about nine principles for Sthanakavasi Jains as distinct from Digambara Jains?

**A**: On nine principles, Notes on Modern Jainism (1910) (Mrs. Sinclair Stevenson, 1910) states: "The S'vetambara and Sthanakavasi believe that there" This is that source's account (manifest scope HIGH_STHANAKAVASI_RELEVANCE); other Jain traditions may describe the same point differently, and this passage does not say so.

**Evidence**: The S'vetambara and Sthanakavasi believe that there
**Source text**: The S'vetambara and Sthanakavasi believe that there
are nine principles of Jainism, Nava Tatva ( rft ^^ ) j the
Digambara hold that there are only seven.
- Citation: [The S'vetambara and Sthanakavasi believe that there](https://archive.org/details/notesonmodernjai00steviala)

---

### T61-CAND-0053 (pos 13)
- Category: STHANAKAVASI_DISTINCTION | Priority: qa_alignment, sect_distinction, source_grounding
- Source: Notes on Modern Jainism (1910) (SVK-0038)
- Sect: UNKNOWN (HIGH) | Layer: MIXED
- Rights: TRAINING_ALLOWED | Split: train

**Q**: How do Sthanakavasi Jains differ from Svetambara Jains on jain a worship. 99 according to Notes on Modern Jainism (1910) (Mrs. Sinclair Stevenson, 1910)?

**A**: On jain a worship. 99, Notes on Modern Jainism (1910) (Mrs. Sinclair Stevenson, 1910) states: "A Sthanakavasi Jaina layman, however, has most kindly" This is that source's account (manifest scope HIGH_STHANAKAVASI_RELEVANCE); other Jain traditions may describe the same point differently, and this passage does not say so.

**Evidence**: A Sthanakavasi Jaina layman, however, has most kindly
**Source text**: A Sthanakavasi Jaina layman, however, has most kindly
furnished me with the following particulars of their daily
religious duties.
- Citation: [A Sthanakavasi Jaina layman, however, has most kindly](https://archive.org/details/notesonmodernjai00steviala)

---

### T61-CAND-0054 (pos 14)
- Category: STHANAKAVASI_DISTINCTION | Priority: qa_alignment, sect_distinction, source_grounding
- Source: Notes on Modern Jainism (1910) (SVK-0038)
- Sect: UNKNOWN (HIGH) | Layer: MIXED
- Rights: TRAINING_ALLOWED | Split: train

**Q**: What difference between Sthanakavasi and Svetambara practice regarding ascetics does Notes on Modern Jainism (1910) (Mrs. Sinclair Stevenson, 1910) describe?

**A**: On ascetics, Notes on Modern Jainism (1910) (Mrs. Sinclair Stevenson, 1910) states: "wear the same dress, etc., as the Sthanakavasi Sadhu, but will" This is that source's account (manifest scope HIGH_STHANAKAVASI_RELEVANCE); other Jain traditions may describe the same point differently, and this passage does not say so.

**Evidence**: wear the same dress, etc., as the Sthanakavasi Sadhu, but will
**Source text**: They are recruited from all three sei-ts, though their founder was
a Sthfinakavasi, who about 150 years ago, in Sojat ( Marwar ),
entertained doubts about certain current practices, and founded a
sect of his own. They are called Terapantha, because the number
of Sadhus who joined was originally thirteen. Their ascetics
wear the same dress, etc., as the Sthanakavasi Sadhu, but will
not stay in an U...
- Citation: [wear the same dress, etc., as the Sthanakavasi Sadhu, but will](https://archive.org/details/notesonmodernjai00steviala)
**Near dups**: 4

---

### T61-CAND-0055 (pos 15)
- Category: STHANAKAVASI_DISTINCTION | Priority: qa_alignment, sect_distinction, source_grounding
- Source: Notes on Modern Jainism (1910) (SVK-0038)
- Sect: UNKNOWN (HIGH) | Layer: MIXED
- Rights: TRAINING_ALLOWED | Split: train

**Q**: In Notes on Modern Jainism (1910) (Mrs. Sinclair Stevenson, 1910), what is said about scriptures for Sthanakavasi Jains as distinct from Svetambara Jains?

**A**: On scriptures, Notes on Modern Jainism (1910) (Mrs. Sinclair Stevenson, 1910) states: "The Terapanthi accept the Sthanakavasi scriptures, but read" This is that source's account (manifest scope HIGH_STHANAKAVASI_RELEVANCE); other Jain traditions may describe the same point differently, and this passage does not say so.

**Evidence**: The Terapanthi accept the Sthanakavasi scriptures, but read
**Source text**: The Terapanthi accept the Sthanakavasi scriptures, but read
their own meaning into certain passages. They are not as particular
as other Jaina about protecting animal life, never for instance
interfering to save mice from cats, so the orthodox of all three
sects unite in condemning them.
- Citation: [The Terapanthi accept the Sthanakavasi scriptures, but read](https://archive.org/details/notesonmodernjai00steviala)
**Near dups**: 1

---

### T61-CAND-0056 (pos 16)
- Category: STHANAKAVASI_DISTINCTION | Priority: qa_alignment, sect_distinction, source_grounding
- Source: Notes on Modern Jainism (1910) (SVK-0038)
- Sect: UNKNOWN (HIGH) | Layer: MIXED
- Rights: TRAINING_ALLOWED | Split: train

**Q**: How do Sthanakavasi Jains differ from Svetambara Jains on scriptures according to Notes on Modern Jainism (1910) (Mrs. Sinclair Stevenson, 1910)?

**A**: On scriptures, Notes on Modern Jainism (1910) (Mrs. Sinclair Stevenson, 1910) states: "The Sthanakavasi Jaina, who do not accept the Kalpa" This is that source's account (manifest scope HIGH_STHANAKAVASI_RELEVANCE); other Jain traditions may describe the same point differently, and this passage does not say so.

**Evidence**: The Sthanakavasi Jaina, who do not accept the Kalpa
**Source text**: On the fasting days the SVetambara go to the Upasaro
to hear die Kalpa Sutra read hi Magadhi, the priest translat-
ing. The Sthanakavasi Jaina, who do not accept the Kalpa
Sutra, go to their own Upasaro and hear Mahavira's life read
in their own Scriptures. The members of all the sects go to
the Upasara as often as thev can, and some of them spend
"107
- Citation: [The Sthanakavasi Jaina, who do not accept the Kalpa](https://archive.org/details/notesonmodernjai00steviala)

---

### T61-CAND-0057 (pos 17)
- Category: STHANAKAVASI_DISTINCTION | Priority: qa_alignment, sect_distinction, source_grounding
- Source: Notes on Modern Jainism (1910) (SVK-0038)
- Sect: UNKNOWN (HIGH) | Layer: MIXED
- Rights: TRAINING_ALLOWED | Split: train

**Q**: What difference between Sthanakavasi and Svetambara practice regarding temple does Notes on Modern Jainism (1910) (Mrs. Sinclair Stevenson, 1910) describe?

**A**: On temple, Notes on Modern Jainism (1910) (Mrs. Sinclair Stevenson, 1910) states: "with greater zeal and attention than usual, but on this day every Jaina must do it. At the time of the ceremony all the temples are crowded ; in large towns the temples have separate buildings for men and women, and the Sthanakavasi have separate Upasara." This is that source's account (manifest scope HIGH_STHANAKAVASI_RELEVANCE); other Jain traditions may describe the same point differently, and this passage does not say so.

**Evidence**: with greater zeal and attention than usual, but on this day every Jaina must do it. At the time of the ceremony all the temples are crowded ; in large towns the temples have separate buildings for men and women, and the Sthanakavasi have separate Upasara.
**Source text**: with greater zeal and attention than usual, but on this
day every Jaina must do it. At the time of the ceremony
all the temples are crowded ; in large towns the temples
have separate buildings for men and women, and the
Sthanakavasi have separate Upasara.
- Citation: [with greater zeal and attention than usual, but on this day every Jaina must do it. At the time of the ceremony all the temples are crowded ; in large](https://archive.org/details/notesonmodernjai00steviala)
**Near dups**: 3

---

### T61-CAND-0058 (pos 18)
- Category: STHANAKAVASI_DISTINCTION | Priority: qa_alignment, sect_distinction, source_grounding
- Source: Notes on Modern Jainism (1910) (SVK-0038)
- Sect: UNKNOWN (HIGH) | Layer: MIXED
- Rights: TRAINING_ALLOWED | Split: train

**Q**: In Notes on Modern Jainism (1910) (Mrs. Sinclair Stevenson, 1910), what is said about scripture for Sthanakavasi Jains as distinct from Digambara Jains?

**A**: On scripture, Notes on Modern Jainism (1910) (Mrs. Sinclair Stevenson, 1910) states: "Devindathuo, 21. Dharma, 20. Dharm.1 Blmvana, 71. Dharmaniitha, 52, 98. Dharmastikaya, 60. Dhumra Prabha, 55. Dhundhia, see Sthanakavasi. Dhupa Puja, 103. Dhyan-, 36. Digambara (Janon, 14. Digambura .Scripture^, 2 1 ." This is that source's account (manifest scope HIGH_STHANAKAVASI_RELEVANCE); other Jain traditions may describe the same point differently, and this passage does not say so.

**Evidence**: Devindathuo, 21. Dharma, 20. Dharm.1 Blmvana, 71. Dharmaniitha, 52, 98. Dharmastikaya, 60. Dhumra Prabha, 55. Dhundhia, see Sthanakavasi. Dhupa Puja, 103. Dhyan-, 36. Digambara (Janon, 14. Digambura .Scripture^, 2 1 .
**Source text**: Devindathuo, 21.
Dharma, 20.
Dharm.1 Blmvana, 71.
Dharmaniitha, 52, 98.
Dharmastikaya, 60.
Dhumra Prabha, 55.
Dhundhia, see Sthanakavasi.
Dhupa Puja, 103.
Dhyan-, 36.
Digambara (Janon, 14.
Digambura .Scripture^, 2 1 .
- Citation: [Devindathuo, 21. Dharma, 20. Dharm.1 Blmvana, 71. Dharmaniitha, 52, 98. Dharmastikaya, 60. Dhumra Prabha, 55. Dhundhia, see Sthanakavasi. Dhupa Puja, ](https://archive.org/details/notesonmodernjai00steviala)
**Near dups**: 1

---

### T61-CAND-0059 (pos 19)
- Category: STHANAKAVASI_DISTINCTION | Priority: qa_alignment, sect_distinction, source_grounding
- Source: Notes on the Religious Literature of India (1920) (SVK-1005)
- Sect: MULTI_TRADITION (UNKNOWN) | Layer: SECONDARY_SCHOLARSHIP
- Rights: TRAINING_ALLOWED | Split: train

**Q**: How do Sthanakavasi Jains differ from Svetambara Jains on books according to Notes on the Religious Literature of India (1920) (J. N. Farquhar, 1920)?

**A**: On books, Notes on the Religious Literature of India (1920) (J. N. Farquhar, 1920) states: "stricter body called the Sthanakavasis arose in the seventeenth" This is that source's account (manifest scope CONTEXTUAL_JAIN with sect recorded as MULTI_TRADITION); other Jain traditions may describe the same point differently, and this passage does not say so.

**Evidence**: stricter body called the Sthanakavasis arose in the seventeenth
**Source text**: §438. In the fifteenth century, at Ahmadabad, where
Muhammadan influence was very powerful, a few Svetambaras
became convinced of the folly of image-worship and noted
that there is no mention of idols in the earliest Jain books.
They therefore formed a new sect called the Lohka or
Lumpaka, which gave up the temple-cult altogether. A
stricter body called the Sthanakavasis arose in the seventeenth
c...
- Citation: [stricter body called the Sthanakavasis arose in the seventeenth](https://archive.org/details/anoutlinereligi00farqgoog)

---

### T61-CAND-0060 (pos 20)
- Category: STHANAKAVASI_DISTINCTION | Priority: qa_alignment, sect_distinction, source_grounding
- Source: Agam 28 Mool 01 Aavashyak Sutra Sthanakvasi (SVK-2022)
- Sect: STHANAKAVASI (HIGH) | Layer: CANONICAL_SCRIPTURE
- Rights: TRAINING_ALLOWED_WITH_PERMISSION_EVIDENCE | Split: validation

**Q**: What difference between Sthanakavasi and Svetambara practice regarding worship does Agam 28 Mool 01 Aavashyak Sutra Sthanakvasi (Amarmuni, 2012) describe?

**A**: On worship, Agam 28 Mool 01 Aavashyak Sutra Sthanakvasi (Amarmuni, 2012) states: "zut Acharya Pravartak Shri Amar Muni jjuvAsAmi matthaeNa vedAmi The editor-in-chief of this Sutra, is a brilliant ascetic affliated with Shri Vardhaman Sthanakvasi Jain Shraman Sangh A great worshiper of the tenets of Jina and a devotee of his Guru, Shri Amar Muni Ji was born in a Malhotra family of Queta (Baluchistan) on Bhadva Sudi 5thin the year 1993V." This is that source's account (manifest scope STHANAKAVASI with sect recorded as STHANAKAVASI); other Jain traditions may describe the same point differently, and this passage does not say so.

**Evidence**: zut Acharya Pravartak Shri Amar Muni jjuvAsAmi matthaeNa vedAmi The editor-in-chief of this Sutra, is a brilliant ascetic affliated with Shri Vardhaman Sthanakvasi Jain Shraman Sangh A great worshiper of the tenets of Jina and a devotee of his Guru, Shri Amar Muni Ji was born in a Malhotra family of Queta (Baluchistan) on Bhadva Sudi 5thin the year 1993V.
**Source text**: citra vazyaka satra zruta AcArya pravartaka zrI amara muni LOTRATED VASHYAK SUTRA Shrut Acharya Pravartak Shri Amar Muni Ji M. zut Acharya Pravartak Shri Amar Muni jjuvAsAmi matthaeNa vedAmi The editor-in-chief of this Sutra, is a brilliant ascetic affliated with Shri Vardhaman Sthanakvasi Jain Shraman Sangh A great worshiper of the tenets of Jina and a devotee of his Guru, Shri Amar Muni Ji was b...
- Citation: [zut Acharya Pravartak Shri Amar Muni jjuvAsAmi matthaeNa vedAmi The editor-in-chief of this Sutra, is a brilliant ascetic affliated with Shri Vardhama](https://jainqq.org/explore/002489)
**Rights flags**: MANIFEST_RIGHTS_STALE: manifest training_permission='NEEDS_PERMISSION (R93_RESTRICTIVE_TERMS)' but permission evidence file reports PERMISSION_GRANTED

---
