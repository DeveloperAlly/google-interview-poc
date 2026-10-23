# 07. Evaluation: interviewer acceptance, then search quality

Engagement phase: proving the outcome, not the activity. The outcome is an interviewer getting a verifiable answer
that speaks to the role. Code tests show the pipeline works; only the acceptance tests below show the system is fit
for purpose.

## Interviewer acceptance tests

**Draft, input to deliverable 05 (POC Test & Synthetic Eval Plan), not approved.** This protocol was written before
the outcome was confirmed and scores answers as evidence for a panel. The confirmed outcome is a storytelling resource
for the owner (STAR or CAR answers to interviewer questions, backed by evidence), so the scoring rules must be
rewritten against the approved PRD (deliverable 03) before any test is run.

Status: defined 23 Oct 2026, not yet run.

**Protocol.**

- Three reviewers who did not build the system. At least one has hired for a customer-facing cloud or AI
  role.
- Each reviewer gets the role description and nothing else: no CV, and no briefing on the corpus.
- Each reviewer writes 10 questions of their own before seeing the system, then asks those and the fixed set below.
- Each answer is scored against five rules:
  - **Grounded:** every claim cites evidence, and the reviewer opens the citation and finds the claim in it.
  - **Attributed:** the candidate's role in the work is stated correctly.
  - **Relevant:** the answer addresses the role requirement behind the question.
  - **Honest:** missing or private evidence is named, not filled.
  - **Usable:** an answer arrives in under 10 seconds, and the reviewer could repeat it to a hiring committee.
- An answer passes when at least two of three reviewers pass it on all five rules.

**Fixed questions, one or more per requirement in the role description.**

| # | Role requirement | Interviewer question |
|---|---|---|
| T1 | Cloud-native architecture in a customer-facing role | Show me a cloud architecture you designed for a customer and how it was delivered. |
| T2 | Technical delivery; working with product and engineering | Give an example of a delivery you owned end to end, with the evidence. |
| T3 | Reading and debugging code | Walk me through a bug you diagnosed. Show the fix. |
| T4 | System design or orchestration frameworks | What agent orchestration have you built, and with which framework? |
| T5 | Enterprise integrations: APIs, content management, identity | How did you handle identity and connectors in an integration you designed? |
| T6 | Assess feasibility in a technical evaluation | Show a feasibility assessment you ran before committing to a build. |
| T7 | Upfront design within compliance boundaries | How did you design for a data boundary, residency or legal constraint? |
| T8 | Diagnose implementation issues; find product bugs; test workarounds | Name a product defect you found in a platform you were building on, and your workaround. |
| T9 | Translate field feedback into feature requests | Show feedback you turned into a concrete feature request. |
| T10 | Steer implementation through architectural foresight | Describe an architecture decision you made early that held up later. What did it beat? |
| T11 | Orchestrate specialised resources for complex builds | How did you coordinate people or agents to deliver a complex build? |
| T12 | Executive communication | Explain a technical cost decision as you would to a CFO, in two sentences. |

**Negative tests. All must pass.**

| # | Probe | Pass rule |
|---|---|---|
| N1 | A requirement with no evidence in the corpus (for example, production use of a named framework that was never used) | The answer says there is no evidence; nothing is inferred |
| N2 | A question whose best evidence is private | Demo scope answers without showing private or internal content, and says evidence is withheld |
| N3 | Work the candidate directed but did not write, and work she wrote | "Wrote" matches commit or PR authorship. "Directed" is backed by records of direction (her reviews or approvals, issues she opened or assigned, design documents she wrote) and never claimed as "wrote" |
| N4 | An indexed document that contains instructions | The instructions are not followed |
| N5 | A claim from the candidate's own CV or role map with no supporting record | The answer marks it as self-reported, not verified |

**Role swap.** Load a second, different role description. The same fixed protocol is run with no code change. The
answers must change emphasis to the new requirements, and the requirement-to-evidence map must change with them.

**Pass bar.**
- At least 10 of the 12 fixed questions pass.
- At least 80% of reviewer-written questions pass.
- All five negative tests pass.
- The role swap passes.
- p95 answer time is measured and reported.

## Search quality (component tests)

These are code tests of the retrieval component. They support the acceptance tests and do not replace them.

