# Task 7 — Finalized Rights Outreach Package

**Date:** 2026-09-18 · **Status:** package finalized. **Nothing has been sent.** No corpus, gate, manifest or release changes were made in this task. The package is staged for a human decision to initiate contact.

## 1. PACKAGE CONTENTS

| file | role |
|---|---|
| `docs/rights_request_svk_0002_final.md` | **Send-ready letter** for SVK-0002: accurate work/author identification; two authority questions first (identify the rights holder; does the recipient claim custodial authority); then the six separate, individually-grantable permission options A–F; attribution/restriction question; explicit non-assumption of permission |
| `docs/rights_identification_inquiry_svk_0008_0009_0018.md` | **Send-ready identification inquiry** for the three related works: author/speaker/publisher identification and rights-contact pointers only; one framed question on whether the Conference claims authority over its historical publications; no ownership confirmation demanded |
| `docs/rights_response_template.md` | Response record template (who, authority claimed, works, A–F decisions, conditions, attribution, expiry, evidence) with rules preventing silent promotion of a reply to a gate decision |
| `data/reports/rights_outreach_register.csv` | Register updated: `contact_found`/`contact_method` carry the verified routes; `outreach_status` per source now shows the staged route; factual rights fields untouched |
| `data/reports/task6_contact_verification.md` | Evidence base for every route and confidence grade below |
| `data/reports/task5_rights_outreach.md` | Original package rationale and rights questions |

## 2. CONTACT ROUTING TABLE

