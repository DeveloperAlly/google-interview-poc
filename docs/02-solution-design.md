# 02. Solution design

Engagement phase: upfront technical design. How the solution integrates with the customer's sources,
identity, data boundary and budget, decided before build and recorded so each choice can be challenged.

## Architecture as delivered

```
GitHub REST + shallow git clone
        |
        v
harvest.py   one HTML document per eligible file, one per repo, stable hashed ids, JSONL metadata
        |
        v
scan.py      gitleaks over the unescaped text; every flagged document quarantined, then re-scan to zero
        |
        v
ingest_inline.py   documents:import with inlineSource, 100 docs or 8 MB per call, INCREMENTAL, resumable
        |
        v
Agent Search (Discovery Engine v1, location global)
   ds-code-lite  ds-prs-lite   digital parser, no chunking
        \           /
         nexus-lite  search app, Enterprise tier, no LLM add-on
        |
        v
reconcile.py (documents.list vs manifest)   eval.py (real search calls, recall@5)
```

## Decisions

| # | Decision | Alternatives considered | Why |
|---|---|---|---|
| D1 | Custom harvester, not the native GitHub connector | Gemini Enterprise GitHub connector | The connector needs a Gemini Enterprise setup and licence. A harvester gives control over eligibility, secret scanning and document shape, all of which mattered |
| D2 | Run locally with the operator's user credentials (ADC) for the POC | GitHub Actions + WIF + service account, as the brief specified | The brief's reason for Actions (no network path) was false here. WIF is the right production identity and is documented in [06](06-production-path.md); building it first would have spent the 2 hours on plumbing |
| D3 | Every document emitted as HTML (`text/html`) | Markdown, TXT | `text/markdown` is not in the REST mimeType list. HTML is, and HTML is the format the layout parser reads if chunking is ever enabled |
| D4 | Digital parser, no chunking, on the stores that hold the corpus | Layout parser with 500-token layout chunks | Layout parsing is billed at USD 10 per 1,000 pages, where an HTML page is 3,000 characters. The corpus is 125.6M characters, about 50,430 pages, about USD 504. The digital parser "is offered without charge". The chunked stores and their app, created first and used only for the pilot, were deleted on owner approval (G5) |
| D5 | Inline import, no Cloud Storage staging | GCS bucket + JSONL with `content.uri` | Zero-cost requirement. A US multi-region bucket sits outside the Cloud Storage free tier, and 16,000+ object writes are billable operations |
| D6 | Search app at Enterprise tier with the LLM add-on removed | Enterprise + `SEARCH_ADD_ON_LLM` | The free allowance of 10,000 queries a month "excludes Advanced Generative Answers". Removing the add-on keeps every query inside it |
| D7 | Stable ids: `<prefix>-<first 32 hex of sha256(canonical source uri)>` | Random or path-based ids | RFC-1034 compliant, under 63 characters, and identical across runs so INCREMENTAL imports upsert instead of duplicating |
| D8 | Scan the unescaped text, not the HTML | Scan what is uploaded | HTML entity escaping hid 32 of 47 findings in the pilot (47 raw vs 15 in HTML). Both copies are now scanned and both must be clean |
| D9 | Eligibility: tracked files only (so `.gitignore` holds), no binaries, lockfiles, vendored or generated code, nothing over 200 KB | Index everything | Platform limit is 200 MB; 200 KB is a quality line. Files over it were data dumps or generated, not authored code |

## Knowledge stores: evidence, work docs, Google reference

Three Agent Search apps, queried separately so that Google's material can never be mistaken for her experience.

