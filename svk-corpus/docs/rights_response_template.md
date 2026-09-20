# Rights Response Record — Template

Fill one copy of this template **per response** (email, letter, or meeting) and save it as
`data/reports/rights_responses/<source_id>_<YYYY-MM-DD>.md`. A response is **evidence**, not
a verdict: the licence gate is re-run afterwards and remains fail-closed until the record
answers *who*, *what authority*, *which work*, *which rights*, *what conditions*, *when*.
An informal or verbal statement is never promoted to `TRAINING_ALLOWED` by this record alone.

```markdown
# Rights Response Record

## Meta
- **date:**                    (date the response was received)
- **received_via:**            (email / letter / meeting / phone — attach or quote the evidence)
- **respondent:**              (name)
- **respondent_role:**         (role/title)
- **organization:**            (organization)
- **authority_claimed:**       (what the respondent says they have: rights owner / authorised
                                representative / speaking on behalf of X / opinion only)
- **authority_evidence:**      (what supports the claimed authority, if anything)
- **evidence:**                (file reference or verbatim quote; store the original message
                                in data/reports/rights_responses/attachments/)

## Work(s) covered
- **work(s):**                 (source_ids and titles, e.g. SVK-0002 — Jain Dharma (1958))
- **edition/coverage:**        (which editions/printings the answer applies to)

## Decisions (mark exactly one per line: YES / NO / NOT ADDRESSED)
- **reading_research_use (A):**
- **rag_retrieval_use (B):**
- **model_training_use (C):**
- **redistribution (D):**
- **commercial_use (E):**
- **derived_works (F):**

## Conditions
- **conditions:**              (conditions as stated by the respondent, verbatim where possible)
- **attribution_requirements:** (exact wording/placement required, if specified)
- **expiry_or_review:**        (time-limited permission? review date?)
- **additional_restrictions:** (anything else stated)

## Project evaluation (completed by the project, not the rights-holder)
- **gate_relevant:**           (which gate rule this evidence addresses, e.g. R92_TERM_UNEXPIRED)
- **sufficiently_documented:** (YES/NO — does the record answer who/authority/work/rights/conditions/when)
- **gate_action:**             (none / re-run gate with new evidence fields / request written confirmation)
- **follow_up_needed:**        (list of open items)

## Notes
- 
```

**Rules for completing this record**

1. **Separate rights stay separate.** A "yes, you may use it" answers (A) at most. (C) training
   and (D) redistribution are recorded only if explicitly granted.
2. **Authority before scope.** If `authority_claimed` is vague ("I am a trustee", "we published
   it long ago"), note it and treat the permission as provisional until authority is
   documented. The register's `rights_holder_evidence` column must be updatable from this
   record.
3. **No silent upgrades.** The gate's decision for a source changes only through the normal
   pipeline (`manifest` → `gate`) after the evidence fields above are filled and reviewed —
   never by editing manifests by hand.
4. **Store the original.** The quoted email/letter file reference in `evidence` is mandatory;
   a summary without the original is not documentation.
