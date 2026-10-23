# 06. Production path

Engagement phase: handover from POC to a system the customer runs. Documented, not built.

## Target shape

| Concern | POC | Production |
|---|---|---|
| Runtime | Operator laptop | The same harvester as a container, run as a **Cloud Run Job** |
| Trigger | Manual | **Cloud Scheduler**, nightly |
| Google identity | Operator user via ADC | **Workload Identity Federation** from GitHub Actions, or the Cloud Run job's own service account. One dedicated service account, `roles/discoveryengine.editor` on the project, nothing broader. No keys |
| GitHub identity | Operator CLI token | A **GitHub App** installed on both owners (one credential across a user and an org; fine-grained tokens are scoped to one owner) |
| Secrets | Local keyring | **Secret Manager**, mounted into the job |
| State | Local files | A private bucket path for manifest and reports; never the public code repo |

## Incremental refresh

1. Rebuild the manifest. New repos appear with their include rule applied; the customer's G1 exclusions persist.
2. Re-harvest. Ids are a hash of the canonical source path, so a file keeps its id across runs. Its body changes
   whenever the repo has a new commit, because the header carries the commit hash and permalink. Cached clones are
   fetched to the current default branch head first.
3. Re-scan. Anything newly flagged is quarantined.
4. Import with `reconciliationMode: INCREMENTAL`. Changed documents are upserted, new ones added.
5. Deleted files: INCREMENTAL does not remove them. Either a periodic `FULL` reconciliation (destructive: removes
   anything not in the current import, so it is a customer-approved action), or an explicit delete list from the
   diff of two manifests.

## Gates that stay human

| Gate | Why it stays with a person |
|---|---|
| Data store creation | Parser, chunking and location cannot be changed afterwards |
| Include list changes | Deciding what is indexed is a legal and ownership decision, not a technical one |
| Secret-scan exclusions | Someone has to rotate what was found |
| FULL reconciliation, purges, store deletion | Destructive |
| Any change that moves cost off the free allowance | Commercial decision |

## D07 Production readiness: interview day

One page for the owner, the only user. It runs on her laptop. Nothing is hosted.

**Start it.** From the repo root:

```
.venv/bin/python nexus/server.py
```

Then open http://127.0.0.1:8765/ for answers and http://127.0.0.1:8765/stages to see how the build ran.

| Page | What it does |
|---|---|
| `/` (also `/answer`) | Type an interviewer question. It maps the question to a role requirement, pulls the story cards and evidence for it, and Gemini writes one STAR/CAR answer in her first person, with her role named (built, led or directed), proof links and any gap stated plainly |
| `/stages` | The pipeline behind each answer, stage by stage: the role profile (every requirement with its sample questions), every STAR/CAR story card with its role, filled and `missing` slots and sources, and the open gaps. Use it to rehearse and to see where a story is thin |
| `/search` | The older raw evidence search over Agent Search, kept for checking a source |

**Known failure modes and the honest fallback for each.**

| Failure | What happens | What to do |
|---|---|---|
| Gemini free tier busy (503) or over quota (429) | Retries once, then falls back to `gemini-3.1-flash-lite` | Nothing. The answer shows which model wrote it |
| `gemini-3-flash-preview` failing outright | Same fallback to `gemini-3.1-flash-lite` | If both fail, the page shows "Gemini unavailable" with the error. Wait a minute and ask again |
| Slow answers | About 10 s per answer (7 to 11 s measured at T+27) | Wait. Do not resubmit |
| Any other error | The page shows the error text. It never shows a canned or cached answer | Read the error; restart the server if it is a crash |
| No evidence for a question | The answer states the gap. It does not pad or guess | Say the gap aloud, or tell a nearby story and name it as such |

**What was dropped, by owner decision ([READ THIS FIRST](https://github.com/DeveloperAlly/google-interview-poc/issues/5#issuecomment-6355551102)).**
Hosting, interviewer users and sign-in, and the D06 security and IAM review. The target production shape above is not
built.

**What comes next.** V's G3 run against the D03 pass bar, with its results added to the README. Then, only if the owner
wants it: cards for the requirements that still have none, a hosted page behind sign-in, and the D06 review that hosting
would require.
