# 01. Discovery and technical feasibility

Engagement phase: technical evaluation. The question this phase answers is whether the solution can be
delivered as asked, inside the customer's real constraints, before anything billable or permanent is created.

## The customer, the problem and the outcome

**Customer.** A hiring panel assessing a candidate for a specific role. The candidate commissions the system; the
panel uses it. In this engagement the role is Google Cloud's AI Outcome Customer Engineer, and the candidate is the
owner of the repositories.

**Problem.** The panel cannot verify a candidate's claims against the work itself. The evidence exists, but it is
spread across hundreds of repositories and documents, in more than one GitHub owner, with public, private and
internal visibility.

**Outcome.** An interviewer asks a question and gets a short answer that is grounded (every claim cited), attributed
(wrote it, directed it, or neither), relevant to the role's requirements, and honest about missing evidence. The role
description is an input, so the same system serves any role.

**Ask as first briefed.**

> Nexus: a pipeline that pulls every repository the customer owns, across a personal account and a company
> organisation (code, docs, merged pull requests), into Google Agent Search, so all of it can be searched
> as one knowledge base.

That brief described a component, not the outcome. The customer's own earlier materials described an
interviewer-facing product: a conversational dossier with probe questions, an evidence inspector behind every claim,
attribution of hands-on authorship against technical direction, and an endpoint other tools can query. Delivery
first built only the search component. The outcome above restores the customer's intent and is what the engagement
is assessed against.

**Exit criteria.** The criteria in the customer's earlier PRD (100% of "240+" repos, "zero hallucinations", P95 under
450 ms) could not be measured as written: the repo count was wrong, "zero hallucinations" has no test, and latency
was never measured. They are replaced by these:

| # | Criterion | Measured by |
|---|---|---|
| E1 | Every in-scope repo has its documents in the index, reconciled against the manifest | `reconcile.py --manifest` |
| E2 | Stored content matches the source file at its commit, on a 50-document sample | Content fidelity check (not built) |
| E3 | Right evidence in the top 5 for at least 80% of 30 or more questions written before the run by someone other than the builder | `eval.py` on an independent set |
| E4 | Every answer claim is cited, and at least 90% of claims are supported by their citation | Claim-level grounding check, plus reviewer judgement ([07](07-evaluation.md)) |
| E5 | At least 90% of "what did you build" answers attribute the work correctly against commit and PR authors | Attribution test ([07](07-evaluation.md)) |
| E6 | Interviewer acceptance tests pass at the bar set in [07](07-evaluation.md) | Reviewers who did not build the system |
| E7 | Demo scope returns no private or internal document on 20 probe questions; no secret uploaded | Probe set and secret scan |
| E8 | p95 latency measured and reported for search and for answers | Timed runs |
| E9 | Running cost USD 0, confirmed in the billing report | Cloud Billing |

## Constraints as stated, and as found

| Constraint | Stated | Found on inspection |
|---|---|---|
| Time | 2 hours to a working pipeline | Held for the build; the full import runs unattended overnight |
| Budget | Not stated at the start | **Zero.** Stated by the customer mid-delivery, after a billable pilot. See [05](05-cost-and-commercials.md) |
| Execution environment | The brief assumed the build agent cannot reach `googleapis.com`, so all cloud work would run in GitHub Actions with Workload Identity Federation | False for this engagement. `curl https://discoveryengine.googleapis.com/` answered (HTTP 404 from the API front end, which proves reachability) |
| GitHub access | Two fine-grained tokens, one per owner, because a fine-grained token is scoped to one owner | Not needed for the POC. The operator's existing CLI token has `repo` and `read:org` and could list private repos in both owners |
| Corpus size | The brief cited counts of 240+, 57 and 113 repos from earlier materials | **293** repos from the API, counted by paginating both owners. None of the earlier figures matched; the manifest is the source of truth |
| Repo visibility | Public and private | Public, private, and **internal** (an enterprise-org visibility the brief did not mention) |

Lesson carried forward: every figure in a brief is a claim until it is re-derived from the system of record.

## Feasibility checks (each one a real call)

| Check | Method | Result |
|---|---|---|
| Network path to the API | `curl` to the Discovery Engine host | Reachable |
| Read access to both owners | List repos via GitHub REST, paginated | 293 repos visible, including private and internal |
| Supported document formats | Agent Search data preparation docs and the `Document.Content` REST reference | Raw source files (`.py`, `.go`, `.ts`) are not an accepted format, so every file must be wrapped. `text/markdown` is **not** in the REST reference's mimeType list (the prose page says Markdown is supported). HTML is listed |
| Chunking prerequisites | Parse and chunk docs | Layout-based chunking requires the layout parser. The layout parser does not handle Markdown or TXT. Chunking cannot be turned on or off after a data store is created |
| Import limits | Data preparation docs | 200 MB per file, 100,000 files per import call. INCREMENTAL reconciliation is the default and upserts |
| Credentials in the corpus | gitleaks over a pilot | Credentials present in real repos. A scan step before upload is mandatory, not optional |
| Cost | Pricing page | Checked **after** the pilot import, not before. That ordering was the defect. See [05](05-cost-and-commercials.md) |

## Scope decision

Go, with these cuts agreed with the customer before the build:

- In: GitHub code, docs and READMEs (one document per file), one summary document per repo, merged PRs.
- Out for the POC: Google Drive and Notion (each needs a customer-created integration token), GitHub Actions
  plus WIF and Cloud Run (documented as the production path in [06](06-production-path.md)), a full 15 to 25 query
  golden set (a draft set is supplied for the customer to edit).
- Excluded from the corpus by the customer at gate G1, by category: client-owned code (9 repos), personal
  material firewalled from career use (5), mirrors and build output that are not the customer's code (2),
  a non-code media archive (1). Forks (49) and empty repos (23) excluded by rule.
- Result: **204 repos in scope**: 71 public, 31 internal and 20 private in the organisation; 53 public and 29
  private in the personal account.
