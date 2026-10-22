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
| G4 | Golden queries | Owner | Two draft sets supplied; awaiting owner edit |
| G5 | Destructive actions | Owner, never pre-approved | None taken. Bucket clean-up and the unused chunked stores are left for the owner |

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
| P7 Eval | 04:54 to 04:57 | recall@5 1.00 (repo routing, 20 queries); 0.60 (code-level, 10 queries) | [07](07-evaluation.md) |

## What went wrong, and what was done about it

| Defect | Caught by | Fix |
|---|---|---|
| Brief assumed no network path and two fine-grained tokens | Feasibility checks | Simpler local POC; WIF moved to the production path |
| `text/markdown` not an accepted mimeType | Doc verification before generating JSONL | All documents as HTML |
| Secret scanner blinded by HTML escaping | Comparing pilot finding counts across formats | Scan the raw text; scan both copies; both must be clean |
| Billable pilot ran before the cost check | Cost check before the full run | Full run stopped; zero-cost redesign; method fix recorded in [05](05-cost-and-commercials.md) |
| 403 on a new project | Preflight | Retry; recorded as product feedback F5 |
| Runbook referenced a script that did not exist yet | Writing the README | `manifest.py` written and verified against the approved manifest |
