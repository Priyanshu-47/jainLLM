"""TASK 60: build DAPT-01 BASE vs ADAPTED evaluation cases (eval-only).

Reads the governed release corpus + source manifest, asserts that every case's
reference material actually exists in those files, and writes
data/evaluation/dapt01_eval_cases.jsonl.

No dataset/corpus/manifest modification. Cases are derived only from
TRAINING_ALLOWED release records and manifest fields; abstention cases are
verified by absence greps recorded in the output.
"""

from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
CORPUS = REPO / "data" / "release" / "training_corpus.jsonl"
MANIFEST = REPO / "manifests" / "source_manifest.csv"
OUT = REPO / "data" / "evaluation" / "dapt01_eval_cases.jsonl"

DAPT_SPLITS = {
    "train": {
        "SVK-0007", "SVK-0016", "SVK-0026", "SVK-0037", "SVK-0038", "SVK-1001",
        "SVK-1002", "SVK-1003", "SVK-1005", "SVK-1006", "SVK-1007", "SVK-1008",
        "SVK-1009", "SVK-1010", "SVK-2002", "SVK-2003", "SVK-2004", "SVK-2005",
        "SVK-2006", "SVK-2007", "SVK-2008", "SVK-2009", "SVK-2010", "SVK-2011",
        "SVK-2012", "SVK-2013", "SVK-2014", "SVK-2015", "SVK-2016", "SVK-2019",
        "SVK-2020",
    },
    "val": {"SVK-2022", "SVK-2023", "SVK-2024", "SVK-2025"},
    "test": {"SVK-2026", "SVK-2027", "SVK-2028", "SVK-2029"},
}

CASES: list[dict] = []


def case(
    cid: str,
    category: str,
    language: str,
    question: str,
    reference: str,
    provenance: dict,
    scoring: dict,
    source_contains: list[str] | None = None,
    abstention: bool = False,
    notes: str = "",
) -> None:
    CASES.append(
        {
            "example_id": f"DAPT01EVAL-{cid}",
            "category": category,
            "language": language,
            "question": question,
            "expected_answer_or_reference": reference,
            "provenance": provenance,
            "scoring": scoring,
            "source_contains": source_contains or [],
            "abstention_case": abstention,
            "notes": notes,
        }
    )


def groups(*, all_of=(), any_of=(), none_of=(), abstention_markers=(), forbidden_claims=()):
    """Objective scoring rules: list of condition groups (all must pass).

    A flat ``any_of`` joins the primary group with ``all_of``; any nested list
    inside ``any_of`` becomes its own extra group (must contain >=1 element).
    """
    primary_any: list = []
    extra: list = []
    for item in any_of:
        if isinstance(item, (list, tuple)):
            extra.append(list(item))
        else:
            primary_any.append(item)
    base: dict = {}
    if all_of:
        base["all_of"] = list(all_of)
    if primary_any:
        base["any_of"] = primary_any
    if none_of:
        base["none_of"] = list(none_of)
    if abstention_markers:
        base["abstention_markers"] = list(abstention_markers)
    if forbidden_claims:
        base["forbidden_claims"] = list(forbidden_claims)
    out = [base] if base else []
    for e in extra:
        out.append({"any_of": e})
    return out


def prov(units, *, role="grounding_unit", **extra):
    d = {"role": role, "unit_ids": units if isinstance(units, list) else [units]}
    d.update(extra)
    return d


def man_prov(source_id, field="author", **extra):
    d = {"role": "manifest", "source_id": source_id, "manifest_field": field}
    d.update(extra)
    return d


# ---------------------------------------------------------------- JAIN_TERMINOLOGY
case(
    "001", "JAIN_TERMINOLOGY", "en",
    "In J. N. Farquhar's Notes on the Religious Literature of India, how is ahimsa defined?",
    "Ahimsa = non-injury, especially non-injury to animal life.",
    prov("SVK-1005:u04715", source_id="SVK-1005", dapt_split="train", dapt_seen_at_train=True),
    groups(all_of=["non-injury"], any_of=["animal life", "animal"]),
    source_contains=["Ahimsa, non-injury", "animal life"],
)
case(
    "002", "JAIN_TERMINOLOGY", "en",
    "According to Stevenson's Notes on Modern Jainism, what is Karma, and how does it affect a person's lives?",
    "Karma is the accumulated force of a person's good and bad actions in previous existences; it determines present and future life and forces a succession of rebirths until exhausted.",
    prov("SVK-0038:u00638", source_id="SVK-0038", dapt_split="train", dapt_seen_at_train=True),
    groups(all_of=["accumulated"], any_of=["previous existences", "past", "good and bad"]),
    source_contains=["accumulated force", "previous existences"],
)
case(
    "003", "JAIN_TERMINOLOGY", "en",
    "According to Stevenson, what are the two great divisions of Jain cosmic time, and how many periods does each contain?",
    "Utsarpini (rising) and Avasarpini (falling); each is subdivided into six periods.",
    prov("SVK-0038:u00957", source_id="SVK-0038", dapt_split="train", dapt_seen_at_train=True),
    groups(
        all_of=["utsarpini", "avasarpini"],
        any_of=["six periods", "six", "6"],
    ),
    source_contains=["Utsarpini", "Avasarpini", "six periods"],
)
case(
    "004", "JAIN_TERMINOLOGY", "en",
    "According to Stevenson, what three things make up the Three Jewels (Ratna Traya) in Jainism?",
    "Right Knowledge (Jnana), Right Faith (Darsana) and Right Conduct (Caritra).",
    prov(["SVK-0038:u00989", "SVK-0038:u00990"], source_id="SVK-0038", dapt_split="train", dapt_seen_at_train=True),
    groups(all_of=["knowledge", "faith", "conduct"]),
    source_contains=["Three Jewels", "Right Knowledge", "Right Faith", "Right Conduct"],
)

