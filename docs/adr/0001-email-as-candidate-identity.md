# 1. Normalized Email is the Candidate identity

Date: 2026-10-26

## Status

Accepted

## Context

The source export carries two plausible identifiers per Candidate, and they
contradict each other:

- `candidate_id` looks like a primary key, but the export reuses `C-1010` for two
  demonstrably different people (different names, emails, and Regions).
- `email` repeats across *different* `candidate_id` values for what is clearly one
  person — once as a case-and-whitespace variant (`"  Alicia.Trent@Gmail.com "`),
  once with an abbreviated name and different contact details.

Exactly one of them can be the identity, and the choice determines what
deduplication even means.

## Decision

**Normalized Email** (trimmed, lowercased) is the Candidate identity, with a unique
constraint. `candidate_id` is retained as **Legacy Candidate ID**: a non-unique
column kept for traceability back to the source system.

A Source Row with no usable email is therefore **rejected**, because it has no
identity.

## Consequences

Good:

- The `C-1010` collision stops being a conflict to resolve — two emails means two
  Candidates, which is the factually correct outcome.
- Deduplication becomes a single unambiguous rule applied consistently, rather than
  a per-case judgement.
- It matches how a recruiting platform actually re-identifies people across sources.

Bad / accepted:

- Three Source Rows are rejected purely for email problems, including one with an
  otherwise complete record (`C-1035`, email missing entirely). We lose that
  Candidate rather than inventing a surrogate identity for them.
- A Candidate who legitimately changes email appears as a new Candidate. Acceptable
  for an import slice; a production system would need an identity-merge workflow.
- Email is user-supplied data acting as a key. Shared inboxes
  (`careers@company.com`) would collapse distinct people. Not present in this
  dataset; worth revisiting before trusting it at scale.
