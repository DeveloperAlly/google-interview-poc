# Nexus: interview answers from a body of work

## The problem (confirmed by the owner, 23 October 2026)

The owner is interviewing for Google Cloud's AI Outcome Customer Engineer role. Her experience is spread across
hundreds of repos, talks, writing and documents, and much of it is direction she set rather than code she wrote. So
neither she nor an interviewer can quickly pull up verifiable evidence for any claim she makes. On top of that, she
has to show she can run a Google customer engagement, and how this project itself is run is that proof.

## Required outcomes (owner's words, verbatim)

> 1. An intelligent q&A site that uses the role needs to answer INTERVIEWER QUESTIONS - this isnt just code is it?
>    Its not about EVIDENCE as must as it is about STORYTELLING / STAR / CAR answers - its a resource FOR ME to use
> 2. The build process MUST follow google's lifecycle - which exists in the google drive already.

The lifecycle is the *Google Cloud Customer Engineering & Solutions Lifecycle* in the owner's project Drive folder:
four phases, seven deliverables, working backwards from an approved outcome. No phase runs ahead of one that is
incomplete.

## How this was delivered

This POC was run on the Google Cloud Customer Engineering lifecycle, 23 October 2026, T+0 = 12:56 AEDT. The plan of
record is [PLAN OF RECORD v2](https://github.com/DeveloperAlly/google-interview-poc/issues/5#issuecomment-6355349310),
narrowed by [READ THIS FIRST](https://github.com/DeveloperAlly/google-interview-poc/issues/5#issuecomment-6355551102):
the owner is the only user, with no hosting, no interviewer users and no security work. The owner approved only G0.
Under the [gate change](https://github.com/DeveloperAlly/google-interview-poc/issues/5#issuecomment-6355490972), an
independent verifier, V ([#11](https://github.com/DeveloperAlly/google-interview-poc/issues/11)), approves G1 to G3 by
using the product, failing by default. The phase table further down this README predates plan v2 and is kept as the
record of where the engagement stood before it.

| Phase | Deliverable | Where it is | Produced by | Gate | Approved by | Owner decisions that shaped it |
|---|---|---|---|---|---|---|
| 0. Plan | Plan of record v2 | [#5 plan v2](https://github.com/DeveloperAlly/google-interview-poc/issues/5#issuecomment-6355349310) | Owner with Session B ([readiness review](https://github.com/DeveloperAlly/google-interview-poc/issues/5#issuecomment-6355541804), four blockers fixed) | G0 | **Owner**, [12:56](https://github.com/DeveloperAlly/google-interview-poc/issues/5#issuecomment-6355532535) | Gate change: owner approves G0 only, V approves G1 to G3 |
| 1. Discover & Justify | D01 Executive Opportunity Brief | [#6 D01](https://github.com/DeveloperAlly/google-interview-poc/issues/6#issuecomment-6355589889) | A (#6) | G1 | **V**. [Round 1 FAIL](https://github.com/DeveloperAlly/google-interview-poc/issues/5#issuecomment-6355618681) (on D02, see next row; D01 passed, deadline weak). [Round 2 PASS](https://github.com/DeveloperAlly/google-interview-poc/issues/5#issuecomment-6355659679) | Owner as only user. Session B [found the dated deadline](https://github.com/DeveloperAlly/google-interview-poc/issues/6#issuecomment-6355649287) D01 said was not written down (recruiter screen, Mon 26 Oct 2026) |
| 1. Discover & Justify | D02 FinOps Business Case & TCO | [#9 D02](https://github.com/DeveloperAlly/google-interview-poc/issues/9#issuecomment-6355549243), [D02 v2](https://github.com/DeveloperAlly/google-interview-poc/issues/9#issuecomment-6355638571) | B (#9) | G1 | **V**. Round 1 FAIL: pass bar weaker than owner decision 2, unsourced claims ("evening of digging", Gemini billing), wrong arithmetic (3,000 queries), "free allowance" was a trial, no pricing URLs. Fixed in v2. Round 2 PASS | [Decision 4, 13:12](https://github.com/DeveloperAlly/google-interview-poc/issues/5#issuecomment-6355727339): Gemini key on a free-tier project, billing off, Gemini cost USD 0 |
| 2. Design & Scope | D03 PRD with binding exit criteria | [#6 D03](https://github.com/DeveloperAlly/google-interview-poc/issues/6#issuecomment-6355594393) | A (#6) | G2 | **V**. D03 passed in rounds 1 and 2; G2 is held open by D04 | [Decision 2, 13:02](https://github.com/DeveloperAlly/google-interview-poc/issues/5#issuecomment-6355601140): pass bar approved as written (5 of 7 topics and 5 of 8 blind questions strong, gaps stated plainly, zero fabricated facts, role correct every time, holds up under two follow-ups) |
| 2. Design & Scope | D04 Technical Architecture Blueprint | [#9 D04](https://github.com/DeveloperAlly/google-interview-poc/issues/9#issuecomment-6355553823), [v2](https://github.com/DeveloperAlly/google-interview-poc/issues/9#issuecomment-6355638920), [v3](https://github.com/DeveloperAlly/google-interview-poc/issues/9#issuecomment-6355680346) | B (#9) | G2 | **V**. Round 1 FAIL: excluded decks used as evidence; owner filling missing slots. Round 2 FAIL: decks fixed by name but readmitted through the *Drive Export Master Archive*, which bundles their stale figures (240+ repos, P95 450 ms). v3 moves the archive to not-evidence. Round 3 verdict on v3: **not yet posted** as of this commit | [Decision 1](https://github.com/DeveloperAlly/google-interview-poc/issues/5#issuecomment-6355601140): four decks excluded. [Decision 3](https://github.com/DeveloperAlly/google-interview-poc/issues/5#issuecomment-6355727339): Master Archive excluded. [Decision 5](https://github.com/DeveloperAlly/google-interview-poc/issues/5#issuecomment-6355808498): Livepeer DocsOS deck allowed, self-reported |
| 3. Execute & Validate | D05 POC test and eval plan | Exit criteria E1 to E6 in [D03](https://github.com/DeveloperAlly/google-interview-poc/issues/6#issuecomment-6355594393); blind questions and rubric in [#10](https://github.com/DeveloperAlly/google-interview-poc/issues/10); V's [anti-rubber-stamp rules](https://github.com/DeveloperAlly/google-interview-poc/issues/11#issuecomment-6355496952), including a calibration set with two planted errors V must find | A, E (#10), V | G3 | V | Decision 2 (pass bar). [Decisions 6 to 8, 13:21](https://github.com/DeveloperAlly/google-interview-poc/issues/5#issuecomment-6355843137): career facts where sources conflict, held in `state/owner_facts.md`, which overrides every source |
| 3. Execute & Validate | **D05 results** | **PLACEHOLDER: V adds the final run here** | V | **G3: PLACEHOLDER** | V | |
| 3. Execute & Validate | D06 Security & IAM review | Not produced | | | | **De-scoped by the owner** for this POC ([READ THIS FIRST](https://github.com/DeveloperAlly/google-interview-poc/issues/5#issuecomment-6355551102) item 1: no security work). The earlier threat model in [docs/08](docs/08-answer-layer.md) is not reviewed |
| 4. Scale & Handover | D07 Production readiness (one page) | [docs/06, "D07 Production readiness: interview day"](docs/06-production-path.md#d07-production-readiness-interview-day) | A-handover | G4 | Owner, on use | No hosting, no interviewer users, no security |

**The fabricated-answer defect, found and fixed.** At
[T+11](https://github.com/DeveloperAlly/google-interview-poc/issues/6#issuecomment-6355662171) the answer page still
overreached in 3 of 3 test answers: it claimed she ran an agent's review, that the Dell work was a delivered platform
with outcomes no source states, and that she delivered Kubernetes at IBM. A fact-check pass went live at
[T+15](https://github.com/DeveloperAlly/google-interview-poc/issues/6#issuecomment-6355714348) with no fabricated facts
in 3 of 3 and the Kubernetes-at-Google question answered as a plain gap. At
[T+25](https://github.com/DeveloperAlly/google-interview-poc/issues/6#issuecomment-6355838598) the second pass was
removed for latency (up to 220 s down to 10 to 15 s). Session B
[flagged](https://github.com/DeveloperAlly/google-interview-poc/issues/6#issuecomment-6355845178) that this could
reopen the defect, and at T+27 an outcome overreach and an IBM conflation were still open, so Session B
[held the hand-back to V](https://github.com/DeveloperAlly/google-interview-poc/issues/6#issuecomment-6355869973).
Separately, Session B caught a deck figure ("830-file PR #730") that the record contradicts: that PR was a
[closed, unmerged draft](https://github.com/DeveloperAlly/google-interview-poc/issues/8#issuecomment-6355730054). The story
cards were [redirected to the upstream record](https://github.com/DeveloperAlly/google-interview-poc/issues/8#issuecomment-6355756026)
instead (86 PRs authored, 52 merged). Whether E4 (zero fabricated facts) holds is V's call at G3.

## Where the engagement is in the lifecycle

| Phase | Deliverable | State |
|---|---|---|
| 1. Discover & Justify | 01 Executive Opportunity Brief | **Not written.** Problem statement confirmed; timebox and value case still open |
| 1. Discover & Justify | 02 FinOps Business Case & TCO | **Not written.** [docs/05](docs/05-cost-and-commercials.md) covers cloud cost only, with no business case |
| 2. Design & Scope | 03 PRD with Binding Exit Criteria | Blocked by phase 1. A draft criteria list (E1 to E13) exists in [docs/01](docs/01-discovery-and-feasibility.md) and is not approved |
| 2. Design & Scope | 04 Technical Architecture Blueprint | Blocked. [docs/00-architecture](docs/00-architecture.md), [docs/02](docs/02-solution-design.md) and [docs/08](docs/08-answer-layer.md) describe what was built, not an approved design |
| 3. Execute & Validate | 05 POC Test & Synthetic Eval Plan | Blocked. [docs/07](docs/07-evaluation.md) holds builder-written tests and a draft acceptance protocol |
| 3. Execute & Validate | 06 Enterprise Security & IAM Review | Blocked. Inputs exist in [docs/02](docs/02-solution-design.md) (data boundary) and [docs/08](docs/08-answer-layer.md) (threat model) |
| 4. Scale & Handover | 07 Production Readiness Review | Blocked. [docs/06](docs/06-production-path.md) is a target outline only |

## What exists, and how to read it

Before the problem and outcomes were confirmed, an ingestion pipeline and a localhost answer page were built and are
described below. **They were built ahead of the lifecycle gates.** They are exploratory: useful as feasibility
evidence for phase 1, but no part of them is an accepted design or a passed exit criterion. Their numbers are real
measurements of what was built; they are not measurements against the required outcomes, which have no approved
criteria yet. How that happened is recorded in [docs/01](docs/01-discovery-and-feasibility.md) and
[docs/03](docs/03-delivery-log.md).

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
