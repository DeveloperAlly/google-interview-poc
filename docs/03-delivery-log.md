# 03. Delivery log

Engagement phase: technical delivery against gates. Times are local (AEDT), 23 October 2026. Every result
column is the output of a command, not a summary of intent.

## Gates

| Gate | Decision | Who | Outcome |
|---|---|---|---|
| G0 | Environment and access | Owner | Owner signed in to gcloud (user + ADC). Agent created the project, linked billing, enabled APIs on owner approval |
| G1 | Include list | Owner | 17 repos excluded by category (client IP, personal, not-owner code, non-code archive); forks and empty repos by rule; 204 in |
| G2 | Data store config (permanent) | Owner | Approved chunked config; later superseded by the zero-cost digital-parser config (D4) |
| G3 | Secret-scan exclusions | Owner, pre-approved | Drop every flagged document, record it, re-scan to zero |
| G4 | Golden queries | Owner, delegated | Three sets approved: repo routing, code-level (three labels widened), merged PRs |
| G5 | Destructive actions | Owner, explicit approval | Approved 2026-10-23: deleted the unused chunked app `nexus-search`, stores `ds-code` and `ds-prs`, and the bucket. Remaining: `nexus-lite` over `ds-code-lite` and `ds-prs-lite` |

## Phases

| Phase | Approx. time | Result | Evidence |
|---|---|---|---|
| P0 Preflight | before 04:15, completed 04:22 | Network reachable; GitHub token sees both owners incl. private and internal; project `billingEnabled: true`; owner holds `roles/owner`; bucket write and read OK; first Discovery Engine call 403, retry 200 (IAM propagation) | Preflight commands in the session; see F5 in [04](04-field-feedback.md) |
| P1 Manifest | before 04:15 | 293 repos; 204 included | `nexus/manifest.py` reproduces the approved include set exactly (293/293 rows identical) |
| P2 Harvest, pilot | 04:15 | 8 repos, 918 docs, 918 unique ids, 26 s | `harvest.py` exit 0 |
| P3 Scan, pilot | 04:16 | First run on HTML found 15; on raw text 47. Scanner changed to raw text (D8). 18 docs dropped, re-scan 0 | `scan.py` |
| P4 Data stores | 04:25 | `ds-code`, `ds-prs`, app `nexus-search` created; GET read-back diff against spec: none | `datastores.py` |
| P5 Import, pilot | 04:28 | 900 of 900 succeeded, 0 failed (GCS-staged, layout parser) | `import-ds-code-pilot.json` |
| P2 Harvest, full | 04:27 | 204 repos, 16,772 docs, 16,772 unique ids | `harvest.json` |
| P3 Scan, full | 04:29 | 483 findings, 217 docs dropped, re-scan 0; 16,555 to upload | `secret-scan.json` |
| Cost check | 04:30 | Full import on layout parser about USD 504; pilot about USD 37 already incurred. **Full import stopped before submission.** Owner set budget to zero | [05](05-cost-and-commercials.md) |
| P4 Data stores, zero cost | 04:31 | `ds-code-lite`, `ds-prs-lite` (digital parser), app `nexus-lite`; LLM add-on removed from both apps, read back as `{'searchTier': 'SEARCH_TIER_ENTERPRISE'}` | `datastores.py --profile lite` |
| P5 Import, code | 04:33 to 04:52 | 166 inline batches; 16,555 succeeded, 0 failed | `import-ds-code-lite-full-inline.jsonl` |
| PR harvest and import | 04:40 to 04:50 | 1,430 merged PRs across 70 repos; 6 dropped by scan; 1,424 of 1,424 imported | `prs.json`, `import-ds-prs-lite-full-inline.jsonl` |
| P6 Reconcile | 04:53 | `ds-code-lite`: expected 16,555, present 16,555, missing 0, extra 0, 204 repos, 0 with gaps. `ds-prs-lite`: 1,424 / 1,424, missing 0, 70 repos | `reconcile.py` |
| P7 Eval | 04:54 to 04:57, re-run after G4 | recall@5 1.00 (repo routing, 20); code-level 0.60 strict, 0.80 approved (10); merged PRs 0.88 (8) | [07](07-evaluation.md) |

