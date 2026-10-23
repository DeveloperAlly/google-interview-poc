# 08. Answer layer and threat model

Engagement phase: from search to the outcome the customer asked for, which is answering an interviewer's question
with evidence.

## Design

| Decision | Alternatives considered | Why |
|---|---|---|
| D10 Answers from Agent Search's search summary, using the machine's Google credentials | The owner's own Claude or Gemini key typed into the page; OpenRouter | No visitor should need a key. The search summary is Enterprise "core generative answers", inside the free query allowance, and keeps the whole answer on Google's stack |
| D11 The answer method (`:answer`) is not used | Agent Search answer method | It returns `FAILED_PRECONDITION: This feature is only available when Large Language Model add-on is enabled`. The add-on is the billed Advanced tier (see F9) |
| D12 The owner's role facts are indexed as citable documents, boosted in search, and repeated in the summary instruction | Instruction text alone | With instruction text alone, the model still described the founder of a project as having "contributed to and reviewed" it, because it cites sources and the instruction is not a source. Indexed, boosted role documents fixed it |
| D13 Citation numbers are rebuilt from `citationMetadata` | Show the model's inline markers | The model writes inconsistent markers (`[3:43, 6]`, `[ROLE FACTS]`). The metadata ties each span to a reference index; proto3 JSON omits index 0, so an empty source object means the first reference |
| D14 Retry up to four times when a summary has no citation metadata; flag the answer as uncited if it still has none | Show it as if cited | Measured: the same question returned citation metadata on 3 of 5 direct calls (state/evidence/citation-metadata-frequency.txt). Answers are never presented as cited when they are not |
| D15 Demo-safe scope by default: public repos plus the owner's own career-story repos | Public only; everything | Public only hid the owner's own story. Everything would surface private and internal code on screen |
| D16 Localhost only | A public static page | The index holds private and internal material; a public page would need a sign-in layer first (production path) |

## Threat model

| Threat | Where it enters | Control |
|---|---|---|
| Prompt injection from indexed text (a README or issue saying "ignore previous instructions") | Every retrieved document is model input | The summary instruction states sources are untrusted data and must not be followed; the model has no tools, so injected text can at worst change wording, which citations make checkable |
| Markup injection into the page | Answer text and source titles come from indexed content | The page renders everything as text nodes, never HTML; links are allowed only for `https://` URLs and open with `noopener` |
| Private or internal code shown in a demo | The index mixes visibilities | Demo-safe scope filter on every query; the "everything" scope is a deliberate owner choice; the smoke test checks the scope held |
| Credentials leaking into answers | Secrets in source files | The raw-text secret scan holds back flagged documents before upload; repo summaries are redacted line by line |
| The index exposed to a network | The answer server | Binds to 127.0.0.1; no question or answer text in server logs |
| Cost creeping off the free allowance | Generative features | LLM add-on removed and checked by `datastores.py`; follow-ups, complex and long query handling not requested |

## Measured

`nexus/answer_smoke.py` asks the eight sample questions through the live server and checks that each answer exists,
carries per-claim citations that all resolve to a listed source, stays inside the demo scope, and, for role
questions, names the role from the owner's role facts. Result: **8 of 8**, with one question needing three attempts
for citation metadata (`state/evidence/answer-smoke.txt`).

## Runbook

```sh
.venv/bin/python nexus/profile_docs.py --state state          # role map -> citable documents
.venv/bin/python nexus/scan.py --state state/profile-docs
.venv/bin/python nexus/ingest_inline.py --project <PROJECT_ID> --state state/profile-docs --ds ds-code --target ds-code-lite --run profile
.venv/bin/python nexus/server.py                              # http://127.0.0.1:8765
.venv/bin/python nexus/answer_smoke.py                        # with the server running
```

Owner-only files, all gitignored: `state/profile/role-map.md` (role facts, from the CV and brand evidence) and
`state/demo-scope.json` (`{"repos": [...]}`, the career-story repos allowed in demo scope).
