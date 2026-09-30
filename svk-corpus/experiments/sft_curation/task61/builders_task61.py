"""TASK 61 stage 3 - candidate builders.

Every candidate question/answer pair is constructed only from
  * one corpus unit (quoted verbatim as the evidence), or
  * the source manifest row / rights evidence (for SOURCE_ATTRIBUTION and
    CANONICAL_VS_COMMENTARY questions), or
  * a machine-verified absence (for abstention candidates).

No fact is written from model memory. Quotes are verified against the cited
unit by the quality gates in build_task61_candidates.py.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from task61_common import canonical_status, is_boilerplate, ocr_noise_score

DEV = re.compile(r"[ऀ-ॿ]")
GUJ = re.compile(r"[઀-૿]")


def script_of(text: str) -> str:
    if not text:
        return "unknown"
    if sum(1 for c in text if GUJ.match(c)) >= 3:
        return "gujarati"
    if sum(1 for c in text if DEV.match(c)) >= 3:
        return "devanagari"
    return "latin"


def split_sentences(text: str) -> List[str]:
    sc = script_of(text)
    if sc == "devanagari":
        parts = re.split(r"(?<=[।॥])\s*|\n+", text)
    elif sc == "gujarati":
        parts = re.split(r"(?<=[।॥])\s*|\n+", text)
    else:
        parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [p.strip() for p in parts if p and p.strip()]


def clean_quote(text: str, must_have: Optional[str] = None,
                min_len: int = 40, max_len: int = 460) -> Optional[str]:
    """Pick the cleanest sentence that carries the required evidence."""
    if not text:
        return None
    cands = []
    for sent in split_sentences(text):
        s = " ".join(sent.split())
        if not (min_len <= len(s) <= max_len):
            continue
        if must_have and not re.search(must_have, s, re.I):
            continue
        if is_boilerplate(s):
            continue
        noise = ocr_noise_score(s)["score"]
        if noise >= 0.5:
            continue
        cands.append((noise, -len(s), s))
    if cands:
        cands.sort()
        return cands[0][2]
    whole = " ".join(text.split())
    if min_len <= len(whole) <= max_len and not is_boilerplate(whole) and ocr_noise_score(whole)["score"] < 0.5:
        return whole
    if must_have and len(whole) <= max_len * 2:
        # keep evidence even when slightly long, but only if reasonably clean
        if ocr_noise_score(whole)["score"] < 0.6 and not is_boilerplate(whole):
            return whole[:max_len].rsplit(" ", 1)[0]
    return None


TOPIC_PHRASES = [
    "chedagrantha", "cheda grantha", "mulagrantha", "mula grantha", "payanna",
    "canon of scriptures", "canonical scriptures", "scriptures", "scripture",
    "books", "reading of the scriptures", "sermon", "laity", "monks only",
    "new name", "nine principles", "nava tatva", "seven principles",
    "intermarriage", "age for marriage", "marriage", "food", "upasaro",
    "whisk", "procession", "birthday", "festival", "vow", "vows",
    "colour of the robe", "clothing", "robe", "names of ascetics",
    "ascetics", "worship", "idol", "image", "temple", "monastery",
    "logic", "anuyogadvdra", "conduct", "penance", "meditation",
]


def topic_from_text(text: str, section: str = "") -> Optional[str]:
    low = (text or "").lower()
    for ph in TOPIC_PHRASES:
        if ph in low:
            return ph
    sec = " ".join((section or "").split())
    if 5 <= len(sec) <= 60 and re.search(r"[A-Za-z]", sec) and not re.search(r"[^A-Za-z0-9 .&\-']", sec):
        return sec.lower()
    return None


def clean_basis(text: str) -> str:
    """Strip raw manifest source ids from prose-visible basis strings."""
    t = re.sub(r"\bSVK-\d{3,4}\b", "a related manifest source", text or "")
    return " ".join(t.split())

def attribution_label(man: Dict[str, str], source_id: str) -> str:
    title = man.get("title") or source_id
    author = (man.get("author") or "").strip()
    year = (man.get("publication_year") or "").strip()
    bits = [b for b in (author, year) if b and b.lower() != "unknown"]
    if bits:
        return "%s (%s)" % (title, ", ".join(bits))
    return title


def layer_sentence(man: Dict[str, str]) -> str:
    raw = (man.get("knowledge_layer") or "").strip()
    if not raw:
        return "The manifest does not record a knowledge layer for this source."
    return "It is recorded in the manifest as %s material." % raw


def scope_sentence(man: Dict[str, str]) -> str:
    raw = (man.get("religious_scope") or "").strip()
    if not raw:
        return "The manifest does not record a religious scope for this source."
    return "Its recorded religious scope is %s." % raw


def quote_answer(label: str, topic: str, quote: str, man: Dict[str, str],
                 boundary: bool = True) -> str:
    parts = ['On %s, %s states: "%s"' % (topic, label, quote)]
    if boundary:
        parts.append(boundary_sentence(man).strip())
    text = " ".join(p.replace("\n", " ") for p in parts if p)
    if not text.endswith((".", "?", "!", "।")):
        text += "."
    return text


def boundary_sentence(man: Dict[str, str]) -> str:
    scope = (man.get("religious_scope") or "").strip()
    sect = (man.get("sect") or "").strip()
    if not scope or scope.upper() == "UNKNOWN":
        return ""
    bits = ["scope %s" % scope]
    if sect and sect.lower() not in ("unknown", ""):
        bits.append("sect recorded as %s" % sect)
    return (" This is that source's account (manifest %s); other Jain traditions may "
            "describe the same point differently, and this passage does not say so."
            % " with ".join(bits))


# --------------------------------------------------------------------------
# draft container
# --------------------------------------------------------------------------
def draft(category: str, task_category: str, question_type: str, question: str,
          answer: str, unit: Optional[Dict[str, Any]], source_id: str,
          sets: List[str], language: str, extra: Optional[Dict[str, Any]] = None,
          manifest_grounded: bool = False, quote: str = "",
          question_hi: str = "") -> Dict[str, Any]:
    return {
        "category": category,
        "task_category": task_category,
        "question_type": question_type,
        "question": question,
        "question_hi": question_hi,
        "answer": answer,
        "source_id": source_id,
        "unit_id": (unit or {}).get("unit_id", ""),
        "corpus_id": (unit or {}).get("corpus_id", ""),
        "quote": quote or "",
        "section": (unit or {}).get("section", ""),
        "locator": (unit or {}).get("locator", {}),
        "unit_text": (unit or {}).get("text", ""),
        "sets": sets,
        "language": language,
        "extra": extra or {},
        "manifest_grounded": manifest_grounded,
    }



USED_QUESTIONS = set()


def fresh_question(q: str) -> bool:
    """Reserve a question string; returns False when it was already used."""
    key = " ".join((q or "").lower().split())
    if not key or key in USED_QUESTIONS:
        return False
    USED_QUESTIONS.add(key)
    return True


SECT_Q = [
    "How do Sthanakavasi Jains differ from {other} Jains on {topic} according to {label}?",
    "What difference between Sthanakavasi and {other} practice regarding {topic} does {label} describe?",
    "In {label}, what is said about {topic} for Sthanakavasi Jains as distinct from {other} Jains?",
]


def build_sect(units, man_by_sid, cap):
    out = []
    for u in units:
        text = u["text"]
        man = man_by_sid.get(u["source_id"], {})
        other = "Digambara" if re.search(r"Digambar", text, re.I) else "Svetambara"
        if not re.search(r"Sthanakavasi|Sthanakvas", text, re.I):
            continue
        topic = topic_from_text(text, u.get("section", ""))
        if not topic:
            continue
        label = attribution_label(man, u["source_id"])
        quote = clean_quote(text, must_have=r"Sthanakavasi|Sthanakvas")
        if not quote:
            continue
        i = len(out) % len(SECT_Q)
        q = SECT_Q[i].format(other=other, topic=topic, label=label)
        if not fresh_question(q):
            continue
        a = quote_answer(label, topic, quote, man, boundary=True)
        out.append(draft("STHANAKAVASI_DISTINCTION", "cross_tradition_distinction",
                         "comparative", q, a, u, u["source_id"],
                         ["candidates_v2", "sect_distinction"], "en",
                         {"other_sect": other, "topic": topic}, quote=quote))
        if len(out) >= cap:
            break
    return out


PRACTICE_TERMS = [
    ("Samayik", r"Samayik"), ("Pratikraman", r"Pratikram"),
    ("Kayotsarga", r"Kayotsarg"), ("Paryushana", r"Paryushan"),
    ("Avashyaka", r"Avashyak"), ("Upavasa (fasting)", r"Upavas"),
    ("the Jain vows", r"\bvows?\b"), ("Ahimsa (non-violence)", r"Ahims[ae]"),
    ("Tapa (austerity)", r"\bTapa\b"),
]
PRACTICE_Q = [
    "How does {label} describe {practice}?",
    "What is {practice} according to {label}?",
    "What role does {practice} play in Jain practice as described in {label}?",
    "According to {label}, how should {practice} be understood?",
]


def build_practice(units, man_by_sid, cap):
    out = []
    for u in units:
        text = u["text"]
        man = man_by_sid.get(u["source_id"], {})
        found = None
        for display, pat in PRACTICE_TERMS:
            if re.search(pat, text, re.I):
                found = (display, pat)
                break
        if not found:
            continue
        display, pat = found
        quote = clean_quote(text, must_have=pat)
        if not quote:
            continue
        label = attribution_label(man, u["source_id"])
        q = PRACTICE_Q[len(out) % len(PRACTICE_Q)].format(practice=display, label=label)
        if not fresh_question(q):
            continue
        a = quote_answer(label, display, quote, man, boundary=False)
        out.append(draft("PRACTICE_EXPLANATION", "general_qa", "explanatory", q, a,
                         u, u["source_id"], ["candidates_v2"], "en",
                         {"practice": display, "practice_pattern": pat}, quote=quote))
        if len(out) >= cap:
            break
    return out


TERM_PATTERNS = [
    ("Upasaro", r"Upasaro"), ("Samayika", r"Samayik"),
    ("Nisahi", r"Nisahi"), ("Avasahi", r"Vasahi"),
    ("Mahapurusa", r"Mahapurusa"), ("Pujya", r"\bPujya\b"),
    ("Mahasati", r"Mahasati"), ("Samvegi", r"Samvegi"),
    ("Garaniji", r"Garaniji"), ("Rajono", r"Rajono"),
    ("Chedagrantha", r"Chedagrantha"), ("Anuyogadvdra", r"Anuyogadv"),
    ("Mithyatva", r"Mithyatva"), ("Sthanakavasi", r"Sthanakavasi"),
]
TERM_Q = [
    "What does the term '{term}' mean in {label}?",
    "How does {label} explain the term '{term}'?",
    "In {label}, what is meant by '{term}'?",
]


def build_terminology(units, man_by_sid, cap):
    out = []
    for u in units:
        text = u["text"]
        man = man_by_sid.get(u["source_id"], {})
        scope = (man.get("religious_scope") or "").upper()
        sect_hint = scope in ("CORE_STHANAKAVASI", "HIGH_STHANAKAVASI_RELEVANCE") or \
            bool(re.search(r"Sthanakavasi|Sthanakvas", text, re.I))
        if not sect_hint:
            continue
        term = None
        for display, pat in TERM_PATTERNS:
            if re.search(pat, text, re.I):
                term = (display, pat)
                break
        if not term:
            continue
        display, pat = term
        quote = clean_quote(text, must_have=pat)
        if not quote:
            continue
        label = attribution_label(man, u["source_id"])
        q = TERM_Q[len(out) % len(TERM_Q)].format(term=display, label=label)
        if not fresh_question(q):
            continue
        a = quote_answer(label, "the term '%s'" % display, quote, man, boundary=False)
        out.append(draft("STHANAKAVASI_TERMINOLOGY", "sthanaqa", "definitional", q, a,
                         u, u["source_id"], ["candidates_v2"], "en",
                         {"term": display}, quote=quote))
        if len(out) >= cap:
            break
    return out


AGAM_Q_HEADER = [
    'What does the catalog header of "{book}" record about its Agam numbering and authors?',
    'According to its own catalog header, which Agam text is "{book}" and who are its authors?',
]
AGAM_Q_TEXT = [
    "What does {label} say about the Angas of the Jain canon?",
    "How does {label} describe the Angas and the scripture catalogue?",
]


def _parse_header(text):
    book = re.search(r"Book Title:\s*(.+?)(?:\s*Author\(s\):|$)", text, re.S)
    authors = re.search(r"Author\(s\):\s*(.+?)(?:\s*Publisher:|$)", text, re.S)
    pub = re.search(r"Publisher:\s*(.+?)(?:\s*Catalog link:|$)", text, re.S)
    agam = re.search(r"Agam\s*(\d+)\s*([A-Za-z]+\s*\d+)?", text, re.I)
    return {
        "book": " ".join(book.group(1).split()) if book else "",
        "authors": " ".join(authors.group(1).split()) if authors else "",
        "publisher": " ".join(pub.group(1).split()) if pub else "",
        "agam": ("AGAM-%03d" % int(agam.group(1))) if agam else "",
    }


def build_agam(header_units, text_units, man_by_sid, cap):
    out = []
    for u in header_units:
        parsed = _parse_header(u["text"])
        if not parsed["book"]:
            continue
        man = man_by_sid.get(u["source_id"], {})
        label = attribution_label(man, u["source_id"])
        q = AGAM_Q_HEADER[len(out) % len(AGAM_Q_HEADER)].format(book=parsed["book"])
        if not fresh_question(q):
            continue
        quote = clean_quote(u["text"], must_have=r"Book Title", min_len=30, max_len=420)
        if not quote:
            continue
        a = ('The header records: "%s" So this text is "%s"%s, published by %s.'
             % (quote, parsed["book"],
                (" (numbered %s)" % parsed["agam"]) if parsed["agam"] else "",
                parsed["publisher"] or "the recorded publisher"))
        out.append(draft("AGAM_GROUNDED", "general_qa", "factual", q, a, u,
                         u["source_id"], ["candidates_v2"], "en",
                         {"agam_id": parsed["agam"], "book": parsed["book"],
                          "authors": parsed["authors"], "publisher": parsed["publisher"]},
                         quote=quote))
        if len(out) >= cap:
            break
    if len(out) < cap:
        for u in text_units:
            text = u["text"]
            if not re.search(r"\bAngas?\b|Aṅga", text):
                continue
            man = man_by_sid.get(u["source_id"], {})
            quote = clean_quote(text, must_have=r"\bAngas?\b|Aṅga")
            if not quote:
                continue
            label = attribution_label(man, u["source_id"])
            q = AGAM_Q_TEXT[len(out) % len(AGAM_Q_TEXT)].format(label=label)
            if not fresh_question(q):
                continue
            a = quote_answer(label, "the Angas of the canon", quote, man, boundary=False)
            out.append(draft("AGAM_GROUNDED", "general_qa", "explanatory", q, a, u,
                             u["source_id"], ["candidates_v2"], "en",
                             {"agam_id": ""}, quote=quote))
            if len(out) >= cap:
                break
    return out


PRAKRIT_TERMS = ["Maharashtri", "Ardhamagadhi", "Ardha Magadhi", "Sauraseni",
                 "Prakrits", "Prakrit", "Sanskrit"]
PRAKRIT_Q = [
    "How does {label} treat the term '{term}'?",
    "What does {label} say about '{term}'?",
    "In {label}, how is '{term}' explained?",
]


def build_prakrit(units, gloss_units, man_by_sid, cap):
    out = []
    for u in units:
        text = u["text"]
        term = None
        for t in PRAKRIT_TERMS:
            if re.search(re.escape(t), text, re.I):
                term = t
                break
        if not term:
            continue
        man = man_by_sid.get(u["source_id"], {})
        quote = clean_quote(text, must_have=re.escape(term))
        if not quote:
            continue
        label = attribution_label(man, u["source_id"])
        q = PRAKRIT_Q[len(out) % len(PRAKRIT_Q)].format(term=term, label=label)
        if not fresh_question(q):
            continue
        a = quote_answer(label, term, quote, man, boundary=False)
        out.append(draft("PRAKRIT", "prakrit_explanation", "definitional", q, a, u,
                         u["source_id"], ["candidates_v2"], "en",
                         {"prakrit_term": term}, quote=quote))
        if len(out) >= cap:
            break
    if len(out) < cap:
        for u in gloss_units:
            m = re.search(r"([A-Za-z][A-Za-z'’\-.]{2,})\s*=\s*([A-Za-z][A-Za-z'’\-.]{1,})", u["text"])
            if not m:
                continue
            term = m.group(1)
            man = man_by_sid.get(u["source_id"], {})
            quote = clean_quote(u["text"], must_have=re.escape(term) + r"\s*=")
            if not quote:
                continue
            label = attribution_label(man, u["source_id"])
            q = "How does the translation in %s gloss the Prakrit form '%s'?" % (label, term)
            if not fresh_question(q):
                continue
            a = quote_answer(label, "the form '%s'" % term, quote, man, boundary=False)
            out.append(draft("PRAKRIT", "prakrit_explanation", "definitional", q, a, u,
                             u["source_id"], ["candidates_v2"], "en",
                             {"prakrit_term": term}, quote=quote))
            if len(out) >= cap:
                break
    return out


HI_TERMS = ["उत्तराध्ययन", "प्रतिक्रमण", "आगम", "सूत्र", "अहिंसा", "तप", "कर्म",
            "विनय", "मोक्ष", "प्रश्न-उत्तर", "समयिक", "उपवास", "व्रत", "श्रमण",
            "भगवान महावीर", "जैन"]
GU_TERMS = ["સૂત્ર", "આગમ", "જૈન", "તપ", "કર્મ", "અહિંસા", "પ્રતિક્રમણ", "મોક્ષ",
            "વ્રત", "શ્રમણ", "ઉત્તરાધ્યયન", "ભગવાન મહાવીર"]
HI_Q = [
    "{label} में {topic} के बारे में क्या कहा गया है?",
    "{topic} पर {label} का क्या कहना है?",
]
GU_Q = [
    "{label} માં {topic} વિશે શું કહેવામાં આવ્યું છે?",
    "{topic} અંગે {label} શું કહે છે?",
]


def build_hindi(units, man_by_sid, cap):
    out = []
    for u in units:
        text = u["text"]
        term = next((t for t in HI_TERMS if t in text), None)
        if not term:
            continue
        man = man_by_sid.get(u["source_id"], {})
        quote = clean_quote(text, must_have=re.escape(term))
        if not quote:
            continue
        label = attribution_label(man, u["source_id"])
        q = HI_Q[len(out) % len(HI_Q)].format(label=label, topic=term)
        if not fresh_question(q):
            continue
        a = '%s के अनुसार: "%s"' % (label, quote)
        scope = (man.get("religious_scope") or "").strip()
        if scope and scope.upper() != "UNKNOWN":
            a += " यह उसी स्रोत का विवरण है (मैनिफेस्ट में दर्ज परिधि: %s)।" % scope
        out.append(draft("HINDI", "multilingual_mapping", "factual", q, a, u,
                         u["source_id"], ["candidates_v2"], "hi",
                         {"topic": term}, quote=quote))
        if len(out) >= cap:
            break
    return out


def build_gujarati(units, man_by_sid, cap):
    out = []
    for u in units:
        text = u["text"]
        term = next((t for t in GU_TERMS if t in text), None)
        if not term:
            continue
        man = man_by_sid.get(u["source_id"], {})
        quote = clean_quote(text, must_have=re.escape(term))
        if not quote:
            continue
        label = attribution_label(man, u["source_id"])
        q = GU_Q[len(out) % len(GU_Q)].format(label=label, topic=term)
        if not fresh_question(q):
            continue
        a = '%s ના અનુસાર: "%s"' % (label, quote)
        scope = (man.get("religious_scope") or "").strip()
        if scope and scope.upper() != "UNKNOWN":
            a += " આ વર્ણન એ જ સ્રોતનું છે (મેનિફેસ્ટમાં નોંધાયેલી પરિધિ: %s)।" % scope
        out.append(draft("GUJARATI", "multilingual_mapping", "factual", q, a, u,
                         u["source_id"], ["candidates_v2"], "gu",
                         {"topic": term}, quote=quote))
        if len(out) >= cap:
            break
    return out


SA_Q = [
    "How does {label} explain the Sanskrit or Prakrit term '{term}'?",
    "What meaning does {label} give for the term '{term}'?",
    "In {label}, how is the term '{term}' rendered?",
]
SA_Q_HI = [
    "{label} में संस्कृत/प्राकृत पद '{term}' का क्या अर्थ दिया गया है?",
]


def build_sanskrit(gloss_units, dev_units, man_by_sid, cap):
    out = []
    for u in gloss_units:
        text = u["text"]
        m = re.search(r"Sanskrit[^.\n]{0,80}", text)
        mg = re.search(r"([A-Za-z][A-Za-z'’\-.]{2,})\s*=\s*([A-Za-z][A-Za-z'’\-.]{1,})", text)
        term = mg.group(1) if mg else (m.group(0).split()[-1] if m else "")
        if not term or len(term) < 3:
            continue
        man = man_by_sid.get(u["source_id"], {})
        quote = clean_quote(text, must_have=re.escape(term))
        if not quote:
            continue
        label = attribution_label(man, u["source_id"])
        q = SA_Q[len(out) % len(SA_Q)].format(term=term, label=label)
        if not fresh_question(q):
            continue
        a = quote_answer(label, "the term '%s'" % term, quote, man, boundary=False)
        out.append(draft("SANSKRIT", "multilingual_mapping", "definitional", q, a, u,
                         u["source_id"], ["candidates_v2"], "en",
                         {"sanskrit_term": term,
                          "language_note": "Sanskrit term glossed in an English source; corpus has no clean sa-language source"},
                         quote=quote))
        if len(out) >= cap:
            break
    if len(out) < cap:
        for u in dev_units:
            text = u["text"]
            m = re.search(r"([ऀ-ॿ]{3,})", text)
            if not m:
                continue
            term = m.group(1)
            man = man_by_sid.get(u["source_id"], {})
            quote = clean_quote(text, must_have=re.escape(term))
            if not quote:
                continue
            label = attribution_label(man, u["source_id"])
            q = SA_Q_HI[len(out) % len(SA_Q_HI)].format(term=term, label=label)
            if not fresh_question(q):
                continue
            a = '%s में पद/संदर्भ "%s"' % (label, quote)
            out.append(draft("SANSKRIT", "multilingual_mapping", "factual", q, a, u,
                             u["source_id"], ["candidates_v2"], "sa",
                             {"sanskrit_term": term,
                              "language_note": "Devanagari unit from a source whose manifest language is not sa; flagged for human confirmation"},
                             quote=quote))
            if len(out) >= cap:
                break
    return out


GENERAL_TERMS = [("Ahimsa (non-violence)", r"Ahims[ae]"), ("karma", r"\bkarm[ae]n?\b"),
                 ("moksa / liberation", r"Moks[ae]"), ("Tirthankara", r"Tirth[a-z]*r[a-z]*kara|Tirtharikara"),
                 ("the twelve limbs of doctrine", r"twelve limbs"),
                 ("the nine principles", r"nine principles"),
                 ("right faith, knowledge and conduct", r"right faith"),
                 ("the Sangha", r"\bSangha\b"), ("papapunya (merit and sin)", r"Papa|Punya")]
GENERAL_Q = [
    "What does {label} say about {concept}?",
    "How is {concept} described in {label}?",
    "According to {label}, how should {concept} be understood?",
]


def build_general(units, man_by_sid, cap):
    out = []
    for u in units:
        text = u["text"]
        found = next(((d, p) for d, p in GENERAL_TERMS if re.search(p, text, re.I)), None)
        if not found:
            continue
        display, pat = found
        man = man_by_sid.get(u["source_id"], {})
        quote = clean_quote(text, must_have=pat)
        if not quote:
            continue
        label = attribution_label(man, u["source_id"])
        q = GENERAL_Q[len(out) % len(GENERAL_Q)].format(concept=display, label=label)
        if not fresh_question(q):
            continue
        a = quote_answer(label, display, quote, man, boundary=False)
        out.append(draft("GENERAL_JAIN_CONCEPT", "general_qa", "explanatory", q, a, u,
                         u["source_id"], ["candidates_v2"], "en",
                         {"concept": display}, quote=quote))
        if len(out) >= cap:
            break
    return out


# --------------------------------------------------------------------------
# SOURCE_ATTRIBUTION (manifest-grounded and header-grounded)
# --------------------------------------------------------------------------
def build_source_attribution(man_by_sid, allowed_sids, header_units, cap):
    out = []
    # 1) header-grounded attribution (real corpus text)
    for u in header_units:
        parsed = _parse_header(u["text"])
        if not parsed["authors"]:
            continue
        man = man_by_sid.get(u["source_id"], {})
        label = attribution_label(man, u["source_id"])
        quote = clean_quote(u["text"], must_have=r"Author\(s\):", min_len=30, max_len=420)
        if not quote:
            continue
        q = 'According to the catalog header of "%s", who authored and published it?' % parsed["book"]
        if not fresh_question(q):
            continue
        a = ('The header records: "%s" It lists %s as author(s) and %s as publisher.'
             % (quote, parsed["authors"], parsed["publisher"] or "the recorded publisher"))
        out.append(draft("SOURCE_ATTRIBUTION", "source_citation", "factual", q, a, u,
                         u["source_id"], ["candidates_v2", "source_attribution"], "en",
                         {"attributed_authors": parsed["authors"],
                          "attributed_publisher": parsed["publisher"]}, quote=quote))
        if len(out) >= cap:
            return out
    # 2) manifest-grounded attribution
    variants = ["author", "kind", "publisher", "tradition", "scope", "provenance"]
    idx = 0
    for sid in sorted(allowed_sids):
        man = man_by_sid.get(sid, {})
        if not man or not man.get("title"):
            continue
        kind = variants[idx % len(variants)]
        idx += 1
        title = man["title"]
        author = (man.get("author") or "").strip()
        year = (man.get("publication_year") or "").strip()
        publisher = (man.get("publisher") or "").strip()
        layer = (man.get("knowledge_layer") or "").strip()
        scope = (man.get("religious_scope") or "").strip()
        rel = (man.get("relation_type") or "").strip()
        lic = (man.get("license") or "").strip()
        cstat = canonical_status(man)
        if kind == "author":
            if not author or author.lower() == "unknown":
                continue
            q = "Who is listed as the author of %s?" % title
            if not fresh_question(q):
                continue
            a = ("The corpus manifest records %s as written by %s%s. It is classified as %s "
                 "material with %s scope."
                 % (title, author, (" in %s" % year) if year else "",
                    layer or "unclassified", scope or "unrecorded scope"))
        elif kind == "kind":
            if not layer:
                continue
            q = "What kind of text is %s - a canonical scripture, a commentary, or a later study?" % title
            if not fresh_question(q):
                continue
            a = ("The manifest records %s as %s material. Its canonical status is derived as %s%s."
                 % (title, layer, cstat,
                    (", because its recorded relation_type is %s" % rel) if rel else ""))
        elif kind == "publisher":
            if not publisher:
                continue
            q = "Which publisher and publication year are recorded for %s?" % title
            if not fresh_question(q):
                continue
            a = ("The manifest records %s as published by %s%s; its recorded license basis is %s."
                 % (title, publisher, (" in %s" % year) if year else " (year not recorded)",
                    clean_basis(lic) or "not recorded"))
        elif kind == "tradition":
            trad = (man.get("tradition") or "").strip()
            if not trad:
                continue
            q = "Which tradition and sect does the manifest record for %s?" % title
            if not fresh_question(q):
                continue
            a = ("The manifest records %s under tradition %s, sect %s (confidence %s), "
                 "with classification basis recorded as %s."
                 % (title, trad, man.get("sect") or "not recorded",
                    man.get("sect_confidence") or "not recorded",
                    clean_basis(man.get("sect_basis")) or "not recorded"))
        elif kind == "scope":
            if not scope:
                continue
            q = "Is %s specific to the Sthanakavasi tradition or general Jain material?" % title
            if not fresh_question(q):
                continue
            a = ("The manifest classifies %s with religious scope %s on the basis of %s. "
                 "That is a manifest classification of the source, not a doctrinal judgement."
                 % (title, scope, clean_basis(man.get("religious_scope_basis")) or "the source manifest"))
        else:
            repo = (man.get("repository") or "").strip()
            if not repo and not man.get("source_url"):
                continue
            q = "What is the recorded provenance of %s?" % title
            if not fresh_question(q):
                continue
            a = ("The manifest records %s as acquired from %s, with recorded training permission %s "
                 "and license basis %s. The recorded source URL is kept in the citations metadata."
                 % (title, repo or "the recorded repository",
                    (man.get("training_permission") or "not recorded"),
                    clean_basis(lic) or "not recorded"))
        out.append(draft("SOURCE_ATTRIBUTION", "source_citation", "factual", q, a, None,
                         sid, ["candidates_v2", "source_attribution"],
                         (man.get("language") or "").split(";")[0].strip() or "en",
                         {"manifest_field": kind, "canonical_status": cstat},
                         manifest_grounded=True))
        if len(out) >= cap:
            break
    return out


# --------------------------------------------------------------------------
# CANONICAL_VS_COMMENTARY
# --------------------------------------------------------------------------
CCV_Q_REL = [
    "Is {child} a canonical scripture itself, or a work about one?",
    "How should {child} be classified: canonical text, edition, translation, or commentary?",
]
CCV_Q_TEXT = [
    "According to {label}, in what language were the scriptures written and in what language were commentaries written?",
    "How does {label} distinguish the scriptures from later commentary on them?",
]


def build_canonical_vs_commentary(man_by_sid, allowed_sids, units, cap):
    out = []
    for sid in sorted(allowed_sids):
        man = man_by_sid.get(sid, {})
        rel = (man.get("relation_type") or "").strip().lower()
        if rel not in ("edition_of", "translation_of", "commentary", "liturgical", "discusses"):
            continue
        parent_id = (man.get("parent_source_id") or "").strip()
        parent = man_by_sid.get(parent_id, {})
        child_cstat = canonical_status(man)
        q = CCV_Q_REL[len(out) % len(CCV_Q_REL)].format(child=man.get("title", sid))
        if not fresh_question(q):
            continue
        a = ("The manifest records %s with relation_type %s%s. Its knowledge layer is %s and its "
             "derived canonical status is %s%s."
             % (man.get("title", sid), rel,
                (", pointing to %s" % parent.get("title", parent_id)) if parent else "",
                (man.get("knowledge_layer") or "not recorded"),
                child_cstat,
                ("; the parent source is recorded as %s" % (canonical_status(parent))) if parent else ""))
        out.append(draft("CANONICAL_VS_COMMENTARY", "canonical_commentary_distinction",
                         "comparative", q, a, None, sid, ["candidates_v2"],
                         (man.get("language") or "en").split(";")[0].strip(),
                         {"relation_type": rel, "parent_source_id": parent_id,
                          "manifest_field": "relation_type"},
                         manifest_grounded=True))
        if len(out) >= cap:
            return out
    for u in units:
        text = u["text"]
        if not re.search(r"commentar|scriptures were written| scriptures ", text, re.I):
            continue
        man = man_by_sid.get(u["source_id"], {})
        quote = clean_quote(text, must_have=r"commentar")
        if not quote:
            continue
        label = attribution_label(man, u["source_id"])
        q = CCV_Q_TEXT[len(out) % len(CCV_Q_TEXT)].format(label=label)
        if not fresh_question(q):
            continue
        a = quote_answer(label, "the scriptures and their commentaries", quote, man, boundary=False)
        out.append(draft("CANONICAL_VS_COMMENTARY", "canonical_commentary_distinction",
                         "explanatory", q, a, u, u["source_id"], ["candidates_v2"], "en",
                         {"relation_type": "text_evidence"}, quote=quote))
        if len(out) >= cap:
            break
    return out


# --------------------------------------------------------------------------
# ABSTENTION (evidence-based, absence machine-verified)
# --------------------------------------------------------------------------
# scan: regex that must produce ZERO matches corpus-wide (or in scope)
# manifest_gap: (field, list of source_ids) that must be empty for the answer
ABSTENTION_CASES = [
    dict(id="ABST-01", question="In which year was the Terapanth sector of Jain monastics founded?",
         scan=r"Terapanth[^.\n]{0,60}\b(1[6-9]\d\d|20[0-2]\d)\b", scope="all",
         missing="a founding year for Terapanth",
         required="a dated Terapanth foundation record",
         known_scan=r"Terapanth[^.\n]{0,80}(years|century)", known_label="the only relative dating the corpus gives"),
    dict(id="ABST-02", question="In which year was the Sthanakavasi sect established as a separate tradition?",
         scan=r"Sthanakavasi[^.\n]{0,60}\b(1[0-9]{3}|20[0-2][0-9])\b", scope="all",
         missing="a founding year for the Sthanakavasi sect",
         required="a dated historical record of the Sthanakavasi split"),
    dict(id="ABST-03", question="How many Agam texts do the Digambara Jains accept?",
         scan=r"Digambara[^.\n]{0,90}\b(twelve|eleven|ten|thirteen|12|11|10)\s+(Agam|Anga)",
         scope="all", missing="a count of Digambara Agam texts",
         required="a Digambara canonical list in this corpus"),
    dict(id="ABST-04", question="Who is the current acharya of the Terapanth tradition?",
         scan=r"(acharya|Acharya)[^.\n]{0,50}Terapanth|Terapanth[^.\n]{0,60}(acharya|Acharya)",
         scope="all", missing="the current Terapanth acharya",
         required="a current Terapanth succession record"),
    dict(id="ABST-05", question="How many Jains live in India according to the latest census?",
         scan=r"\b\d+(\.\d+)?\s*(million|crore|lakh)[^.\n]{0,40}(Jain|Jaina)",
         scope="all", missing="a census population figure for Jains",
         required="a census or survey record"),
    dict(id="ABST-06", question="How many Sthanakavasi monasteries (upasaras) exist today?",
         scan=r"Sthanakavasi[^.\n]{0,70}\b\d+\s*(monaster|upasar|asan)",
         scope="all", missing="a count of Sthanakavasi monasteries",
         required="a contemporary institutional survey"),
    dict(id="ABST-07", question="Exactly how long should one perform Samayika?",
         scan=r"Samayik[^.\n]{0,70}\b\d+\s*(minute|hour|hour)", scope="all",
         missing="a fixed duration for Samayika",
         required="a rule text stating a duration"),
    dict(id="ABST-08", question="How many verses does the Uttaradhyayana Sutra contain?",
         scan=r"Uttaradhyayan[^.\n]{0,70}\b\d+\s*(verse|sloka|sutra)", scope="all",
         missing="a verse count for the Uttaradhyayana Sutra",
         required="a metrical colophon or critical edition count"),
    dict(id="ABST-09", question="In which year was the Kalpa Sutra composed?",
         scan=r"Kalpa Sutra[^.\n]{0,90}\b(composed|written|compiled)[^.\n]{0,50}\b\d{3}\b",
         scope="all", missing="a composition year for the Kalpa Sutra",
         required="a dated composition record"),
    dict(id="ABST-10", question="How many Digambara monastic orders are there today?",
         scan=r"Digambara[^.\n]{0,70}\b\d+\s*(monastic order|orders|sects)", scope="all",
         missing="a count of Digambara monastic orders",
         required="a contemporary denominational survey"),
    dict(id="ABST-11", question="How many Jains live in Gujarat according to official statistics?",
         scan=r"Gujarat[^.\n]{0,70}\b\d+(\.\d+)?\s*(million|crore|lakh)", scope="all",
         missing="a Jain population figure for Gujarat",
         required="a state census tabulation"),
    dict(id="ABST-12", question="Is the Dṛṣṭivāda (Drastivada) Agam text available in this corpus?",
         scan=r"Book Title:[^\n]*(Drastivada|Dṛṣṭivāda|D.rstivada)", scope="all",
         missing="any Dṛṣṭivāda text",
         required="a Dṛṣṭivāda source with text"),
    dict(id="ABST-13", question="Does this corpus contain the original Prakrit text of the Acharanga Sutra?",
         scan=r"Book Title:[^\n]*(Acharanga|Acaranga)[^\n]*Prakrit", scope="all",
         missing="an original-language Acharanga source",
         required="a Prakrit Acharanga source in the manifest/corpus",
         known_scan=r"Acharanga|Acaranga", known_label="what the corpus does contain"),
    dict(id="ABST-14", question="What is the exact publication year of the JainQQ Pratikraman guide by Pravin K. Shah?",
         manifest_gap=("publication_year", ["SVK-2024"]),
         missing="a publication year for the JainQQ Pratikraman guide",
         required="a dated imprint for that source"),
    dict(id="ABST-15", question="What is the exact publication year of the Sthanakvasi Jain Itihas volume?",
         manifest_gap=("publication_year", ["SVK-2027"]),
         missing="a publication year for the Sthanakvasi Jain Itihas volume",
         required="a dated imprint for that source"),
    dict(id="ABST-16", question="What is the exact publication year of the Aupapatik Sutra JainQQ edition?",
         manifest_gap=("publication_year", ["SVK-2029"]),
         missing="a publication year for the Aupapatik Sutra JainQQ edition",
         required="a dated imprint for that source"),
    dict(id="ABST-17", question="Who wrote the work titled 'Jaina Psychology'?",
         manifest_gap=("author", ["SVK-1006"]),
         missing="an author name for 'Jaina Psychology'",
         required="a title page or bibliographic record naming the author"),
    dict(id="ABST-18", question="Who wrote 'Notes on the Jainas' (1911)?",
         manifest_gap=("author", ["SVK-1008"]),
         missing="an author name for 'Notes on the Jainas'",
         required="a bibliographic record naming the author"),
    dict(id="ABST-19", question="Who compiled 'Shri Utradhyayan Sutar' (1920)?",
         manifest_gap=("author", ["SVK-0016"]),
         missing="a compiler name for 'Shri Utradhyayan Sutar'",
         required="a title page naming the compiler"),
    dict(id="ABST-20", question="Who is the author of the Jain Shvetambar Conference Herald, Varsh 13?",
         manifest_gap=("author", ["SVK-1010"]),
         missing="an author for the Herald",
         required="a masthead naming the author"),
    dict(id="ABST-21", question="Does the Sthanakavasi tradition permit idol worship in temples?",
         scan=r"Sthanakavasi[^.\n]{0,80}\b(idol|image worship|image)", scope="all",
         missing="a stated Sthanakavasi position on idol worship",
         required="a passage stating that position",
         known_scan=r"idol", known_label="the general material the corpus does hold"),
    dict(id="ABST-22", question="How many years did Mahavira undertake penance before enlightenment?",
         scan=r"Mahavira[^.\n]{0,80}\b\d+\s*year[s]?\s*(of\s*)?penance", scope="all",
         missing="a duration for Mahavira's final penance",
         required="a canonical passage giving the duration"),
    dict(id="ABST-23", question="What is the total number of pages in the source titled 'Aupapatik Sutra'?",
         scan=r"Aupapatik[^.\n]{0,60}\b\d+\s*pages", scope="all",
         missing="a page count for that source",
         required="a collation record"),
    dict(id="ABST-24", question="Which modern Jain organisation is the largest by membership?",
         scan=r"(largest|biggest)[^.\n]{0,40}(Jain|Jaina)[^.\n]{0,40}(organis|organiz|samaj)",
         scope="all", missing="any membership ranking of Jain organisations",
         required="a comparative membership study"),
    dict(id="ABST-25", question="How many languages has the Agam literature been translated into completely?",
         scan=r"Agam[^.\n]{0,60}\btranslated into[^.\n]{0,30}\b\d+\s*(language|version)",
         scope="all", missing="a count of complete Agam translations",
         required="a translation survey"),
    dict(id="ABST-26", question="What is the exact date of Mahavira's nirvana?",
         scan=r"Mahavira[^.\n]{0,90}\bnirvana[^.\n]{0,40}\b\d{3}\s*(B\.?C|BCE|CE|A\.?D)",
         scope="all", missing="an exact dated record of Mahavira's nirvana in this corpus",
         required="a dated record",
         known_scan=r"nirvana|nirvaaNa", known_label="the material on nirvana the corpus does hold"),
    dict(id="ABST-27", question="How many manuscripts of the Acharanga are held in the Sthanakavasi libraries?",
         scan=r"Acharanga|Acaranga[^.\n]{0,80}\b\d+\s*manuscript", scope="all",
         missing="a manuscript count for the Acharanga",
         required="a library catalogue"),
    dict(id="ABST-28", question="What is the population of Jain monks and nuns today?",
         scan=r"\b\d[\d,]*\s*(Jain|Jaina)?\s*(monk|nun|muni|sadhu)[^.\n]{0,30}(today|now|present)",
         scope="all", missing="a current count of Jain monks and nuns",
         required="a contemporary ordination census"),
]

ABSTAIN_Q = [
    "{question}",
    "{question} Please answer only from the corpus sources.",
]


def build_abstention(cases, scans, anchors, known_hits, man_by_sid, allowed_sids):
    """Build abstention drafts whose absence claim was machine-verified."""
    out, dropped = [], []
    for c in cases:
        cid = c["id"]
        if c.get("scan"):
            n = scans.get(cid, 0)
            if n != 0:
                dropped.append({"id": cid, "reason": "absence scan matched %d corpus units" % n,
                                "pattern": c["scan"]})
                continue
        if c.get("manifest_gap"):
            field, sids = c["manifest_gap"]
            sids = [s for s in sids if s in allowed_sids]
            if not sids:
                dropped.append({"id": cid, "reason": "no rights-cleared source for manifest gap check"})
                continue
            def _populated(val):
                v = (val or "").strip().lower()
                return bool(v) and v not in ("unknown", "not recorded", "n/a", "none")
            if any(_populated(man_by_sid.get(s, {}).get(field)) for s in sids):
                dropped.append({"id": cid, "reason": "manifest field %s is populated" % field})
                continue
            anchor = {"source_id": sids[0], "unit_id": "manifest:%s" % sids[0], "quote": ""}
        else:
            anchor = anchors.get(cid)
            if not anchor:
                dropped.append({"id": cid, "reason": "no rights-cleared anchor source for the absence claim"})
                continue
        src_anchor = (known_hits.get(cid) or anchor)
        src = src_anchor["source_id"]
        if src not in allowed_sids:
            dropped.append({"id": cid, "reason": "anchor source %s not rights-cleared" % src})
            continue
        man = man_by_sid.get(src, {})
        label = attribution_label(man, src)
        parts = []
        kh = known_hits.get(cid) or {}
        src_anchor = kh or anchor
        known = kh.get("quote") or anchor.get("quote") or ""
        if known:
            parts.append('What the corpus does say: "%s" (%s).' % (known, label))
        parts.append("The corpus does not record %s, so this question cannot be answered from the "
                     "available sources." % c["missing"])
        parts.append("Evidence needed first: %s." % c["required"])
        answer = " ".join(parts)
        unit = {"unit_id": src_anchor.get("unit_id", "absence_scan:corpus"),
                "corpus_id": src_anchor.get("corpus_id", ""),
                "text": src_anchor.get("quote", ""), "section": "", "locator": {}}
        out.append(draft("ABSTENTION/INSUFFICIENT_EVIDENCE", "abstention", "abstention",
                         c["question"], answer, unit, src,
                         ["candidates_v2", "abstention_set"], "en",
                         {"absence_check": {
                             "case_id": cid,
                             "pattern": c.get("scan", ""),
                             "scope": c.get("scope", "all"),
                             "matches": 0,
                             "manifest_gap": list(c["manifest_gap"]) if c.get("manifest_gap") else None,
                             "anchor_source_id": src,
                             "anchor_unit_id": anchor.get("unit_id", ""),
                             "known_evidence_quote": known or "",
                         }},
                         quote=known,
                         manifest_grounded=bool(c.get("manifest_gap"))))
    return out, dropped