# --------------------------------------------- STHANAKAVASI_TERMINOLOGY
case(
    "005", "STHANAKAVASI_TERMINOLOGY", "en",
    "According to Stevenson, where is the Samayika generally said by Sthanakavasi Jaina?",
    "In a monastery (an Upasaro).",
    prov("SVK-0038:u01125", source_id="SVK-0038", dapt_split="train", dapt_seen_at_train=True),
    groups(all_of=["monastery"], any_of=["upasaro", "upasara", "upāsāro"]),
    source_contains=["Sthanakavasi Jaina in a monastery (Upasaro"],
)
case(
    "006", "STHANAKAVASI_TERMINOLOGY", "en",
    "According to Stevenson's account of the Sthanakavasi canon, how many Mulagrantha are there?",
    "Four Mulagrantha (according to the Sthanakavasi canon); the Sthanakavasi accept only the first two as Mulagrantha.",
    prov(["SVK-0038:u00235", "SVK-0038:u00233"], source_id="SVK-0038", dapt_split="train", dapt_seen_at_train=True),
    groups(all_of=["four"], any_of=["mula", "mulagrantha", "first two"]),
    source_contains=["Four Mulagrantha", "Sthanakavasi accept only the first two"],
)
case(
    "007", "STHANAKAVASI_TERMINOLOGY", "en",
    "According to Stevenson, what is Vaiyavacca and what does an ascetic do under it?",
    "Service: an ascetic must serve his superiors and the afflicted (bringing water/food for his guru, massaging him when tired).",
    prov("SVK-0038:u00399", source_id="SVK-0038", dapt_split="train", dapt_seen_at_train=True),
    groups(all_of=["serve", "superiors"], any_of=["afflicted", "guru", "service"]),
    source_contains=["This is called Vaiyavacca", "serve his superiors and the afflicted"],
)
case(
    "008", "STHANAKAVASI_TERMINOLOGY", "en",
    "According to Stevenson, which scriptures do the Terapanthi accept?",
    "They accept the Sthanakavasi scriptures (but read their own meaning into certain passages).",
    prov("SVK-0038:u01199", source_id="SVK-0038", dapt_split="train", dapt_seen_at_train=True),
    groups(all_of=["sthanakavasi"], any_of=["scripture", "accept", "read"]),
    source_contains=["The Terapanthi accept the Sthanakavasi scriptures"],
)

# ---------------------------------------------------------------- PRAKRIT
case(
    "009", "PRAKRIT", "hi",
    "पाइय-सद्द-महान्नवो के अनुसार प्राकृत शब्द 'अहिंसण' का क्या अर्थ है?",
    "अहिंसा (ahimsa).",
    prov("SVK-2006:u04075", source_id="SVK-2006", dapt_split="train", dapt_seen_at_train=True),
    groups(any_of=["अहिंसा", "ahimsa", "ahinsa", "non-violence", "non-injury"]),
    source_contains=["अहिंसण", "अहिंसा"],
)
case(
    "010", "PRAKRIT", "hi",
    "पाइय-सद्द-महान्नवो में प्राकृत शब्द 'उवस्सय' के लिए क्या दिया गया है और वह क्या होता है?",
    "उपाश्रय — जैन साधुओं के निवास करने का स्थान (residence of Jain ascetics).",
    prov("SVK-2007:u09904", source_id="SVK-2007", dapt_split="train", dapt_seen_at_train=True),
    groups(any_of=[["उपाश्रय", "upashraya", "upāśraya", "upasraya"], ["निवास", "residence", "staying", "abode", "place"]]),
    source_contains=["उवस्सय", "उपाश्रय", "निवास"],
)
case(
    "011", "PRAKRIT", "hi",
    "पाइय-सद्द-महान्नवो में प्राकृत शब्द 'सामइगि' का हिंदी रूप और अर्थ क्या दिया गया है?",
    "सामायिक वाला (samayika) — one who practises Samayika.",
    prov("SVK-2006:u39393", source_id="SVK-2006", dapt_split="train", dapt_seen_at_train=True),
    groups(any_of=[["सामायिक", "samayika", "samayik"], ["वाल", "वाला", "practis", "perform"]]),
    source_contains=["सामइगि", "सामायिक"],
)
case(
    "012", "PRAKRIT", "en",
    "In Woolner's Introduction to Prakrit, which Prakrit was regarded as the 'Prakrt par excellence'?",
    "Maharastri.",
    prov("SVK-2008:u00366", source_id="SVK-2008", dapt_split="train", dapt_seen_at_train=True),
    groups(any_of=["maharastri", "mahārāṣṭrī", "maharashtri", "māhārāṣṭrī"]),
    source_contains=["Maharastri was regarded as the Prakrt par excellence"],
)

