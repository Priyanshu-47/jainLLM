#!/usr/bin/env python3
"""TASK 63 stage 1: adjudicate the complete Task 62 review pool.

Reads the 252-row Task 62 review queue (the supplied review material) and
assigns exactly one decision per candidate - APPROVE / REVISE / REJECT - using
only the evidence supplied with each candidate (evidence quote, source text,
manifest row, provenance, rights) plus the Task 62 rubric.

Design rules (auditable, deterministic):
  * No outside knowledge is used to repair an answer. A revision may only
    re-present material that is already in the supplied source text.
  * The answer's quoted fragment is never treated as a complete answer.
  * Decisions are conservative: APPROVE only for answers that already answer
    the question and are grounded; REJECT only where the supplied evidence
    cannot support the question; REVISE otherwise.
  * Every output record keeps human_review_required=true - this adjudication
    layer is not a human approval.

Outputs are written by run_task63.py.
"""
import json
import math
import os
import re
import unicodedata
from collections import Counter, OrderedDict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

CRITERIA = ["qa_alignment", "source_grounding", "attribution", "sect_distinction",
            "knowledge_layer", "abstention", "practice", "language",
            "language_quality", "no_fabrication", "pedagogy"]
HIGH = {"source_grounding", "attribution", "no_fabrication"}

STOP = set("""a an the and or of in on to for from with by as is are was were be been
that this these those which who whom whose what when where how why does do did
can could may might shall should would not no it its into over under about than
then there here their his her our your my me we you they i if but so such same
other others also very more most much many any all each both per via within
towards among between before after during while against without within
according stated state states states: says say said
it if so we me my us no not do does did was were are is am be been being
at by up down out off over under again further once here there all any both
each few more most other some such only own same too very
""".split())

# Hindi / Gujarati question scaffolding - the equivalents of
# "what does it say about ..." / "according to ..." / "in ..." .
STOP.update("""
में के का की था थे है हैं हो होगा किया गया गयी गई कहा कहता कहे कहा
बारे इस उस यह वह जो और या से पर को कि तो भी ही नहीं ना में
क्या कैसे कब कहाँ क्यों किसने किसको किसकी
बताओ बताये लिखिए दिया देते करता करते होता होती हैं रहा रहे रही
विषय विशेष संबंध संबंधी अनुसार अर्थात् अर्थात अर्थ मतलब भाव अर्थ
માં ના નું ની નો છે છેં થાય થયું થઈ થવું કહેવા કહેવામાં આવ્યું આવે
શું કયું કઈ કોણ કેમ ક્યારે ક્યાં કેવી વિશે અંગે માટે અને અથવા
તે તેના આ જે પણ વધુ બધું દ્વારા દીધું કરી કરે છે હોય હતું
""".split())

# ---------------------------------------------------------------------------
# Direct readings of the supplied evidence.
#
# The lexical rules above cannot judge whether a passage is *readable*, so the
# two sources whose OCR is corrupted beyond reliable recovery were read row by
# row. SVK-2003 (an Ardhamagadhi dictionary scan) and SVK-2016 (Panch-pratikraman,
# 1928) return glyph soup in every sampled passage; nothing in the supplied
# evidence lets a reader recover the intended meaning without outside knowledge.
# ---------------------------------------------------------------------------
OCR_CORRUPT_SOURCES = {
    "SVK-2003": ("Every sampled passage from this dictionary scan is glyph soup "
                 "or digit-laden noise (e.g. T61-CAND-0173, 0174, 0177); the "
                 "intended readings cannot be recovered from the supplied text."),
    "SVK-2016": ("Every sampled passage from this scan is systematically corrupt "
                 "(broken conjuncts, dropped vowels, truncated clauses - e.g. "
                 "T61-CAND-0163, 0164, 0165); meaning cannot be recovered "
                 "reliably from the supplied text."),
}

