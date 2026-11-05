# CLAUDE.md — Aerchain "Kill the Quote Spreadsheet" project

## Source of truth (mandatory)

`docs/00_source_of_truth.md` is the **canonical requirements reference**. It catalogues every requirement, edge case, example, AI constraint, deliverable, evaluation signal and permission in the original assignment (`docs/assignment.pdf`), with stable IDs (REQ-, FN-, EX-, EDGE-, AI-, DEL-, EVAL-, PERM-, LIM-, INFO-). Derived documents (`01`–`09`) are interpretations of it and never override it.

Rules:

1. **Check the source of truth first.** Before modifying the PRD, architecture, dataset, implementation plan or tests, check the relevant items in `docs/00_source_of_truth.md`, and cite their IDs in the change.
2. **Never weaken without approval.** Never remove or weaken an assignment requirement (narrowing scope, downgrading priority, making it optional, dropping its test or demo evidence) without explicitly flagging it to the user, citing the source-of-truth ID, and getting their approval first.
3. **Edge-case completeness.** Every named edge case (`EDGE-*`) must have a corresponding **dataset fixture**, **test**, and **demonstration strategy**. A gap in any of the three is a defect that must be reported.
4. **Coverage audit before readiness.** Never declare the project "ready to build" or "ready to submit" without first running a source-to-deliverable coverage audit against `docs/00_source_of_truth.md` (the format of `docs/09_source_coverage_audit.md`) and reporting its open findings.
5. **Go back to the PDF.** When documents disagree, or a review is based only on AI-generated documents, re-read `docs/assignment.pdf` directly rather than trusting the derived documents.
6. **The source of truth changes only with the assignment.** Edit `docs/00_source_of_truth.md` only if the assignment PDF itself changes, or to correct an extraction error. Flag either case to the user.
