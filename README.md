# Nexus: verifiable answers about a candidate's work, tailored to the role

## Purpose

A hiring panel assessing a senior technical candidate works from a CV and a conversation. The evidence that would
settle most of its questions exists: code, merged pull requests, review threads, issues, design documents, talks and
delivery records. But it is spread across hundreds of repositories and documents, and no one on the panel has the
time to find it. Claims are taken on trust or not checked at all.

Nexus closes that gap. Given **a role description** and **a candidate's body of work**, it answers an interviewer's
question with a short answer that is:

1. **Grounded.** Every claim cites its evidence: a file at a commit, a merged pull request, an issue, or a source
   document. A claim with no evidence is not made.
2. **Attributed.** It says whether the candidate wrote the work, directed the people who did, or neither. Attribution
   is derived from authorship records, not asserted.
3. **Relevant to the role.** The answer speaks to the requirements of the role being hired for, and states which
   requirements the evidence supports, which it does not, and which it cannot speak to.
4. **Honest about gaps.** When the evidence is missing or private, it says so instead of filling the gap.

The role is an input, not a constant. This engagement is assessed against the Google Cloud **AI Outcome Customer
Engineer** role. The same system must accept any other role description, and any other candidate's sources, with no
code change.

## What this engagement demonstrates

Two outcomes, and both are assessed:

1. **The product outcome above.** It is proven by interviewer acceptance tests run by people who did not build the
   system ([docs/07](docs/07-evaluation.md)), not by code tests alone.
2. **The delivery method.** The engagement is run as a Google Cloud AI Outcome Customer Engineer runs one, on Google
   Cloud's own stack: a technical evaluation and feasibility check before commitment; an upfront design that settles
   connectors, identity, data residency and legal constraints; gated delivery with evidence at every gate; field
   feedback to Google Product and Engineering; and a production handover.

## Status

| Layer | State | Where |
|---|---|---|
| Ingest: code, merged PRs with review threads, issues, commit history, external contributions, career archive | Code, repo summaries, issues, external work and career archive built and reconciled (216 of 216 repos). PR discussion threads and commit history still being harvested. Fail-open defects fixed | [docs/03](docs/03-delivery-log.md) |
| Role description as an input (requirements extracted, evidence mapped to each) | Not built: the role is written into `prompts/preamble.md` | [docs/07](docs/07-evaluation.md) |
| Attribution: "wrote" from authorship records, "directed" from records of direction | Partly built: role facts come from the candidate's own role map, not yet labelled self-reported or checked against records | [docs/08](docs/08-answer-layer.md) |
| Cited answers | Built, localhost only, from the Agent Search search summary | [docs/08](docs/08-answer-layer.md) |
| Claim-level grounding check | Not built | [docs/07](docs/07-evaluation.md) |
| Interviewer acceptance tests | Defined, not yet run | [docs/07](docs/07-evaluation.md) |
| Hosted page behind sign-in | Not built | [docs/06](docs/06-production-path.md) |

This repo is the ingestion and answer layers, plus the **engagement record** of how the work was scoped, designed,
delivered and handed over.

## Architecture

[docs/00-architecture.md](docs/00-architecture.md) shows the system, the request flow and every component mapped to
the need it serves.

## Ask it a question

```sh
.venv/bin/python nexus/server.py     # then open http://127.0.0.1:8765
```

Answers come from Google Agent Search with your Google login. No model key is needed.

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
| Answer layer and threat model | [docs/08-answer-layer.md](docs/08-answer-layer.md) |

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
.venv/bin/python nexus/harvest.py  --state state --cache clones --bucket unused [--path-exclusions state/path-exclusions.json]
.venv/bin/python nexus/prs.py      --state state --bucket unused     # merged PRs with discussion and review threads
.venv/bin/python nexus/issues.py   --state state --author <GITHUB_LOGIN>  # issues, plus your work in others' repos
.venv/bin/python nexus/commits.py  --state state                     # commit history, one document per repo-month
.venv/bin/python nexus/profile_docs.py --state state                 # role map -> citable documents
```

Owner files in gitignored `state/`: `exclusions.json` (repos to leave out, by category), `inclusions.json` (forks
that carry your own work), `path-exclusions.json` (sensitive paths inside an included repo),
`profile/role-map.md` (your roles), `demo-scope.json` (story repos allowed in demo scope).

One HTML document per eligible file, one summary document per repo, one per merged PR. Ids are
`<prefix>-<sha256(canonical uri)[:32]>`, stable across runs. Both scripts exit non-zero if any id repeats.
Cached clones are fetched to the current default branch head before harvesting.

### 3. Secret scan (gate G3)

```sh
.venv/bin/python nexus/scan.py --state state
```

gitleaks runs over the unescaped text. Every flagged document is moved to `state/quarantine/` and dropped from the
metadata, except repo summaries, which have the flagged lines redacted so the repo stays findable. The corpus is
then re-scanned. Exits non-zero unless the re-scan is clean.

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
.venv/bin/python nexus/reconcile.py --project <PROJECT_ID> --state state --ds ds-code --target ds-code-lite \
  --manifest state/manifest/repos.json
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
