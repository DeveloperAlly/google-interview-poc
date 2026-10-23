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