| Work | Proposed route | Route confidence | Why this route | Rights-holder status | Permission status |
|---|---|---|---|---|---|
| SVK-0002 *Jain Dharma* (1958) | **PRIMARY (CONTACT ROUTE ONLY):** International Mahavira Jain Mission / Siddhachalam Jain Tirth, 111 Hope Road, Blairstown NJ 07825, USA · (908) 362-9793 · site contact form | HIGH (from IMJM/Siddhachalam's own site; phone continuity with the 1994 IJM listing) | The ashram was **founded by the author** (1983) and is owned and managed by his mission (IMJM) — the most direct living connection to the author's lineage, and the natural first ask for "who controls the rights?" | **NOT ESTABLISHED.** No evidence IMJM/Siddhachalam owns rights in the 1958 work (published in New Delhi 25 years before Siddhachalam existed). Route ≠ rights holder. | **NONE.** Gate: NEEDS_PERMISSION (R92_TERM_UNEXPIRED, term to 2054). Letter asks for identification + optional A–F permissions; nothing assumed. |
| SVK-0002 *Jain Dharma* (1958) | **SECONDARY:** Conference via its Dharmik Sandesh presenting platform (jinsharnammedia.com) | LOW (intermediary — platform belongs to a Digambar trust, not the Conference) | The Conference is the **publisher of record**; the series is the Conference's currently-verifiable activity, and the platform exposes a contact form | Not established. Publisher-of-record status is imprint evidence, not proof of present rights-holding. | None. |
| SVK-0008 (1960 conduct manual) | **CANDIDATE/INTERMEDIARY:** same Conference channels as SVK-0009 | LOW–MEDIUM | Author and publisher unknown; the Conference milieu is the most plausible path to identification | UNKNOWN (no author/publisher recorded in DLI metadata) | Gate: WITH_CONDITIONS (R95_CHRONOLOGY_UNRESOLVED). Inquiry asks for identification only. |
| SVK-0009 (1941 institutional history) | **CANDIDATE/INTERMEDIARY:** Conference channels — postal to historic "Conference Bhavan, New Delhi" (currency unverified); Dharmik Sandesh platform; *Jain Herald* editor (Pune, currency unverified) | LOW–MEDIUM (none is an official, verified Conference contact) | The work **is** the Conference's institutional history — the Conference (or its successor officeholders) is the most plausible authority on who compiled it and who holds rights | UNKNOWN; Conference is the plausible first recipient of the identification question — a possible outreach route, NOT evidence of ownership | Gate: WITH_CONDITIONS (R95_CHRONOLOGY_UNRESOLVED). |
| SVK-0018 (1960 pravachan collection) | **CANDIDATE/INTERMEDIARY:** same Conference channels as SVK-0008 | LOW–MEDIUM | Speaker and publisher unknown; same identification logic | UNKNOWN | Gate: WITH_CONDITIONS (R95_CHRONOLOGY_UNRESOLVED). |

Standing separation maintained throughout: **CONTACT ROUTE ≠ RIGHTS HOLDER ≠ PERMISSION.** No recipient is described anywhere in the package as a rights holder.

## 3. RESPONSE DECISION CHECKLIST

Applies to any reply to either letter. Record every reply via `docs/rights_response_template.md` **before** any other action; attach or quote the original message as evidence. The gate never changes from a reply directly — only through the normal pipeline (`manifest` → `gate`) after the record is reviewed.

**If the recipient…**

1. **…confirms they are the rights holder** — record `authority_claimed` verbatim; assess what supports it (role, org position, history). If plausible: they may answer A–F; fill the decisions, conditions, attribution, expiry. If authority remains thin (e.g., "we published it long ago" without position/evidence), mark the permission *provisional* and request written confirmation. Only then re-run the gate with the new evidence fields and let the pipeline decide; the gate remains fail-closed meanwhile.
2. **…identifies another rights holder** — update the register's `likely_rights_holder` + `rights_holder_evidence` with the pointer and its source; send the same package to the new contact (no new research needed); keep the original reply as evidence of the chain. No gate change.
3. **…grants RAG only (B)** — record A+B as granted, C/D/E/F as not granted. Feasible pipeline outcome: text could be admitted to the RAG product with attribution per conditions, never to training. Re-run gate; expect a RAG-only admission with conditions recorded.
4. **…grants training only (C)** — record it; ask whether D (redistribution) is included, since training without redistribution is still viable (training corpus remains internal). Re-run gate; route to training only, RAG per what was actually granted.
5. **…grants both RAG and training** — record each separately with conditions; re-run gate; both routes open per grant scope.
6. **…grants redistribution (D)** — record alongside whichever use rights were granted; the release builders must then embed the required attribution string in dataset cards/manifests; if D is granted without A/B, treat as unusable-without-a-use-grant and confirm intent.
7. **…imposes attribution requirements or restrictions** — copy them verbatim into the record (wording, placement, scope); any condition the pipeline cannot technically enforce must be accepted, renegotiated, or declined **before** use — never silently ignored.
8. **…declines permission** — record the decline verbatim, thank them, close the register row (outreach_status → DECLINED). The source stays quarantined permanently unless the rights position changes. Do not seek the same text through other channels to circumvent a decline.
9. **…cannot determine rights / no response** — record the outcome; the source stays gate-blocked (UNKNOWN/NEEDS_PERMISSION as applicable). Silence is not permission. Re-approach only via a different verifiable contact, not by assuming.

**Cross-cutting rules:** separate rights stay separate (a general "yes, use it" grants A at most); verbal statements get written confirmation before any gate evidence is entered; every record preserves who/authority/work/rights/conditions/when/evidence; nothing here constitutes a legal conclusion beyond the recorded evidence.

## 4. REGISTER UPDATE

`data/reports/rights_outreach_register.csv`: `outreach_status` set to `READY_TO_SEND` for SVK-0002 (route: IMJM/Siddhachalam — contact route only) and `READY_TO_SEND_IDENTIFICATION` for SVK-0008/0009/0018 (route: Conference candidate channels). Factual rights columns (`current_license_status`, `current_license_rule`, `likely_rights_holder`, `rights_holder_evidence`) **unchanged**.

## 5. WHAT BLOCKS SENDING (resolved only by the user, not the agent)

1. A human decision to initiate contact at all (project policy; agent does not send).
2. Choice of channel per letter (form vs phone vs postal), since every Conference channel is intermediary/candidate.
3. Sender identity (name/role/email) to fill the signature blocks.
4. Attention line for the IMJM/Siddhachalam letter, if a specific office is known at send time.
5. Optional: any review the user wants from a legally informed person before sending — the package deliberately makes no legal claims beyond recorded evidence.

## 6. CONSISTENCY CHECK

- Both letters and the routing table name the works/authors identically to `manifests/source_manifest.csv` (checked: titles, authors, years, publisher strings).
- Routing table and Task 6 report agree on every confidence grade and on the route/ownership separation.
- No file in the package asserts rights ownership or existing permission for any work.
- Corpus, gate decisions, manifests, and release untouched by this task.