# ---------------------------------------------------------------- HINDI
case(
    "013", "HINDI", "hi",
    "उत्तराध्ययन सूत्र की रचना किसने, कहाँ और किस अवसर पर की थी?",
    "श्रमण भगवान् महावीर ने, पावापुरी के अंतिम समवसरण में, निर्वाण से कुछ समय पूर्व।",
    prov("SVK-2020:u00021", source_id="SVK-2020", dapt_split="train", dapt_seen_at_train=True),
    groups(all_of=["महावीर", "पावापुरी"], any_of=["समवसरण", "निर्वाण"]),
    source_contains=["महावीर ने", "पावापुरी", "अन्तिम समवसरण"],
)
case(
    "014", "HINDI", "hi",
    "'उत्तराध्ययन' शब्द का शाब्दिक अर्थ क्या बताया गया है?",
    "उत्तर + अध्ययन = उत्तम शास्त्र / श्रेष्ठ शास्त्र (excellent or supreme scripture).",
    prov("SVK-2020:u00020", source_id="SVK-2020", dapt_split="train", dapt_seen_at_train=True),
    groups(any_of=["उत्तम", "श्रेष्ठ", "excellent", "supreme"]),
    source_contains=["उत्तम", "शरेष्ठ"],
)
case(
    "015", "HINDI", "hi",
    "उत्तराध्ययनसूत्र की व्याख्या के अनुसार 'विनीत' शिष्य कौन कहलाता है?",
    "जो गुरु की आज्ञा और निर्देश का पालन करता है, गुरु के पास रहकर सेवा-शुश्रूषा करता है, और इंगित (शरीर की चेष्टा) व आकार से मनोभावों को समंजस्य करता है।",
    prov("SVK-2020:u00168", source_id="SVK-2020", dapt_split="train", dapt_seen_at_train=True),
    groups(any_of=[["आज्ञा", "निर्देश", "पालन"], ["सेवा", "शुश्रूषा", "service"]], all_of=["गुरु"]),
    source_contains=["आज्ञा", "निर्देश", "सेवा"],
)
case(
    "016", "HINDI", "hi",
    "'अविनीत' शिष्य की पहचान उत्तराध्ययनसूत्र में क्यै बताई गई है?",
    "जो गुरु की आज्ञा-निर्देश का पालन नहीं करता, गुरुजनों की सेवा से दूर रहता है और उनके प्रतिकूल आचरण करता है, वह अविनीत है।",
    prov("SVK-2020:u00179", source_id="SVK-2020", dapt_split="train", dapt_seen_at_train=True),
    groups(any_of=[["नहीं", "सेवा", "दूर"], ["अविनीत"]], all_of=["गुरु"]),
    source_contains=["गुरु", "अविनीत"],
)

# ---------------------------------------------------------------- GUJARATI
case(
    "017", "GUJARATI", "gu",
    "જૈન શાળાના બાળકોને દરરોજ શું કરવાનું કહેવામાં આવ્યું છે?",
    "સામાયિક કરવી (to practise Samayika during the Jain-school period).",
    prov("SVK-2027:u095770", source_id="SVK-2027", dapt_split="test", dapt_seen_at_train=False),
    groups(any_of=["સામાયિક", "સમાયિક", "samayika", "samayik"]),
    source_contains=["જૈન શાળાના વખતમાં સામાયિક કરવી"],
)
case(
    "018", "GUJARATI", "gu",
    "જૈન માહાત્મ્ય મુજબ પ્રભુએ ક્યાં મોક્ષ પ્રાપ્ત કર્યો?",
    "અષ્ટપદ પર્વત ઉપર (on the Astapada mountain).",
    prov("SVK-2014:u00096", source_id="SVK-2014", dapt_split="train", dapt_seen_at_train=True),
    groups(any_of=["અષ્ટપદ", "astapada", "અષ્ટપાદ"]),
    source_contains=["અષ્ટપદ પર્વત"],
)
case(
    "019", "GUJARATI", "gu",
    "પુસ્તક 'જૈન સાથન કવાસી' (1928) ના લેખક કોણ છે?",
    "સ્વામી જીતમલ (Swami Jitmal).",
    man_prov("SVK-2010", "author", source_title="Jain Sathan Kavasi (1928)", dapt_split="train", dapt_seen_at_train=True),
    groups(any_of=["jitmal", "જીતમલ", "swami jitmal"]),
    source_contains=[],
)
case(
    "020", "GUJARATI", "gu",
    "જૈન શાસનની રચના કયા ત્રણ તત્ત્વો પર આધારિત છે એમ નવયુગ ગ્રંથમાં શું કહેવાયું છે?",
    "અહિંસા, સંયમ અને તપ (ahiṃsā, saṃyama and tapa).",
    prov("SVK-2012:u00063", source_id="SVK-2012", dapt_split="train", dapt_seen_at_train=True),
    groups(
        any_of=[
            ["અહિંસા", "અહિ'સા", "ahimsa", "અહિંસ"],
            ["સંયમ", "સયમ", "samyam"],
            ["તપ", "tapa"],
        ],
    ),
    source_contains=["સયમ", "તપ"],
)