| App | Store | Holds | Cited as |
|---|---|---|---|
| nexus-lite | ds-code-lite, ds-prs-lite | Her repos, PRs, issues, my-content | [E#] evidence |
| nexus-docs | ds-docs-lite | 38 Drive work docs (Lilypad Network, Livepeer) and the Notion speaking log | [E#] evidence |
| nexus-google | ds-google-lite | 53 Google docs: Next '26 talk transcripts, their summaries, Google Cloud case studies | [G#] reference only |

All three use the D4 to D6 settings: digital parser, no chunking, inline import, Enterprise tier with no LLM add-on.
Builders are `google_corpus.py` and `docs_corpus.py`. The query layer is `knowledge.py`, with a page at
`knowledge_server.py` (127.0.0.1:8766). None of these touch the frozen answer path (server.py, compose.py,
facts_layer.py); folding them into the main answer is for the integrator.

Work-docs include rule: professional project and work material only. Left out:
- legal and financial documents (SAFEs, warrants, board consents, employment agreements, dissolution);
- the excluded positioning decks;
- tailored CVs and cover letters;
- interview prep;
- templates and brand assets;
- third-party papers;
- contact lists;
- personal and HR documents.

The extraction manifest lists every doc and why any was skipped. Both the raw text and the HTML went through gitleaks: zero findings.

| # | Decision | Alternatives considered | Why |
|---|---|---|---|
| D10 | A separate app for Google reference material | Add it to nexus-lite | A data store attaches to one app, and keeping reference apart makes "never evidence" structural rather than a prompt rule |
| D11 | A separate app for work docs | Add them to nexus-lite | Leaves the main product's index unchanged until the integrator chooses to merge |
| D12 | Plan per-store queries before searching | Send the question to every store | One question often asks about her and about Google. The whole sentence retrieved research notes on the evidence side |
| D13 | Pass the passage of a long doc that best matches the question, not its first 3,000 characters | Truncate | The relevant passage of a long doc was usually past the cut |
| D14 | Deterministic checks before an answer is returned: it must have inline citations, and a sentence naming an employer must cite [F] or a source that names that employer; otherwise one or two retries with the problem stated | Prompt rules only | Prompt rules alone still let unrelated work be framed as Lilypad |

Acceptance results, 26 Oct:
- 15/15 Google-platform questions cite a Google doc, with one in the top 5.
- 19/20 experience questions present no Google material as hers. The failure was a first-person view cited only to
  Google. That pattern is now a composer check (D14), and the question passed 3 of 3 re-runs.
- 10/10 sampled Google docs are retrieved in the top 5 by a phrase from their own text.
- 8/8 natural questions retrieve the expected work doc in the top 5.
- 3/4 previously weak questions now cite a work doc. The fourth, developer community, is supported by profile evidence instead.
- Still weak: "measured a business outcome". It retrieves her job-search tooling rather than the investor report.

## Identity and access

- POC: the operator's Google user via Application Default Credentials, with the quota project set so client
  libraries bill and meter against the right project. GitHub via the operator's CLI token.
- Production: GitHub Actions or Cloud Run authenticating through Workload Identity Federation to a dedicated
  service account holding `roles/discoveryengine.editor` on the project and nothing broader. No keys.
- A new project's IAM grant took a few minutes to propagate: the first Discovery Engine call returned 403
  "permission denied ... (or it may not exist)" for a project owner. A retry minutes later succeeded.
  Preflight must retry before declaring an access failure.

## Data boundary, residency and legal

- Data stores are in location `global`. For a customer with an in-region residency requirement this is the
  first thing to change, before creation, since a data store's location is fixed.
- Customer-owned code only. Client-owned repositories were excluded at G1 even though the operator had access:
  access is not the same as the right to index into a new system.
- Personal material firewalled from professional use was excluded by category.
- Secrets: 483 findings across the full corpus (generic API keys, curl auth headers, JWTs, Slack webhooks,
  GCP and AWS keys). All 217 affected documents were quarantined locally and never uploaded. The findings
  themselves are a customer action item: any live credential in a repo, public or not, should be rotated.
- **The search app mixes public, private and internal content.** Every document carries `visibility` in its
  metadata. Before any live demo, `visibility` must be made filterable and queries filtered to `public`, or private
  and internal code can surface on screen. A separate public-only app would need its own data stores, because a data
  store attaches to one app only.
- The ingestion repo is public. It holds code and these documents only. The corpus, manifest, reports and any
  repo or file names from private repos stay local.
