# Glossary

Canonical vocabulary for this project. If a term here has a definition, use that
term — not a synonym.

## Candidate

A person who has applied for a role. Identified by their **Normalized Email**.
A Candidate belongs to exactly **one** Region.

## Normalized Email

A Candidate's email with surrounding whitespace stripped and the whole string
lowercased. This is the Candidate's identity. Two Source Rows with the same
Normalized Email describe the same Candidate, regardless of what any other column
says.

## Legacy Candidate ID

The `candidate_id` column from the source export. Retained for traceability only.
It is **not** an identity: the source data reuses one value for two different
Candidates, so it carries no uniqueness guarantee.

## Region

One of six canonical codes: `US-MW`, `US-NE`, `US-SE`, `US-W`, `PH-MNL`, `CO-BOG`.
A Candidate has one Region. A Recruiter has a *set* of Assigned Regions. Visibility
is therefore **set membership**, never equality.

## Recruiter

A user of the platform. Has a set of Assigned Regions, or is an Admin.

## Admin

A Recruiter with global visibility — every Candidate in every Region. Represented
as `*` in the source roster.

## Assigned Regions

The set of Regions a non-Admin Recruiter may see Candidates in. Empty for an Admin,
whose visibility does not depend on it.

## Candidate Status

Where a Candidate sits in the hiring pipeline: `active`, `screening`,
`interviewing`, `withdrawn`. A property of a **person**.

Distinct from Import Outcome. Do not call either one "status" unqualified.

## Import Outcome

What happened to a single Source Row during an Import: `imported`, `merged`, or
`rejected`. A property of a **row**, not a person.

## Source Row

One data row of the uploaded CSV. Numbered from 1, excluding the header. A rejected
Source Row is reported back by this number.

## Import

One `POST` of a CSV. Produces an Import Report.

## Import Report

The result of an Import: how many Candidates were created, how many were Merged,
and every rejected Source Row with its reason.

## Merge

Folding a Source Row into an existing Candidate that has the same Normalized Email.
Counted separately from `imported` in the Import Report. An exact duplicate row is a
Merge, not an Import.

## Rejection

A Source Row that could not be made into a valid Candidate. Reported, never silently
dropped. Rejection is about a row being *unusable*, not about the Candidate being
unsuitable.