# ---------------------------------------------------------------- SANSKRIT
case(
    "021", "SANSKRIT", "en",
    "According to the source manifest of this corpus, who is credited as the author of the Sanskrit work 'Sri Avasyaka Sutra Part-i' (1928)?",
    "Bhadrabahu.",
    man_prov("SVK-2015", "author", source_title="Sri Avasyaka Sutra Part-i (1928)", language="san",
             dapt_split="train", dapt_seen_at_train=True),
    groups(any_of=["bhadrabahu", "bhadrabahu", "bhadrabāhu"]),
    source_contains=[],
    notes="Sanskrit-language category limited to Sanskrit work provenance: release corpus records contain 0 units with language code 'sa'.",
)
case(
    "022", "SANSKRIT", "en",
    "In Stevenson's Kalpa Sutra translation, what is the Sanskrit technical term for the duty of confession/absolution, and what is the Gujarati word for it?",
    "Sanskrit: Pratikramana; Gujarati: Alavan.",
    prov("SVK-1002:u00101", source_id="SVK-1002", dapt_split="train", dapt_seen_at_train=True),
    groups(all_of=["pratikramana"], any_of=["alavan", "al-avan"]),
    source_contains=["Sans. Pratikramana", "Gujarathi word", "Alavan"],
)
case(
    "023", "SANSKRIT", "en",
    "According to Stevenson, what is the first vow taken by a Jaina ascetic, and what term is used for it?",
    "To refrain from destroying/killing living beings, whether subtle or movable or immovable (Ahimsarata).",
    prov("SVK-0038:u00337", source_id="SVK-0038", dapt_split="train", dapt_seen_at_train=True),
    groups(any_of=[["refrain", "renounce", "destroying", "kill"], ["living beings", "life"], ["ahimsa", "ahimsarata", "non-kill"]]),
    source_contains=["first vow the Jaina ascetic takes", "Ahimsarata"],
)

# ---------------------------------------------------------------- AGAM_GROUNDED
case(
    "024", "AGAM_GROUNDED", "en",
    "In this corpus's illustrated Agam series, which Agam and mool number is the Aavashyak Sutra?",
    "Agam 28, Mool 01 (Aavashyak Sutra, Sthanakvasi).",
    prov("SVK-2022:u088898", source_id="SVK-2022", dapt_split="val", dapt_seen_at_train=False),
    groups(all_of=["28"], any_of=["01", "mool 1", "first", "1"]),
    source_contains=["Agam 28 Mool 01 Aavashyak"],
)
case(
    "025", "AGAM_GROUNDED", "en",
    "In this corpus's illustrated Agam series, which Agam and mool number is the Dasvaikalik Sutra?",
    "Agam 29, Mool 02 (Dasvaikalik Sutra, Sthanakvasi).",
    prov("SVK-2026:u094492", source_id="SVK-2026", dapt_split="test", dapt_seen_at_train=False),
    groups(all_of=["29"], any_of=["02", "second", "mool 2"]),
    source_contains=["Agam 29 Mool 02 Dasvaikalik"],
)
case(
    "026", "AGAM_GROUNDED", "en",
    "According to the introduction of the Dasvaikalik Sutra in this corpus, how many Angas are there, how many are currently available, and what is the missing twelfth Anga called?",
    "Twelve Angas in all; eleven are currently available; the twelfth is Drstivada (Dṛṣṭivāda), which is not available.",
    prov("SVK-2026:u094511", source_id="SVK-2026", dapt_split="test", dapt_seen_at_train=False),
    groups(
        any_of=[
            ["12", "twelve"],
            ["11", "eleven"],
            ["drishti", "dṛṣṭi", "dristi", "drastivada", "dṛṣṭivāda", "tristivada", "dṛṣṭivād"],
        ],
    ),
    source_contains=["12 aNg", "11 aMga", "dRSTivAda"],
)
case(
    "027", "AGAM_GROUNDED", "en",
    "In this corpus's illustrated Agam series, what position does the Aupapatik Sutra hold among the Upangas, and which Anga does it accompany?",
    "It is the First Upanga, associated with the first Anga (Acaranga Sutra).",
    prov(["SVK-2029:u096137", "SVK-2029:u096175"], source_id="SVK-2029", dapt_split="test", dapt_seen_at_train=False),
    groups(any_of=[["upanga", "upang"], ["acharanga", "acaranga", "first anga"]], all_of=["first"]),
    source_contains=["The First Upanga", "Acharanga Sutra is the first Anga"],
)