## Scope expansion after owner review (G1 revisited)

The owner reviewed the first cut and found it had left out the most interview-relevant material. Every exclusion
had been proposed by the builder and judged by file type or repo shape, not against the purpose.

| Change | Why | Result |
|---|---|---|
| Content archive repo re-included: presentations, resume, writing, brand story, social posts, transcripts, research | Judged by format ("non-code archive") instead of purpose; it is the core of interviewer facts | 1,697 of 1,697 indexed. Extracted PDF text indexed instead of the raw PDFs; derived dumps of sensitive sources excluded by a gitignored path rule |
| Client repos re-included (9) | Owner: they are evidence of delivered work. The index stays in the owner's private project; this repo never names them | 1,506 of 1,506 indexed |
| One fork re-included by owner override | The fork carries the owner's own active work on a partner's documentation | 1,761 of 1,761 indexed |
| Issues collected for every owned repo, including issue-only planning repos | Issues are where plans of work live. GitHub reports `size 0` for repos that hold only issues, so the "empty repo" rule had hidden 8 planning repos holding 126 issues | 2,068 issues across 62 repos, with comment threads |
| The owner's issues and PRs in repositories they do not own | Contribution to other organisations' projects was invisible | 84 issues and 121 PRs across 56 repos; visibility looked up per repo (52 public, 4 private) |
| PR discussion and review threads, and commit history | Direction-setting shows in review and discussion, not only in authored code | Re-harvest with the review fixes in progress at the time of writing |

## Second review: fail-open defects

An automated reviewer on the PR found five places where a failure would still report success. All fixed:
an import batch with failures was recorded as finished; GitHub pagination treated any error as the end of the
list; a crashed verification scan read as zero findings; failed clones did not fail the harvest; an existing search
app was not checked for its attached stores. A sixth gap: reconcile compared the store with the harvest, not the
manifest. Reconcile now requires a summary document for every included repo. On its first run it found **9 included
repos with no summary document**: 8 had been dropped whole by the secret scan because their README excerpt held a
key-like string, and one repo post-dated the harvest. Summaries are now redacted line by line instead of dropped;
coverage is 216 of 216 (`reconcile.py --manifest`, 0 uncovered).

## What went wrong, and what was done about it

| Defect | Caught by | Fix |
|---|---|---|
| Brief assumed no network path and two fine-grained tokens | Feasibility checks | Simpler local POC; WIF moved to the production path |
| `text/markdown` not an accepted mimeType | Doc verification before generating JSONL | All documents as HTML |
| Secret scanner blinded by HTML escaping | Comparing pilot finding counts across formats | Scan the raw text; scan both copies; both must be clean |
| Billable pilot ran before the cost check | Cost check before the full run | Full run stopped; zero-cost redesign; method fix recorded in [05](05-cost-and-commercials.md) |
| 403 on a new project | Preflight | Retry; recorded as product feedback F5 |
| Runbook referenced a script that did not exist yet | Writing the README | `manifest.py` written and verified against the approved manifest |
| Most interview-relevant sources excluded or never collected | Owner review | Scope rebuilt around the purpose; see above |
| Five fail-open paths and a reconcile blind spot | Automated PR review | Fixed; reconcile now checks the manifest |
| GitHub and Google API clients had no retry on network errors | A read timeout and a connection reset during reconcile and harvest | Retry with backoff in both clients |
| External PRs and issues labelled public regardless of their repo | Second automated review | Visibility looked up per repo; 22 documents from 4 private repos relabelled and re-imported, verified by reading them back |
| Private repo names hardcoded in a committed test | Second automated review | Moved to gitignored state |