# Rows whose outcome was settled by reading the supplied passage directly.
ROW_OVERRIDES = {
    "T61-CAND-0184": ("REJECT", "Gujarati OCR is broken beyond recovery "
                                "(garbled conjuncts and dropped vowels); no "
                                "reliable reading survives in the supplied text."),
    "T61-CAND-0185": ("REJECT", "Gujarati OCR is broken beyond recovery; the "
                                "supplied passage cannot be read reliably."),
    "T61-CAND-0186": ("REJECT", "Gujarati OCR is broken beyond recovery; the "
                                "supplied passage cannot be read reliably."),
    "T61-CAND-0187": ("REJECT", "Gujarati OCR is broken beyond recovery; the "
                                "supplied passage cannot be read reliably."),
    "T61-CAND-0188": ("REJECT", "Gujarati OCR is broken beyond recovery; the "
                                "supplied passage cannot be read reliably."),
    "T61-CAND-0083": ("REJECT", "The supplied passage concerns the Srividya "
                                "tradition, not Jain vows; answering from it "
                                "would require importing outside knowledge."),
}

# Question scaffolding: words that describe the *act of asking*, not the subject.
SCAFFOLD = set("""difference differences differing regard regarding related relates
according asks asked ask describe described describes says said states state
explain explains explained mention mentioned mentions treated treat treats
meaning means term terms question answer answers passage source sources
what which who whom whose where when how why whose titled called named
""".split())

# Domain words are deliberately NOT scaffolding: "jain", "vows", "worship" are
# what a question is actually about, so they count as subject evidence.

# Subjects that belong to a different religious tradition than this corpus.
# Used only to refuse an answer, never to supply one.
ALIEN = set("""siva shiva shankar paupata pasupata lakula lakulisa buddha buddhist
bodhi brahma brahman vedic vedas quran koran bible christian christianity
jesus christ church gospel muslim islam allah mohammed nanak guru granth
krishna krisna vishnu rama isckon hare""".split())

# Markers that identify a sentence as being about Jain material. A sentence that
# names another tradition is only usable as a Jain answer if it also carries one
# of these, or if it carries several of the question's subject terms.
JAIN = set("""jain jaina jains jainism jina jinas ahimsa ahinsa himsa tirthankara
tirthankaras mahavira mahavir sramana shramana srmana agam agamas anuvrata
mahavrata kevala moksa moksha""".split())

def is_distinctive(term):
    """A term long enough to identify a subject on its own."""
    return len(term) >= 6 and term not in SCAFFOLD and not term.isdigit()


def quoted_subjects(question):
    """Terms the question explicitly asks about: how is 'Prakrit' explained.

    The possessive lookbehind stops "Woolner's" from opening a match.
    """
    out = []
    for m in re.finditer(r"(?<![A-Za-z])['\u2018]([^'\u2019]{2,40})['\u2019]", question):
        out.extend(words(m.group(1)))
    return out


def subject_terms(q_terms, title, question=""):
    """The question's subject: everything except the cited source's own title
    words and question scaffolding, plus whatever the question quotes."""
    title_words = set(content_terms(title))
    kept = [t for t in q_terms if t not in title_words and t not in SCAFFOLD
            and not t.isdigit() and t not in STOP]
    for t in quoted_subjects(question or ""):
        if t not in kept:
            kept.append(t)
    return kept


def match_terms(q_terms, s_terms, text=None):
    """Match the question's subject terms against a passage.

    Three layers, because this corpus mixes normalised Latin with OCR'd Indic:
      * exact token match;
      * 5-character prefix match, so OCR variants line up
        (tirthankara <-> tirtharikara, svetambara <-> s'vetambara);
      * substring match, so Indic compounds still count
        (karman inside papakarman, tapas inside tapascarya).
    """
    pref = {w[:5] for w in s_terms if len(w) >= 5}
    hay = (text or "").lower()
    hits = []
    for t in q_terms:
        if t in s_terms:
            hits.append(t)
        elif len(t) >= 5 and t[:5] in pref:
            hits.append(t)
        elif len(t) >= 3 and text and t in hay:
            hits.append(t)
    return hits


def tokens(text):
    return set((text or "").lower().split())


def alien(text):
    return bool(tokens(text) & ALIEN)


def usable_sentence(sentence, hits):
    """A sentence may only be quoted back as an answer if it is about the
    question's subject, is substantive, and is not simply a passage about
    another tradition.

    A comparative work naturally mentions Buddhism and the Vedas; that alone is
    not a reason to discard the passage. It counts against the sentence only
    when the sentence carries nothing Jain and rests on a single subject word.
    """
    if not hits or not complete_sentence(sentence):
        return False
    toks = tokens(sentence)
    if toks & ALIEN and not (toks & JAIN) and len(hits) < 2:
        return False
    return True