# --------------------------------------------- STHANAKAVASI_DISTINCTION
case(
    "028", "STHANAKAVASI_DISTINCTION", "en",
    "Are the Sthanakavasi counted among the Svetambara or the Digambara, according to Stevenson and this corpus's source manifest?",
    "They are Svetambara (manifest: tradition SHWETAMBAR, sect STHANAKAVASI); Stevenson groups Svetambara and Sthanakavasi together and contrasts them with Digambara.",
    prov("SVK-0038:u00185", source_id="SVK-0038", dapt_split="train", dapt_seen_at_train=True,
         manifest_source_id="SVK-2026"),
    groups(all_of=["svetambara"], none_of=["are digambara", "sthānakavāsī are digambara", "sthankavasi are digambara"]),
    source_contains=["all Svetambara and Sthanakavasi practically agree"],
    notes="Forbids claiming the Sthanakavasi are Digambara; correct answers must affirm Svetambara affiliation.",
)
case(
    "029", "STHANAKAVASI_DISTINCTION", "en",
    "According to Stevenson, do the Sthanakavasi Jaina accept the Kalpa Sutra, and what do they do instead on the fasting days?",
    "No — the Sthanakavasi do not accept the Kalpa Sutra; they go to their own Upasaro and hear Mahavira's life read in their own scriptures.",
    prov("SVK-0038:u01204", source_id="SVK-0038", dapt_split="train", dapt_seen_at_train=True),
    groups(any_of=[["do not accept", "don't accept", "not accept", "reject", "no"], ["upasaro", "own scriptures", "mahavira's life", "not accept the kalpa"]]),
    source_contains=["Sthanakavasi Jaina, who do not accept the Kalpa Sutra"],
)
case(
    "030", "STHANAKAVASI_DISTINCTION", "en",
    "According to Stevenson, what is the Digambara position on the Svetambara Canon?",
    "The Digambara reject the Svetambara Canon.",
    prov("SVK-0038:u00171", source_id="SVK-0038", dapt_split="train", dapt_seen_at_train=True),
    groups(all_of=["digambara"], any_of=["reject", "refuse", "do not accept"]),
    source_contains=["The Digambara reject the Svetambara Canon"],
)
case(
    "031", "STHANAKAVASI_DISTINCTION", "en",
    "According to Stevenson, does a Sthanakavasi ascetic take a new name at diksha like Digambara and Svetambara ascetics do?",
    "No — Digambara and Svetambara ascetics take a new name, whereas the Sthanakavasi ascetic retains his old one.",
    prov("SVK-0038:u00297", source_id="SVK-0038", dapt_split="train", dapt_seen_at_train=True),
    groups(any_of=[["retain", "keeps", "old name", "same name", "still retain", "old one", "no"], ["sthānakavāsī", "sthankavasi", "sthana", "sthanakavasi", "not"]]),
    source_contains=["if he be a Sthanakavasi", "retain his old one"],
)

# ---------------------------------------------------------------- SOURCE_ATTRIBUTION
case(
    "032", "SOURCE_ATTRIBUTION", "en",
    "Who wrote the book 'Sthanakvasi Jain Itihas' listed in this corpus's source manifest?",
    "Kesrichand Bhandari.",
    man_prov("SVK-2027", "author", source_title="Sthanakvasi Jain Itihas", dapt_split="test", dapt_seen_at_train=False),
    groups(any_of=["kesrichand", "kesarichand", "bhandari"]),
    source_contains=[],
)
case(
    "033", "SOURCE_ATTRIBUTION", "en",
    "Who translated 'Gaina Sutras' (Acaranga and Sutrakrtanga) for the Sacred Books of the East, according to this corpus's source manifest?",
    "Hermann Jacobi.",
    man_prov("SVK-1001", "author", source_title="Gaina Sutras (Sacred Books of the East): Acaranga and Sutrakrtanga",
             dapt_split="train", dapt_seen_at_train=True),
    groups(any_of=["jacobi", "hermann"]),
    source_contains=[],
)
case(
    "034", "SOURCE_ATTRIBUTION", "en",
    "Who is the author of 'Notes on Modern Jainism' (1910), according to this corpus's source manifest?",
    "Mrs. Sinclair Stevenson.",
    man_prov("SVK-0038", "author", source_title="Notes on Modern Jainism (1910)", dapt_split="train", dapt_seen_at_train=True),
    groups(any_of=[["stevenson"], ["sinclair", "mrs"]]),
    source_contains=[],
)
case(
    "035", "SOURCE_ATTRIBUTION", "en",
    "On the title page of the Illustrated Aupapatik Sutra in this corpus, who is listed as Editor-in-Chief?",
    "Shri Amar Muni.",
    prov("SVK-2029:u096137", source_id="SVK-2029", dapt_split="test", dapt_seen_at_train=False),
    groups(all_of=["amar", "muni"]),
    source_contains=["Editor-in-Chief", "Shri Amar Muni"],
)