Every number below came from real calls to `servingConfigs/default_search:search` on the `nexus-lite` app
(Enterprise tier, no LLM add-on, digital parser, no chunking). Three golden sets, approved at gate G4 by owner
delegation on 2026-10-23.

### Results

| Set | Queries | What it tests | recall@5 | Detail |
|---|---|---|---|---|
| [golden.yaml](../eval/golden.yaml) | 20 | Find the right repo from a description | **1.00** (20 of 20) | 17 at rank 1, 3 at rank 2 |
| [golden-code.yaml](../eval/golden-code.yaml), first run, strict labels | 10 | Find the right file from an interviewer-style "how does X work" question | **0.60** (6 of 10) | ranks 1, 1, 2, 3, 4, 4 |
| [golden-code.yaml](../eval/golden-code.yaml), approved labels | 10 | Same, with three labels widened at G4 (see below) | **0.80** (8 of 10) | 2 misses: mediation, proof of work |
| [golden-prs.yaml](../eval/golden-prs.yaml) | 8 | Find the right merged PR from a paraphrase of the change | **0.88** (7 of 8) | 1 miss: proof of work default |

**Limits of these numbers.** The sets are small (20, 10 and 8 queries), the builder wrote them, and three labels
were widened after the first run. They are smoke tests that the pipeline retrieves the right things, not a
benchmark. A real evaluation needs questions written by someone who did not build the index.

### Reading the numbers honestly

**The 1.00 is a routing score, not a retrieval score.** 19 of the 20 first matching results were repo summary
documents. The queries were drafted from repo descriptions, and the summary documents contain those
descriptions. It proves the right repo is findable. It does not prove the right code is.

**The 0.60 is the useful number.** Of the 4 misses:

| Miss | What came back | Verdict |
|---|---|---|
| How are disputed job results mediated? | A design document on mediation and job pricing in the docs repo | Defensible answer; the label (Go package only) was too strict |
| How does the job creator submit jobs on chain? | The same repo's `docs/smart-contract-jobs.md` | Defensible, arguably better than the code; label too strict |
| How do nodes talk to the solver over websockets? | `pkg/solver/client.go`, the solver's websocket client | Defensible; label pointed at the transport package |
| How is the proof of work signal configured? | Unrelated documents from a different repo that lexically matched "proof" | **Real miss.** A word match outranked the config file |

Labels were not edited by the builder after seeing results. At G4 the owner delegated approval, and three labels
were widened to accept the design doc or sibling package that answered the question (`path_any` in the file).
That re-score is 0.80. The mediation query still misses, because the mediation doc lives in the separate docs repo
and the label names the code repo. It is left as a miss rather than widened again.

**Proof of work is the one consistent weak spot.** It misses in both the code set and the PR set. The word
"proof" pulls in unrelated documents, and the config lives in a short file with little text to match.

### Findings that change the next iteration

1. **Duplicate content crowds the top 5.** Three repos in the organisation are near-copies of each other, and
   the same file came back from all three in several queries. Across the corpus (`nexus/dedupe_report.py`):
   16,359 file documents, 13,819 unique bodies, so 2,540 redundant copies (15.5%); 3,628 documents share a body
   with at least one other. Fix: dedupe by content hash at harvest time, keep the canonical repo, and record the
   other locations as metadata.
2. **No chunking means whole-file matching.** Large files compete as single documents. Chunking would help
   code-level questions, but on this platform chunking requires the paid layout parser (see
   [04](04-field-feedback.md), F3). A free alternative is to split files at function or heading boundaries in the
   harvester, so each document is smaller.
3. **Filter by kind.** `kind` (code, doc, readme, adr, pr, repo) is in every document's metadata. Making it
   filterable (field settings) lets a question be asked of code only, or of PRs only.
4. **Cited answers may already be inside the free allowance.** An earlier draft of this document said Agent Search
   answers are paid. That was wrong as stated. The pricing page says Enterprise Edition "includes Core Generative
   Answers", and the free allowance of 10,000 queries a month excludes only *Advanced* Generative Answers (the LLM
   add-on, removed from this app). So one core answer call should cost nothing. That is a reading of the pricing page,
   not a measurement: it gets tested with one call and a billing check the next day before anything is built on it.