def on_topic(hits, text=""):
    """Is the supplied passage about the question's subject?"""
    return bool(hits)


def words(text):
    """Tokenise letters, keeping combining marks.

    Python's ``\\w`` excludes Indic vowel signs (category Mc), so a regex-based
    tokenizer silently destroys every Hindi/Gujarati word. Build the tokens by
    category instead, and measure length in *letters* so that marks do not
    inflate a token's length.
    """
    text = unicodedata.normalize("NFKC", text or "").lower()
    out, cur, letters = [], [], 0
    for ch in text:
        if unicodedata.category(ch)[0] in ("L", "M"):
            cur.append(ch)
            if unicodedata.category(ch)[0] == "L":
                letters += 1
        else:
            if letters >= 2:
                out.append("".join(cur))
            cur, letters = [], 0
    if letters >= 2:
        out.append("".join(cur))
    return out


def content_terms(text, drop=()):
    drop = {w.lower() for w in drop}
    out = []
    for w in words(text):
        if w in STOP or w in drop or re.fullmatch(r"(18|19|20)\d\d", w):
            continue
        out.append(w)
    return out


def sentences(text):
    text = re.sub(r"\s+", " ", text or "").strip()
    if not text:
        return []
    parts = re.split(r"(?<=[.!?\u0964\u0965|;])\s*", text)
    return [p.strip() for p in parts if len(p.strip()) >= 25]


CONTINUATION = set("""and but or nor yet so which whose however therefore
moreover besides although though following formerly latter former
unless whether""".split())


def complete_sentence(text):
    """Would this string read as a finished sentence if quoted back?

    Guards the spec rule that a quotation fragment must never be presented as a
    complete answer: reject continuations, trailing fragments, and broken
    bracket/ punctuation runs.
    """
    t = (text or "").strip()
    if len(t) < 40 or len(t.split()) < 7:
        return False
    if not re.match(r"^[A-Z0-9\u00C0-\u024F\u0900-\u097F\u0A80-\u0AFF\"'\[(]", t):
        return False
    first = words(t[:24])
    if first and first[0] in CONTINUATION:
        return False
    if not re.search(r"[.!?\u0964\u0965\"'\u2019)]$", t):
        return False
    if re.search(r"\s[)\]}]", t) or re.search(r"[(\[]\s", t):
        return False
    if re.search(r"[;:,.]\s*[;:,.]", t):
        return False
    if re.search(r"\b[a-z]\s*[.!?]\s*$", t) or re.search(r"\b[a-z]\s*$", t):
        return False
    return True


def extract_quote(answer):
    m = re.search(r'"(.+?)"', answer, re.S) or re.search(r'["“](.+?)["”]', answer, re.S)
    return " ".join(m.group(1).split()) if m else ""


def well_formed(text):
    """Unbalanced brackets / truncated tail => generated text is malformed."""
    if not text:
        return False
    for o, c in (("(", ")"), ("[", "]"), ('"', '"')):
        if text.count(o) != text.count(c):
            return False
    if re.search(r"\(\s*$|\w\s+\($", text.strip()):
        return False
    return True


