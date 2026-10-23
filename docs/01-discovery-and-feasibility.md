# 01. Discovery and technical feasibility

Engagement phase: technical evaluation. The question this phase answers is whether the solution can be
delivered as asked, inside the customer's real constraints, before anything billable or permanent is created.

## The customer, the problem and the outcome

**Customer.** The owner of the repositories, preparing for Google Cloud AI Outcome Customer Engineer interviews. The
resource is for her to use. Interviewers are its subject, not its users: the questions it answers are theirs.

**Problem** (confirmed by the owner, 23 October 2026). Her experience is spread across hundreds of repos, talks,
writing and documents, and much of it is direction she set rather than code she wrote. So neither she nor an
interviewer can quickly pull up verifiable evidence for any claim she makes. On top of that, she has to show she can
run a Google customer engagement, and how this project itself is run is that proof.

**Outcomes** (owner's words): "An intelligent q&A site that uses the role needs to answer INTERVIEWER QUESTIONS ...
Its not about EVIDENCE as must as it is about STORYTELLING / STAR / CAR answers - its a resource FOR ME to use", and
"The build process MUST follow google's lifecycle". See the [README](../README.md) for the lifecycle position.

**Superseded framing.** An earlier version of this section, written by another session, named a hiring panel as the
customer and made verifiable evidence the product. The owner corrected both: the resource is hers, and storytelling
answers are the product, with evidence in support.

## How discovery actually ran

This section is a correction. An earlier version of this document read as if discovery had been completed before
the build. It was not.

- Discovery started with the customer's written brief and three exchanges: what the system is, that it was for a
  Google interview, and that the first call was a recruiter screen.
- The customer then set a two-hour deadline. Discovery stopped there. The purpose, the audiences and the success
  criteria were never written down, and the brief's "ingestion layer only" scope was built as stated.
- Consequences, each found by the customer rather than by a check: the most relevant repo (presentations, resume,
  writing) was excluded as a "non-code archive"; a fork carrying the customer's own work, issues, PR discussion,
  commit history and contributions to other organisations' projects were left out; and answers credited the
  customer's own founding role to others.
- The outcome above and the exit criteria below were written on 23 October 2026, after the build, and reconciled
  from two independent drafts. They await the customer's sign-off.

The lesson for the method: the outcome document is the first artefact of an engagement, written even when time is
short, and every later phase is checked against it.

**Ask as first briefed.**

> Nexus: a pipeline that pulls every repository the customer owns, across a personal account and a company
> organisation (code, docs, merged pull requests), into Google Agent Search, so all of it can be searched
> as one knowledge base.

That brief described a component, not the outcome. The customer's own earlier materials (a PRD shared in the engagement, not in this repo) described an
interviewer-facing product: a conversational dossier with probe questions, an evidence inspector behind every claim,
attribution of hands-on authorship against technical direction, and an endpoint other tools can query. Delivery
first built only the search component. The outcome above restores the customer's intent and is what the engagement
is assessed against.

**Draft exit criteria (input to deliverable 03, not approved).** These were drafted before phase 1 was complete and
before the outcome above was confirmed; they still describe an evidence tool, and must be rewritten for the confirmed
outcome in the PRD. The criteria in that PRD (100% of "240+" repos, "zero hallucinations", P95 under
450 ms) could not be measured as written: the repo count was wrong, "zero hallucinations" has no test, and latency
was never measured. They are replaced by these:

| # | Criterion | Measured by | Status, 23 Oct 2026 |
|---|---|---|---|
| E1 | Every in-scope repo has its documents in the index, reconciled against the manifest | `reconcile.py --manifest` | **Partly met.** 216 of 216 included repos have a summary document, 0 missing; code, issues and external work reconciled. PR discussion threads and commit history still being harvested |
| E2 | Stored content matches the source file at its commit, on a 50-document sample | Content fidelity check (not built) | **Not met** |
| E3 | Right evidence in the top 5 for at least 80% of 30 or more questions written before the run by someone other than the builder | `eval.py` on an independent set | **Not run.** The only sets so far were written by the builder (20 of 20 repo, 8 of 10 file, 7 of 8 PR) |
| E4 | Every answer claim is cited, and at least 90% of claims are supported by their citation | Claim-level grounding check, plus reviewer judgement ([07](07-evaluation.md)) | **Not met.** Citations resolve to a listed source (8 of 8 sample questions) but support is not checked |
| E5 | At least 90% of "what did you build" answers attribute the work correctly. "Wrote" must match commit or PR authorship. "Directed" must be backed by records of direction in a project the candidate led: PRs she reviewed or approved, issues she opened or assigned, design or roadmap documents she wrote. The candidate's own role facts count as self-reported and are labelled so | Attribution test ([07](07-evaluation.md)) | **Not met.** Role facts come from the candidate's role map and are not yet labelled self-reported or checked against records |
| E6 | Interviewer acceptance tests pass at the bar set in [07](07-evaluation.md) | Reviewers who did not build the system | **Not run.** No reviewers or date set |
| E7 | Demo scope returns no private or internal document on 20 probe questions; no secret uploaded | Probe set and secret scan | **Partly met.** Secret scan clean on every upload. One leak path found and fixed (22 external documents from private repos were labelled public). The 20-question probe set has not been run |
| E8 | p95 latency measured and reported for search and for answers | Timed runs | **Not met** |
| E9 | Running cost USD 0, confirmed in the billing report | Cloud Billing | **Not confirmed.** Design is zero cost by the pricing page; about USD 37 was incurred on a pilot before the customer set a zero budget; the billing report has not been checked |
| E10 | The person asking needs no key, account or setup | Ask from the page with nothing configured | **Met on localhost only.** No hosted version |
| E11 | Strategy and reasoning sources are indexed: Drive folders and Notion pages the customer names | Named sources present in the index | **Not met.** Needs the customer to name folders and create a Notion integration |
| E12 | Sensitive data handled by the customer's rule: extracted text instead of raw binaries; derived dumps of sensitive sources excluded by a gitignored path rule; no private repo, client or personal name in this public repo | Path-rule report; independent review of committed files | **Met**, checked by two independent reviews |
| E13 | An interviewer can follow the engagement and see the system work in five minutes | A start-here path and a demo script, tried on someone who did not build it | **Not met** |

**Where each criterion comes from.** E1 to E9 restate the customer's PRD criteria in measurable form. E10 to E13
come from the customer's instructions during delivery: "not need someone to have to manually put a key in to use the
site.. thats not good product" (E10); "we should ingest google drive and notion files - because these contain more
strategy and thinking than just code proof points" (E11); the approved rule for the career archive, "this is how data
should be handled" (E12); "make sure you document the process - that IS THE MOST IMPORTANT PART" (E13, with E6).

**Open item from the PRD.** The PRD also describes "an endpoint other tools can query". It has no criterion yet;
the customer decides whether it is in scope.

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

Go, with these cuts proposed by the builder and approved at G1 under the deadline (several later reversed; see [03](03-delivery-log.md)):

- In: GitHub code, docs and READMEs (one document per file), one summary document per repo, merged PRs.
- Out for the POC: Google Drive and Notion (each needs a customer-created integration token), GitHub Actions
  plus WIF and Cloud Run (documented as the production path in [06](06-production-path.md)), a full 15 to 25 query
  golden set (a draft set is supplied for the customer to edit).
- Excluded at gate G1 on the builder's proposal, by category: client-owned code (9 repos), personal
  material firewalled from career use (5), mirrors and build output that are not the customer's code (2),
  a non-code media archive (1). Forks (49) and empty repos (23) excluded by rule.
- Result at the time: **204 repos in scope** (later 216, after the customer reversed exclusions; see [03](03-delivery-log.md)): 71 public, 31 internal and 20 private in the organisation; 53 public and 29
  private in the personal account.
