# Nexus: repository knowledge engine on Google Agent Search

Nexus ingests every repository a customer owns (code, docs, READMEs, merged pull requests) into Google Agent
Search, so the whole body of work can be searched with citations back to the exact file and commit.

This repo is the **ingestion layer** and the **engagement record** of how it was scoped, designed, delivered
and handed over, written the way an AI Outcome Customer Engineer runs a customer engagement.

## The engagement record

| Phase | Document |
|---|---|
| Technical evaluation: the ask, real constraints, feasibility checks, scope | [docs/01-discovery-and-feasibility.md](docs/01-discovery-and-feasibility.md) |
| Upfront design: connectors, identity, data boundary, residency, decisions | [docs/02-solution-design.md](docs/02-solution-design.md) |
| Delivery against gates, with evidence | [docs/03-delivery-log.md](docs/03-delivery-log.md) |
| Field feedback to Product and Engineering | [docs/04-field-feedback.md](docs/04-field-feedback.md) |
| Cost, commercials and a correction of error | [docs/05-cost-and-commercials.md](docs/05-cost-and-commercials.md) |
| Production path and handover | [docs/06-production-path.md](docs/06-production-path.md) |
| Search quality evaluation | [docs/07-evaluation.md](docs/07-evaluation.md) |

## Runbook

A fresh operator can re-run every step from here. Nothing in this repo contains corpus data; all state is
written to a local `state/` directory that is gitignored.

### 0. Prerequisites

```sh
brew install --cask google-cloud-sdk && brew install gitleaks gh
gcloud auth login && gcloud auth application-default login
gcloud config set project <PROJECT_ID>
gcloud auth application-default set-quota-project <PROJECT_ID>
gcloud services enable discoveryengine.googleapis.com
gh auth login            # token needs repo + read:org to see private and internal repos
# Python 3.9 or later
python3 -m venv .venv && .venv/bin/pip install markdown google-cloud-discoveryengine requests pyyaml
```

### 1. Manifest (read-only)

Builds `state/manifest/repos.json`: one row per repo with owner, visibility, fork, archived, size, default
branch, pushed_at and an include flag with a reason. Forks and empty repos are excluded by rule. The owner's G1
exclusions live in `state/exclusions.json` as `{"owner/name": "category"}`. That file is gitignored, so private
repo names never reach this repo, and it is re-applied on every run, so an excluded repo stays excluded on refresh.
The manifest itself is rebuilt each run: never hand-edit `repos.json`.

```sh
.venv/bin/python nexus/manifest.py --state state --owners DeveloperAlly,Lilypad-Tech
```

### 2. Harvest and normalise

```sh
.venv/bin/python nexus/harvest.py --state state --cache clones --bucket unused
.venv/bin/python nexus/prs.py     --state state --bucket unused
```

One HTML document per eligible file, one summary document per repo, one per merged PR. Ids are
`<prefix>-<sha256(canonical uri)[:32]>`, stable across runs. Both scripts exit non-zero if any id repeats.
Cached clones are fetched to the current default branch head before harvesting.

### 3. Secret scan (gate G3)

```sh
.venv/bin/python nexus/scan.py --state state
```

gitleaks runs over the unescaped text. Every flagged document is moved to `state/quarantine/`, dropped from the
metadata, and the corpus is re-scanned. Exits non-zero unless the re-scan is clean.

### 4. Data stores and search app (gate G2: parser and chunking are permanent)

```sh
.venv/bin/python nexus/datastores.py --project <PROJECT_ID> --profile lite \
  --stores ds-code-lite,ds-prs-lite --engine nexus-lite
```

Creates or reads back each store and diffs its config against the spec. `--profile chunked` uses the layout
parser with 500-token chunks: **billable**, see [docs/05](docs/05-cost-and-commercials.md).

### 5. Import

```sh
.venv/bin/python nexus/ingest_inline.py --project <PROJECT_ID> --state state --ds ds-code --target ds-code-lite --run <label>
.venv/bin/python nexus/ingest_inline.py --project <PROJECT_ID> --state state --ds ds-prs  --target ds-prs-lite  --run <label>
```

Inline import, 100 documents or 8 MB per call, INCREMENTAL, resumable: re-running the same `--run` skips
finished batches. (`nexus/ingest.py` is the Cloud Storage staged variant for corpora too large for inline.)

### 6. Reconcile

```sh
.venv/bin/python nexus/reconcile.py --project <PROJECT_ID> --state state --ds ds-code --target ds-code-lite
```

`documents.list` against the manifest, per repo. Exits non-zero if anything expected is missing.

```sh
.venv/bin/python nexus/dedupe_report.py --state state   # duplicate content across repos, read-only
```

### 7. Evaluate (gate G4)

```sh
for set in golden golden-code golden-prs; do
  .venv/bin/python nexus/eval.py --project <PROJECT_ID> --engine nexus-lite --golden eval/$set.yaml --state state/eval-$set
done
```

Real calls to `servingConfigs/default_search:search`; recall@5 per query and overall. No generative features
are requested, so queries stay in the free allowance.

### Incremental refresh

Re-run steps 1 to 6 with a new `--run` label. Unchanged files keep their ids and are upserted in place. Files
deleted upstream are not removed by INCREMENTAL; see [docs/06](docs/06-production-path.md).

## Safety rules this repo follows

- Public repo: code and documentation only. No corpus, manifest, report, private repo name or file path.
- Logs print counts, HTTP status codes and hashed ids only.
- No service account keys anywhere.
- Destructive actions (FULL reconciliation, purges, deleting a data store or bucket) are owner-approved only.