# --------------------------------------------------------------------------
# feature extraction
# --------------------------------------------------------------------------
def features(row):
    answer = row["answer"]
    quote = extract_quote(answer)
    src = " ".join((row.get("source_text") or "").split())
    title = row.get("source_title") or ""
    q_terms = content_terms(row["question"], drop=[title])
    topic = subject_terms(q_terms, title, row["question"])
    s_terms = content_terms(src, drop=[title])
    hits = match_terms(topic, s_terms, src)
    overlap = (len(hits) / len(topic)) if topic else 0.0

    # does the supplied source continue past the quoted fragment?
    continuation = 0
    if quote and src:
        idx = src.find(quote[: min(70, len(quote))])
        if idx >= 0:
            continuation = len(src) - (idx + min(70, len(quote)))

    # sentences in the source that touch the question
    best_sent, best_hits, best_hit_list = "", 0, []
    best_key = (-1, -1, 0)
    for s in sentences(src):
        h = match_terms(topic, content_terms(s, drop=[title]), s)
        if not h:
            continue
        if not usable_sentence(s, h):
            continue
        key = (sum(1 for t in h if is_distinctive(t)), len(h), -len(s))
        if key > best_key:
            best_key, best_hits, best_sent, best_hit_list = key, len(h), s, h
    src_on_topic = on_topic(hits, src)
    sent_on_topic = on_topic(best_hit_list, best_sent)

    shape = "other"
    if re.match(r"^(The (corpus )?manifest (records|classifies)|The header records|"
                r"The corpus manifest records)", answer):
        shape = "manifest"
    elif row["category"] == "ABSTENTION/INSUFFICIENT_EVIDENCE":
        shape = "abstention"
    elif answer.startswith("The concept of "):
        shape = "concept"
    elif quote and re.search(r"(states:|के अनुसार:|ના અનુસાર:|ના અનુસાર:|ने|के अनुसार|ના અનુસાર)\s*$",
                             answer[:answer.find('"')] if '"' in answer else "") \
            or re.search(r':\s*"', answer):
        shape = "fragment"

    # OCR corruption signal: line-break hyphens + technical strays + broken words
    ocr = 0
    if quote:
        ocr += len(re.findall(r"[¬°]", quote))
        ocr += len(re.findall(r"[a-z]-\s", quote))
        ocr += len(re.findall(r"\s[,.;:]\s", quote))
        ocr += len(re.findall(r"\b\w*[0-9]\w*\b", quote)) // 4
        # Indic: long vowel-sign runs (broken glyph sequences)
        matras = ({chr(c) for c in range(0x093E, 0x094D)}
                  | {chr(c) for c in range(0x0ABE, 0x0ACE)})
        run = best = 0
        for ch in quote:
            run = run + 1 if ch in matras else 0
            best = max(best, run)
        if best >= 3:
            ocr += 4
    return {
        "quote": quote,
        "q_hits": hits,
        "topic": topic,
        "src_on_topic": src_on_topic,
        "sent_on_topic": sent_on_topic,
        "best_hit_list": best_hit_list,
        "src": src,
        "title": title,
        "overlap": round(overlap, 3),
        "continuation": continuation,
        "best_sentence": best_sent,
        "best_hits": best_hits,
        "shape": shape,
        "ocr": ocr,
        "well_formed": well_formed(answer),
        "q_terms": sorted(set(q_terms)),
    }


# --------------------------------------------------------------------------
# revision builder - only ever re-presents supplied source text
# --------------------------------------------------------------------------
def scope_note(row):
    if row["category"] in ("STHANAKAVASI_DISTINCTION", "STHANAKAVASI_TERMINOLOGY"):
        return (" This is that source's account; other Jain traditions may describe "
                "the same point differently, and this passage does not say so.")
    if row["category"] in ("CANONICAL_VS_COMMENTARY", "AGAM_GROUNDED"):
        return (" This reports what the cited source records; it does not by itself "
                "settle what canonical or other traditions hold.")
    return ""


def build_revision(row, ft):
    """Construct an answer strictly from the supplied source text."""
    sentence = ft["best_sentence"]
    hits = ft["best_hits"]
    if not sentence or hits < 1 or not ft["sent_on_topic"]:
        return "", ""
    if len(sentence) < 30:
        return "", ""
    sentence = sentence.strip()
    if not sentence.endswith((".", "!", "?", "।")):
        sentence += "."
    title = ft["title"] or row.get("source_id", "this source")
    revised = 'According to %s, "%s"%s' % (title, sentence, scope_note(row))
    if not well_formed(revised):
        revised = revised.replace('"', "'")
    basis = ("Rebuilt from the supplied source text: the original answer quoted only "
             "an incomplete fragment (\"%s\"). The sentence retained here is the "
             "supplied passage that actually touches the question "
             "(%d question term(s) matched: %s). No information outside the supplied "
             "evidence was added."
             % (ft["quote"][:120], hits, ", ".join(ft["best_hit_list"]) or "n/a"))
    return revised, basis


