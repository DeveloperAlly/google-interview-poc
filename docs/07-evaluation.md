# 07. Search quality evaluation

Engagement phase: proving the outcome, not the activity. Every number below came from real calls to
`servingConfigs/default_search:search` on the `nexus-lite` app (Enterprise tier, no LLM add-on, digital
parser, no chunking). Both golden sets are drafts awaiting owner approval at gate G4.

## Results

| Set | Queries | What it tests | recall@5 | Detail |
|---|---|---|---|---|
| [golden.yaml](../eval/golden.yaml) | 20 | Find the right repo from a description | **1.00** | 17 at rank 1, 3 at rank 2 |
| [golden-code.yaml](../eval/golden-code.yaml) | 10 | Find the right file from an interviewer-style "how does X work" question | **0.60** | 6 hits; ranks 1, 1, 2, 3, 4, 4 |

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

Labels are not edited after seeing results. Re-scoring with corrected labels is an owner decision at G4.

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
4. **Generative answers are off by design.** Enterprise core generative answers and the LLM add-on would turn
   results into cited answers, the end goal for interview use. They are off to stay at zero cost; switching them
   on is a commercial decision priced in [05](05-cost-and-commercials.md).