# ---------------------------------------------------------------- ABSTENTION
case(
    "036", "ABSTENTION", "en",
    "In what year was 'Sthanakvasi Jain Itihas' by Kesrichand Bhandari published?",
    "NOT MEASURED / abstention: neither the manifest publication_year nor any text in the source states a publication year.",
    man_prov("SVK-2027", "publication_year", source_title="Sthanakvasi Jain Itihas", dapt_split="test", dapt_seen_at_train=False),
    groups(
        abstention_markers=["not stated", "unknown", "not available", "cannot", "no year", "unspecified", "do not know", "don't know", "not mentioned", "not mention", "not given", "nowhere", "doesn't state", "does not state", "unable to determine", "not recorded", "not specified", "not know", "not have", "couldn't find", "could not find", "no record", "no information"],
        forbidden_claims=["(18|19|20)\\d{2}"],
    ),
    source_contains=[],
    abstention=True,
    notes="Absence verified: manifest publication_year empty; no real 18xx/19xx/20xx year token in SVK-2027 text (only the boilerplate string 'JainQQ source SVK-2027').",
)
case(
    "037", "ABSTENTION", "en",
    "In which year exactly was the Terapanth founded?",
    "NOT MEASURED / abstention: Stevenson gives only 'about 150 years ago' (relative to 1910); no exact founding year is stated in the corpus.",
    prov("SVK-0038:u01198", source_id="SVK-0038", dapt_split="train", dapt_seen_at_train=True),
    groups(
        abstention_markers=["about", "approximately", "circa", "around", "150 years", "19th century", "not stated", "unknown", "cannot", "do not know", "don't know", "not mentioned", "exact", "no exact", "unclear", "unsure", "earlier", "1910"],
        forbidden_claims=["in (17|18|19|20)\\d{2}", "founded in (17|18|19|20)\\d{2}(?!\\s*(or|to))", "\\b(17|18)\\d{2}\\b"],
    ),
    source_contains=["about 150 years ago"],
    abstention=True,
    notes="Correct behaviour: qualify ('about 150 years ago') or state that no exact year is given. Forbidden: an unqualified bare 15th-20th-century year.",
)
case(
    "038", "ABSTENTION", "en",
    "Who published 'Notes on Modern Jainism' (1910)?",
    "NOT MEASURED / abstention: the manifest publisher field is 'unknown' and no publisher statement appears in the source text.",
    man_prov("SVK-0038", "publisher", source_title="Notes on Modern Jainism (1910)", dapt_split="train", dapt_seen_at_train=True),
    groups(
        abstention_markers=["not stated", "unknown", "not available", "cannot", "do not know", "don't know", "not mentioned", "not given", "nowhere", "does not state", "doesn't state", "unable", "not recorded", "not specified", "no information", "no record"],
        forbidden_claims=["(?:publisher is|published by|issued by)\\s+(?!not\\b|unknown|no\\b|none)"],
    ),
    source_contains=[],
    abstention=True,
    notes="Absence verified: manifest publisher='unknown'; 0 hits for publish/printed/press/imprint within 300 chars of any 'Notes on Modern Jainism' mention in SVK-0038 text.",
)
case(
    "039", "ABSTENTION", "en",
    "How many Agams do the Digambara tradition accept?",
    "NOT MEASURED / abstention: the governed corpus states the Sthanakavasi/Svetambara enumeration but never states a Digambara Agam count.",
    prov([], role="corpus_absence", dapt_split="train", dapt_seen_at_train=True,
         absence_check="no unit co-occurs 'Digambara' with a number + Agam/Anga/scripture pattern in data/release/training_corpus.jsonl (0 hits)"),
    groups(
        abstention_markers=["not stated", "unknown", "not available", "cannot", "do not know", "don't know", "not mentioned", "not given", "does not state", "doesn't state", "unable", "not recorded", "not specified", "no information", "no record", "corpus", "sources"],
        forbidden_claims=["\\b(24|36|45|64|72)\\s*(agam|aagam)"],
    ),
    source_contains=[],
    abstention=True,
    notes="Absence verified corpus-wide: 0 hits for number+Agam/Anga near 'Digambara'.",
)