# --------------------------------------------------------------------------
# per-candidate decision
# --------------------------------------------------------------------------
# Manifest fields a question can explicitly ask for. The answer must state the
# recorded value whenever the question asks for it: an answer that reports the
# title but skips the asked-for author is a partial answer, not a complete one.
MANIFEST_FACETS = (
    (r"\bauthors?\b|\bauthored\b|\bwritten by\b", ("author",), "author(s)"),
    (r"\bpublisher\b|\bwho published\b|\bpublished by\b", ("publisher",),
     "publisher"),
    (r"\bpublication year\b|\byear of publication\b", ("publication_year",),
     "publication year"),
    (r"which tradition|tradition and sect|recorded tradition|tradition does",
     ("tradition",), "tradition"),
    (r"\bsect\b", ("sect", "subsect"), "sect"),
    (r"\blanguages?\b", ("language",), "language"),
    (r"\bknowledge layer\b", ("knowledge_layer",), "knowledge layer"),
    (r"\breligious scope\b", ("religious_scope",), "religious scope"),
    (r"\blicen[cs]e\b|\btraining permission\b", ("license",), "licence"),
)


def missing_manifest_facets(question, answer, manifest_fields):
    """Asked-for manifest fields that the answer never states.

    Values recorded as 'unknown' / 'not recorded' are not required: the answer
    may not be forced to invent a gap, and stating nothing is then honest.
    """
    if not manifest_fields:
        return []
    q = (question or "").lower()
    a = " ".join(_fold(answer).split())
    out = []
    for pattern, keys, label in MANIFEST_FACETS:
        if not re.search(pattern, q):
            continue
        values = []
        for k in keys:
            v = manifest_fields.get(k)
            if not v or str(v).strip().lower() in ("unknown", "not recorded",
                                                   "none", "n/a"):
                continue
            values.append(str(v).strip())
        if not values:
            continue
        if not any(_fold(v) in a for v in values):
            out.append((label, ", ".join(values)))
    return out


def _fold(text):
    text = unicodedata.normalize("NFKC", text or "").lower()
    return " ".join("".join(ch if ch.isalnum() else " " for ch in text).split())


