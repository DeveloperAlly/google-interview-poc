# 07. Search quality evaluation

Engagement phase: proving the outcome, not the activity. Every number below came from real calls to
`servingConfigs/default_search:search` on the `nexus-lite` app (Enterprise tier, no LLM add-on, digital
parser, no chunking). Three golden sets, approved at gate G4 by owner delegation on 2026-10-23.

## Results

| Set | Queries | What it tests | recall@5 | Detail |
|---|---|---|---|---|
| [golden.yaml](../eval/golden.yaml) | 20 | Find the right repo from a description | **1.00** (20 of 20) | 17 at rank 1, 3 at rank 2 |
| [golden-code.yaml](../eval/golden-code.yaml), first run, strict labels | 10 | Find the right file from an interviewer-style "how does X work" question | **0.60** (6 of 10) | ranks 1, 1, 2, 3, 4, 4 |
| [golden-code.yaml](../eval/golden-code.yaml), approved labels | 10 | Same, with three labels widened at G4 (see below) | **0.80** (8 of 10) | 2 misses: mediation, proof of work |
| [golden-prs.yaml](../eval/golden-prs.yaml) | 8 | Find the right merged PR from a paraphrase of the change | **0.88** (7 of 8) | 1 miss: proof of work default |

**Limits of these numbers.** The sets are small (20, 10 and 8 queries), the builder wrote them, and three labels
were widened after the first run. They are smoke tests that the pipeline retrieves the right things, not a
benchmark. A real evaluation needs questions written by someone who did not build the index.

## Reading the numbers honestly

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

## Findings that change the next iteration

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