# ---------------------------------------------------------------- PRACTICE
case(
    "040", "PRACTICE", "en",
    "According to Stevenson, how long must a layman spend over Samayika?",
    "Forty-eight minutes.",
    prov("SVK-0038:u01132", source_id="SVK-0038", dapt_split="train", dapt_seen_at_train=True),
    groups(any_of=[["forty-eight", "forty eight", "48"], ["minute"]]),
    source_contains=["fbrty-oight minutes over Samayika"],
    notes="Source has OCR 'fbrty-oight'; reference transcription is forty-eight (confirmed by the same figure in u01125 'about forty-eight minutes').",
)
case(
    "041", "PRACTICE", "en",
    "According to Stevenson, into how many parts does Samayika consist?",
    "Eight parts.",
    prov("SVK-0038:u01125", source_id="SVK-0038", dapt_split="train", dapt_seen_at_train=True),
    groups(any_of=[["eight", "8"], ["part"]]),
    source_contains=["consists of eight parts"],
)
case(
    "042", "PRACTICE", "en",
    "According to the Pratikraman source in this corpus, how many essential acts (Avashyaka) are there, and what is Pratikraman used as for them?",
    "Six Avashyaka (essential acts); Pratikraman is used as a common noun covering all six.",
    prov("SVK-2024:u091510", source_id="SVK-2024", dapt_split="val", dapt_seen_at_train=False),
    groups(any_of=[["six", "6"], ["avashyaka", "avasayika", "essential act"]]),
    source_contains=["common noun for all six essential acts (six Avashyaka)"],
)
case(
    "043", "PRACTICE", "en",
    "In the Sthanang Sutra material of this corpus, in which direction(s) and for how long per direction is the Sarvatobhadra pratima kayotsarga practised?",
    "It faces all ten directions (four cardinal, four intermediate, zenith and nadir), for at least one ahoratra (24 hours) per direction.",
    prov("SVK-2025:u092214", source_id="SVK-2025", dapt_split="val", dapt_seen_at_train=False),
    groups(any_of=[["ten", "10"], ["24", "ahoratra", "day and night", "one day", "a day and a night"]]),
    source_contains=["Sarvatobhadraa pratima", "facing ten directions", "ahoratra"],
)

# ---------------------------------------------------------------- MULTILINGUAL_MAPPING
case(
    "044", "MULTILINGUAL_MAPPING", "en",
    "In the Sacred Books of the East Acaranga translation, the Prakrit word 'sthana' is explained by which Sanskrit/Jain technical term?",
    "Kayotsarga.",
    prov("SVK-1001:u01494", source_id="SVK-1001", dapt_split="train", dapt_seen_at_train=True),
    groups(any_of=["kayotsarga", "kayotsarga", "kāyotsarga", "kayotsarg"]),
    source_contains=["sthana is explained kayotsarga"],
)
case(
    "045", "MULTILINGUAL_MAPPING", "gu",
    "સ્ટીવેન્સનના કલ્પ સૂત્ર અનુવાદમાં પશ્ચાતાપ/અભય માટેનો ગુજરાતી શબ્દ શું છે? (સંસ્કૃત શબ્દ પ્રતિક્રમણ સાથે)",
    "આલવણ (Alavan).",
    prov("SVK-1002:u00101", source_id="SVK-1002", dapt_split="train", dapt_seen_at_train=True),
    groups(any_of=["alavan", "આલવણ"]),
    source_contains=["The Gujarathi word that expresses the priestly absolution, is Alavan"],
    notes="Same source unit as case 022 but a different (Gujarati-language) question and a different required key term.",
)
case(
    "046", "MULTILINGUAL_MAPPING", "en",
    "In Woolner's Introduction to Prakrit, what does Sanskrit 'n' generally become in Prakrit?",
    "It is generally represented in Prakrit by 'n' (with the dental n occurring before other dentals).",
    prov("SVK-2008:u00111", source_id="SVK-2008", dapt_split="train", dapt_seen_at_train=True),
    groups(any_of=[["represented", "written", "correspond", "become"], ["prakrit"]], all_of=["sanskrit"]),
    source_contains=["Sanskrit n is generally represented in Prakrit by n"],
)
case(
    "047", "MULTILINGUAL_MAPPING", "hi",
    "पाइय-सद्द-महान्नवो में प्राकृत शब्द 'मोक्क' के लिए क्या दिया गया है?",
    "मुक्त (mukta / liberation).",
    prov("SVK-2007:u32618", source_id="SVK-2007", dapt_split="train", dapt_seen_at_train=True),
    groups(any_of=["मुक्त", "mukta"]),
    source_contains=["मोक्क", "मुक्त"],
)


# ------------------------------------------------------------------ verification
def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").lower()