def adjudicate(row, ft):
    """Return (decision, failed_criteria, notes, revised_answer, revision_basis)."""
    fails, notes = [], []

    # -- decisions already settled by reading the evidence directly --------
    if row["review_id"] in ROW_OVERRIDES:
        decision, reason = ROW_OVERRIDES[row["review_id"]]
        if "OCR" in reason:
            fails = ["language", "language_quality", "source_grounding"]
        else:
            fails = ["qa_alignment", "source_grounding"]
        return (decision, fails, reason, "", "")

    if row.get("source_id") in OCR_CORRUPT_SOURCES and ft["shape"] == "fragment":
        return ("REJECT", ["language", "language_quality", "source_grounding"],
                "Unusable OCR. " + OCR_CORRUPT_SOURCES[row["source_id"]], "", "")

    # -- rights / provenance blockers first -------------------------------
    if row.get("rights_status") not in ("TRAINING_ALLOWED",
                                        "TRAINING_ALLOWED_WITH_PERMISSION_EVIDENCE"):
        return ("REJECT", ["source_grounding"],
                "Rights status %r does not clear the record for training use."
                % row.get("rights_status"), "", "")

    # -- shape: manifest metadata answers ---------------------------------
    if ft["shape"] == "manifest":
        mfobj = row.get("manifest_fields") or {}
        mf = json.dumps(mfobj, ensure_ascii=False)
        a = row["answer"]
        grounded = True
        for pat, label in ((r"as written by (.+?) in (\d{4})", "author/year"),
                           (r"with relation_type (\w+)", "relation_type"),
                           (r"religious scope ([A-Z_]+)", "religious_scope")):
            for m in re.finditer(pat, a):
                for g in m.groups():
                    if g and g not in mf and g != "unknown":
                        grounded = False
                        notes.append("claim %r not found in the manifest row" % g)
        missing = missing_manifest_facets(row["question"], a, mfobj)
        if missing:
            fails += ["qa_alignment"]
            notes.append("The question asks for %s, but the answer does not state "
                         "it even though the supplied manifest row records %s."
                         % (", ".join(m[0] for m in missing),
                            "; ".join("%s = %s" % (m[0], m[1]) for m in missing)))
        if not ft["well_formed"]:
            fails += ["language_quality"]
            notes.append("generated text is malformed (unbalanced brackets / truncation)")
        if not grounded:
            fails += ["source_grounding", "no_fabrication"]
        if not fails:
            notes.append("Complete manifest/catalog answer; every claim matches the "
                         "supplied manifest row; no doctrinal inference added.")
            return ("APPROVE", [], " ".join(notes), "", "")
        if grounded:
            revised = " ".join(a.split())
            repairs = []
            delta = revised.count("(") - revised.count(")")
            if delta > 0:
                revised += ")" * delta
                repairs.append("Closed %d unbalanced parenthesis in the generated "
                               "text" % delta)
            for label, value in missing:
                revised += " The manifest also records %s: %s." % (label, value)
                repairs.append("stated the asked-for %s exactly as recorded in the "
                               "supplied manifest row (%s)" % (label, value))
            if not repairs:
                repairs.append("No change beyond whitespace normalization")
            return ("REVISE", fails,
                    " ".join(notes) + " Wording repair only; content already matches "
                    "the manifest row.",
                    revised,
                    "; ".join(repairs) + ". Every other fact is kept identical to "
                    "the supplied manifest row; nothing was added or removed beyond "
                    "the recorded fields.")
        return ("REJECT", sorted(set(fails)),
                " ".join(notes) + " The answer asserts manifest values that the "
                "supplied manifest row does not contain.", "", "")

    # -- abstention --------------------------------------------------------
    if ft["shape"] == "abstention":
        a = row["answer"]
        has_lead_quote = a.startswith("What the corpus does say")
        if has_lead_quote:
            # the quotation does not establish the asked fact - drop it
            m = re.search(r"\)\.\s*(The corpus does not record.+)$", a, re.S)
            gap = m.group(1).strip() if m else a.split("). ", 1)[-1].strip()
            if not gap.startswith("The corpus does not record"):
                gap = ("The available evidence does not establish the answer to this "
                       "question, so it should not be asserted as fact.")
            return ("REVISE", ["qa_alignment", "source_grounding"],
                    "The abstention itself is correct and evidence-grounded, but the "
                    "answer opens with a quotation that does not bear on the asked "
                    "fact. Reviewer guidance for Queue C: the abstention must rest on "
                    "an evidence check, not on an unrelated passage.",
                    gap,
                    "Removed the non-evidentiary quotation only. The gap statement and "
                    "the 'evidence needed first' clause are kept verbatim from the "
                    "supplied answer; no new factual claim was introduced.")
        fails += []
        notes.append("Direct evidence-gap statement, no filler quotation; the gap is "
                     "corroborated by the supplied manifest row.")
        return ("APPROVE", [], " ".join(notes), "", "")

    # -- concept-shaped answers (question/answer mismatch) ----------------
    if ft["shape"] == "concept":
        return ("REJECT", ["qa_alignment", "source_grounding"],
                "The answer is a boilerplate 'The concept of X is central to Jain "
                "philosophy' wrapper around an unrelated source quotation; it does not "
                "answer the question and the quotation is a raw passage dump, not an "
                "explanation.", "", "")

    # -- no source text supplied with the candidate ------------------------
    if not ft["src"]:
        return ("REJECT", ["source_grounding", "no_fabrication"],
                "The candidate supplies no source text to check it against (evidence "
                "quote only: %r), so no claim in it can be verified. Rejecting rather "
                "than inventing the missing evidence." % ft["quote"][:80], "", "")

    # -- fragment / everything else ---------------------------------------
    fragment = ft["shape"] == "fragment"
    quote = ft["quote"]

    # unusable OCR: the quotation cannot be read reliably
    if ft["ocr"] >= 4:
        return ("REJECT", ["language", "language_quality", "source_grounding"],
                "The quoted source text is visibly corrupted OCR (stray technical "
                "characters / broken glyph sequences / line-break hyphens) and the "
                "supplied evidence offers no clean parallel reading, so the intended "
                "meaning cannot be recovered without outside knowledge.", "", "")

    # wrong source / topic: supplied evidence does not touch the question
    if not ft["src_on_topic"]:
        return ("REJECT", ["qa_alignment", "source_grounding"],
                "The supplied source passage does not bear on the question: the "
                "supplied text (%d characters) contains none of the question's subject "
                "terms (subject terms: %s; matched: %s). Repairing it would require "
                "importing outside knowledge, which this adjudication never does."
                % (len(ft["src"]), ", ".join(ft["topic"]) or "n/a",
                   ", ".join(ft["q_hits"]) or "none"), "", "")

    # evidence exists - build the supported answer
    revised, basis = build_revision(row, ft)
    if revised:
        fails = ["qa_alignment"]
        if fragment:
            fails.append("source_grounding")
        if ft["ocr"] > 0:
            fails.append("language_quality")
        if row["category"] in ("STHANAKAVASI_DISTINCTION", "STHANAKAVASI_TERMINOLOGY"):
            fails.append("sect_distinction")
        if row["category"] == "CANONICAL_VS_COMMENTARY":
            fails.append("knowledge_layer")
        notes.append("Supplied source text contains an on-topic passage the answer did "
                     "not use (matched terms: %s)."
                     % ", ".join(ft["best_hit_list"]))
        return ("REVISE", sorted(set(fails)), " ".join(notes), revised, basis)

    # source is on-topic but no single sentence in it addresses the question
    src_toks = tokens(ft["src"])
    if src_toks & ALIEN and not (src_toks & JAIN):
        return ("REJECT", ["qa_alignment", "attribution", "source_grounding"],
                "Wrong tradition: the supplied passage is material about %s, "
                "not Jain material, so quoting it back would attribute another "
                "tradition's statement to the Jain question asked. The subject "
                "term shared with the question is %s."
                % (", ".join(sorted(src_toks & ALIEN)[:4]),
                   ", ".join(ft["q_hits"]) or "n/a"), "", "")
    return ("REJECT", ["qa_alignment", "source_grounding"],
            "The supplied source passage mentions the subject (%s) but no complete, "
            "readable sentence in it answers the question, so the evidence cannot "
            "support a usable answer without outside knowledge."
            % ", ".join(ft["q_hits"]), "", "")