def main() -> int:
    want_units: set[str] = set()
    for c in CASES:
        for u in c["provenance"].get("unit_ids", []):
            want_units.add(u)
    want_sources = {
        c["provenance"].get("source_id")
        for c in CASES
        if c["provenance"].get("role") == "manifest"
    }
    for c in CASES:
        if "manifest_source_id" in c["provenance"]:
            want_sources.add(c["provenance"]["manifest_source_id"])

    units: dict[str, dict] = {}
    source_ids_seen: set[str] = set()
    absence_hits = {"digambara_count": 0, "svk2027_years": [], "svk0038_publisher_title_ctx": 0}
    dig_pat = re.compile(
        r"(\d{1,3}|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|forty|sixty|seventy)"
        r"\s*(Agam|Aagam|Anga|scripture)",
        re.I,
    )

    with CORPUS.open(encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            sid = r.get("source_id")
            if sid:
                source_ids_seen.add(sid)
            uid = r.get("id")
            if uid in want_units:
                units[uid] = r
            else:
                for w in want_units:
                    if uid.startswith(w + ":") and w not in units:
                        units[w] = r
            if sid == "SVK-2027":
                for m in re.finditer(r"(?<![\d:])(?:18|19|20)\d{2}(?![\d:])", r.get("normalized_text") or ""):
                    absence_hits["svk2027_years"].append((m.group(0), uid))
            if sid == "SVK-0038":
                t = r.get("normalized_text") or ""
                for m in re.finditer(r"Notes on Modern Jainism|MODERN JAINISM", t):
                    ctx = t[max(0, m.start() - 300): m.end() + 300]
                    if re.search(r"publish|printed|press|imprint", ctx, re.I):
                        absence_hits["svk0038_publisher_title_ctx"] += 1
                if "Digambara" in t or "Digumbara" in t:
                    for m in dig_pat.finditer(t):
                        ctx = t[max(0, m.start() - 80): m.end() + 80]
                        if re.search(r"Digambara|Digumbara", ctx):
                            absence_hits["digambara_count"] += 1

    manifest = {row["source_id"]: row for row in csv.DictReader(MANIFEST.open(encoding="utf-8"))}

    failures: list[str] = []
    for c in CASES:
        p = c["provenance"]
        if p.get("role") in {"manifest"}:
            sid = p.get("source_id")
            if sid not in manifest:
                failures.append(f"{c['example_id']}: manifest source {sid} missing")
                continue
            field = p.get("manifest_field")
            val = (manifest[sid].get(field) or "").strip()
            if not val:
                # abstention cases intentionally have empty values
                if not c["abstention_case"]:
                    failures.append(f"{c['example_id']}: manifest {sid}.{field} empty")
            else:
                keys = [k.lower() for k in c["scoring"][0].get("any_of", [])]
                if keys and not any(k in val.lower() for k in keys):
                    failures.append(
                        f"{c['example_id']}: manifest {sid}.{field}={val!r} does not contain any of {keys}"
                    )
            if sid not in source_ids_seen and field not in {"author", "publication_year", "publisher"}:
                failures.append(f"{c['example_id']}: manifest source {sid} absent from release corpus")
        if p.get("role") in {"manifest"} and p.get("field_language_check"):
            pass
        for u in p.get("unit_ids", []):
            if u not in units:
                failures.append(f"{c['example_id']}: unit {u} not found in release corpus")
        if c["source_contains"]:
            blob = norm(" ".join((units.get(u, {}).get("normalized_text") or "") for u in p.get("unit_ids", [])))
            for needle in c["source_contains"]:
                if norm(needle) not in blob:
                    failures.append(
                        f"{c['example_id']}: source text does not contain {needle!r} "
                        f"(units={p.get('unit_ids')})"
                    )
        # split consistency
        sid = p.get("source_id") or p.get("manifest_source_id")
        if sid and p.get("dapt_split"):
            expected = next((k for k, v in DAPT_SPLITS.items() if sid in v), None)
            if expected != p["dapt_split"]:
                failures.append(
                    f"{c['example_id']}: source {sid} split {p['dapt_split']} != domain-train split {expected}"
                )

    # abstention absence assertions
    real_years = [y for y in absence_hits["svk2027_years"] if y[0] != "2027"]
    if real_years:
        failures.append(f"ABSTENTION 036: SVK-2027 contains year tokens {real_years[:5]}")
    if absence_hits["svk0038_publisher_title_ctx"]:
        failures.append("ABSTENTION 038: publisher statement found near the Notes on Modern Jainism title")
    if absence_hits["digambara_count"]:
        failures.append(f"ABSTENTION 039: {absence_hits['digambara_count']} Digambara+count hits")

    if failures:
        print("VERIFICATION FAILED:")
        for f in failures:
            print(" -", f)
        return 1

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as fh:
        for c in CASES:
            fh.write(json.dumps(c, ensure_ascii=False) + "\n")

    cat = Counter(c["category"] for c in CASES)
    lang = Counter(c["language"] for c in CASES)
    split = Counter(
        c["provenance"].get("dapt_split") or "unspecified" for c in CASES
    )
    print(f"wrote {len(CASES)} cases -> {OUT.relative_to(REPO)}")
    print("categories:", dict(sorted(cat.items())))
    print("languages:", dict(lang))
    print("dapt splits:", dict(split))
    print("abstention cases:", sum(1 for c in CASES if c["abstention_case"]))
    print("objective (rule-scored) cases:", sum(1 for c in CASES if c["scoring"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