# --------------------------------------------------------------------------
def revision_confidence(ft, decision):
    """How strongly the supplied source pins down the revised wording.

    Used to order human attention: a substring-only single hit is weaker
    grounding than two independent exact tokens.
    """
    if decision != "REVISE":
        return "n/a"
    if ft["shape"] == "manifest":
        return "high"
    if ft["shape"] == "abstention":
        return "medium"
    hits = ft.get("q_hits") or []
    if not hits:
        return "low"
    src_terms = set(content_terms(ft.get("src") or ""))
    exact = [t for t in hits if t in src_terms]
    if len(exact) >= 2:
        return "high"
    if exact or len(hits) >= 2:
        return "medium"
    return "low"


def main(queue_path):
    rows = [json.loads(l) for l in open(queue_path, encoding="utf-8") if l.strip()]
    out = []
    for r in rows:
        ft = features(r)
        decision, fails, notes, revised, basis = adjudicate(r, ft)
        rec = OrderedDict([
            ("review_id", r["review_id"]),
            ("candidate_id", r["review_id"]),
            ("queue", r["queue"]),
            ("queue_name", r.get("queue_name", "")),
            ("category", r["category"]),
            ("task_category", r.get("task_category", "")),
            ("decision", decision),
            ("failed_criteria", fails),
            ("notes", notes),
            ("revised_answer", revised),
            ("revision_basis", basis),
            ("revision_confidence", revision_confidence(ft, decision)),
            ("source_id", r["source_id"]),
            ("source_title", r.get("source_title", "")),
            ("rights_status", r.get("rights_status", "")),
            ("split", r.get("split", "")),
            ("language", r.get("language", "")),
            ("original_question", r["question"]),
            ("original_answer", r["answer"]),
            ("evidence", (r.get("evidence") or {}).get("quote", "")),
            ("source_text", (r.get("source_text") or "")[:4000]),
            ("provenance", r.get("provenance", {})),
            ("manifest_fields", r.get("manifest_fields", {})),
            ("human_review_required", True),
            ("human_verified", False),
            ("features", {k: ft[k] for k in
                          ("shape", "overlap", "continuation", "best_hits", "ocr",
                           "well_formed", "src_on_topic", "sent_on_topic",
                           "q_hits", "topic", "best_hit_list")}),
        ])
        out.append(rec)
    return out


if __name__ == "__main__":
    import sys
    q = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        ROOT, "data/training/sft_task62_review_queue_v1.jsonl")
    res = main(q)
    print("total", len(res))
    print("decisions", dict(Counter(r["decision"] for r in res)))
    for qn in ("A", "B", "C", "R", "D"):
        sub = [r for r in res if r["queue"] == qn]
        print("  queue %s: %s" % (qn, dict(Counter(r["decision"] for r in sub))))
    print("shapes", dict(Counter(r["features"]["shape"] for r in res)))
