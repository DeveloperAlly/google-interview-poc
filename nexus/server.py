"""Nexus interview assistant: a local web page that answers interviewer questions from the index, with citations.

No model key is needed. Answers come from Agent Search's search summary (Enterprise core generative answers, inside
the free query allowance; the LLM add-on stays off), using this machine's Google Application Default Credentials.

Binds to 127.0.0.1 only: the index holds private and internal material, so this is never served to a network.
Scopes:
  demo  public repos plus the owner's own story repos listed in state/demo-scope.json (default for interviews)
  all   everything indexed, private and internal included (owner only)
"""
from __future__ import annotations

import argparse, json, re, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from datastores import Client

ROOT = Path(__file__).resolve().parent.parent
ROLE_MAP = ROOT / "state" / "profile" / "role-map.md"  # gitignored: the owner's own role facts, from her CV and brand/
PREAMBLE = ((ROOT / "prompts" / "preamble.md").read_text(encoding="utf-8").strip()
            + ("\n\nROLE FACTS:\n" + ROLE_MAP.read_text(encoding="utf-8").strip() if ROLE_MAP.exists() else ""))
SCOPE_FILE = ROOT / "state" / "demo-scope.json"  # gitignored: may name private repos


def scope_filter(scope: str) -> str | None:
    if scope == "all":
        return None
    extra = json.load(open(SCOPE_FILE)).get("repos", []) if SCOPE_FILE.exists() else []
    f = 'visibility: ANY("public")'
    if extra:
        f += " OR repo: ANY(" + ", ".join(json.dumps(r) for r in extra) + ")"
    return f


# Model-written markers: [2], [1, 2], [3:43, 6] (source:line) and [1:3:43, 8:2:00] (source:timestamp in a transcript)
MARK = re.compile(r"\s?\[(?:\d+(?::\d+)*(?:\s*,\s*\d+(?::\d+)*)*|ROLE FACTS(?:\s*,\s*\d+(?::\d+)*)*)\]")


def cite_from_metadata(text: str, meta: dict, n_refs: int) -> str:
    """Replace the model's own inline markers (inconsistent: "[3:43, 6]", "[ROLE FACTS]") with markers built from
    citationMetadata: each cited span gets [n] where n is its reference position, so every number resolves."""
    cites = (meta.get("citationMetadata") or {}).get("citations", []) or []
    inserts = []
    for c in cites:
        # proto3 JSON omits zero values: a source of {} is referenceIndex 0, the first reference
        nums = sorted({int(src.get("referenceIndex", 0)) + 1 for src in c.get("sources", [])})
        nums = [x for x in nums if 1 <= x <= n_refs]
        if nums:
            inserts.append((int(c.get("endIndex", 0)), "\u27e6" + ", ".join(map(str, nums)) + "\u27e7"))
    for pos, tok in sorted(inserts, reverse=True):
        text = text[:pos] + tok + text[pos:]
    text = MARK.sub("", text)
    return text.replace("\u27e6", " [").replace("\u27e7", "]")


class Nexus:
    def __init__(self, project: str, engine: str):
        self.c = Client(project)
        self.sc = f"{self.c.base}/engines/{engine}/servingConfigs/default_search"

    def ask(self, question: str, scope: str) -> dict:
        body = {"servingConfig": self.sc, "query": question, "pageSize": 10,
                "contentSearchSpec": {
                    "snippetSpec": {"returnSnippet": True},
                    "summarySpec": {"summaryResultCount": 10, "includeCitations": True,
                                    "ignoreNonSummarySeekingQuery": False,
                                    "modelPromptSpec": {"preamble": PREAMBLE},
                                    "modelSpec": {"version": "stable"}}}}
        # Lift the owner's role facts into the top results so the summary sees her role beside the evidence.
        body["boostSpec"] = {"conditionBoostSpecs": [{"condition": 'kind: ANY("profile")', "boost": 0.6}]}
        f = scope_filter(scope)
        if f:
            body["filter"] = f
        for attempt in range(4):  # summaries sometimes return without citation metadata; retry, never invent
            r = self.c.call("POST", f"{self.sc}:search", json=body)
            if r.status_code != 200:
                raise RuntimeError(f"Agent Search returned HTTP {r.status_code}: {r.text[:300]}")
            d = r.json()
            cm = ((d.get("summary") or {}).get("summaryWithMetadata") or {}).get("citationMetadata") or {}
            if cm.get("citations"):
                break
        by_name = {}
        results = []
        for res in d.get("results", []):
            doc = res.get("document", {})
            sd = doc.get("structData", {})
            snip = ""
            for s in (doc.get("derivedStructData", {}) or {}).get("snippets", []) or []:
                if s.get("snippet_status") == "SUCCESS":
                    snip = s.get("snippet", "")
                    break
            item = {"repo": f"{sd.get('owner')}/{sd.get('repo')}", "kind": sd.get("kind"), "path": sd.get("path", ""),
                    "url": sd.get("html_url", ""), "visibility": sd.get("visibility"),
                    "pr": sd.get("pr_number"), "snippet": snip}
            by_name[doc.get("name")] = item
            results.append(item)
        s = d.get("summary", {}) or {}
        meta = s.get("summaryWithMetadata", {}) or {}
        refs = []
        for ref in meta.get("references", []) or []:
            item = dict(by_name.get(ref.get("document"), {}))
            item["title"] = ref.get("title", "")
            item.setdefault("url", ref.get("uri", ""))
            refs.append(item)
        return {"answer": cite_from_metadata(s.get("summaryText", ""), meta, len(refs)),
                "skipped": s.get("summarySkippedReasons", []),
                "uncited": not ((meta.get("citationMetadata") or {}).get("citations")), "attempts": attempt + 1,
                "references": refs, "results": results, "scope": scope, "filter": f}


# Not evidence (issue #5 "READ THIS FIRST" item 5): stale Drive decks with figures that are not hers (240+ repos,
# $45 a month, P95 450 ms, "deployed in under 48 hours"). The Master Archive bundles the same decks. Matched on the
# document title or path; never shown to the composer.
NOT_EVIDENCE = ("customer engineering case study", "scaled ai knowledge engine", "solutions lifecycle",
                "autonomous technical knowledge engine", "enterprise repository knowledge engine",
                "drive export master archive")


PINNED = [("dr-c5bdf54850b70dedb9fe36fc2c97e51a", "Lilypad Architecture & Engineering Direction: Executive Leadership Guide.docx"),
          # The CV docx is no longer pinned: it carries the recruiter email (owner instruction, 23 Oct).
          ]


# Owner exclusions (23 Oct): never evidence, never cited. The CV docx carries the recruiter email.
BLOCKED_DOCS = ("recruiter email", "dr-4a8d7996f1ebc0e56a6f0ba41c4bed70",
                "google customer engineering case study: scaled ai knowledge engine", "dr-91831587030918c0d48e5d956dee8fe0",
                "google cloud customer engineering & solutions lifecycle", "dr-7f60bd0efff1bacc3d22b9ddd6744d7f",
                "nexus: autonomous technical knowledge engine", "dr-266c181d8e5845bae4bad26656aefb57",
                "vertex ai search & agent builder: enterprise repository knowledge engine", "dr-f4d4fda3457fc62913b584974aa74cb5",
                "drive export master archive", "dr-51fdcac4d5303738aaf137d37daf81bc")


def is_not_evidence(*fields: str) -> bool:
    t = " ".join(f or "" for f in fields).lower()
    if any(x in t for x in BLOCKED_DOCS):  # owner-excluded Drive files, by filename or index id
        return True
    return any(x in t for x in NOT_EVIDENCE)


def evidence_for(nexus: "Nexus", question: str) -> list[dict]:
    """Retrieve evidence for Gemini to compose from: narrative sources (Drive, resumes, profiles, docs) boosted."""
    import answer  # local corpus index: doc id -> text
    body = {"servingConfig": nexus.sc, "query": question, "pageSize": 20,
            "boostSpec": {"conditionBoostSpecs": [
                {"condition": 'kind: ANY("narrative", "profile")', "boost": 0.8},
                {"condition": 'kind: ANY("doc", "readme", "pr", "issue", "pr-external")', "boost": 0.3}]}}
    r = nexus.c.call("POST", f"{nexus.sc}:search", json=body)
    if r.status_code != 200:
        raise RuntimeError(f"Agent Search returned HTTP {r.status_code}")
    global _IDX
    try:
        _IDX
    except NameError:
        _IDX = answer.build_index()
        for p in (ROOT / "state" / "drive-docs" / "scan").glob("*/*.md"):
            _IDX[p.stem] = p
        for p in (ROOT / "state" / "profile-docs" / "scan").glob("*/*.md"):
            _IDX[p.stem] = p
    out = []
    for res in r.json().get("results", []):
        d = res.get("document", {}); sd = d.get("structData", {})
        p = _IDX.get(d.get("id", ""))
        text = p.read_text(encoding="utf-8") if p else ""
        if is_not_evidence(sd.get("path", ""), sd.get("title", ""), text[:300]):
            continue
        text = re.sub(r"[ \t]+", " ", re.sub(r"<[^>]{0,400}>", " ", text))  # docx export leaves XML tags in the text
        if not text.strip():
            continue  # nothing the composer could trace a fact to
        out.append({"kind": sd.get("kind"), "repo": f"{sd.get('owner')}/{sd.get('repo')}", "path": sd.get("path", ""),
                    "url": sd.get("html_url", ""), "text": text})
    out = out[:6]
    # Issue #21: code-only facts. (a) Facts layer: cited technology facts extracted from every cloned repo.
    # (b) Query planning: re-search the index in code vocabulary for the technologies the question names,
    # unboosted, so deploy scripts (rank 1 for "gcloud") reach the composer.
    try:
        import facts_layer
        facts = facts_layer.facts_for(question)
        seen = {e["path"] for e in out}
        terms = {"Google Cloud": "gcloud GCP deploy", "Gemini / Vertex AI": "gemini vertex", "LangGraph": "langgraph create_react_agent",
                 "LangChain": "langchain", "Model Context Protocol (MCP)": "MCP server", "Kubernetes / Helm": "helm kubernetes",
                 "Terraform (IaC)": "terraform", "Prometheus / Grafana / OpenTelemetry": "prometheus grafana",
                 "LiteLLM gateway": "litellm failover", "Kafka streaming": "kafka"}
        extra = []
        for f in facts[:2]:
            t = f["path"].replace("facts: ", "")
            if t not in terms:
                continue
            rr = nexus.c.call("POST", f"{nexus.sc}:search", json={"servingConfig": nexus.sc, "query": terms[t], "pageSize": 8})
            for res in (rr.json().get("results", []) if rr.status_code == 200 else []):
                d = res.get("document", {}); sd = d.get("structData", {})
                path = sd.get("path", "")
                if path in seen or "/litellm/llms/" in f"/{path}" or "docs/my-website" in path or is_not_evidence(path, sd.get("title", "")):
                    continue
                if sd.get("owner") not in ("Lilypad-Tech", "DeveloperAlly") or sd.get("repo") in facts_layer._EX["exclude_repos"]:
                    continue
                p = _IDX.get(d.get("id", ""))
                text = re.sub(r"[ \t]+", " ", re.sub(r"<[^>]{0,400}>", " ", p.read_text(encoding="utf-8"))) if p else ""
                if text.strip():
                    seen.add(path)
                    extra.append({"kind": sd.get("kind"), "repo": f"{sd.get('owner')}/{sd.get('repo')}", "path": path,
                                  "url": sd.get("html_url", ""), "text": text})
                if len(extra) >= 3:
                    break
        out = facts + out[:4] + extra
    except Exception as e:  # never break the answer path; record why
        sys.stderr.write(f"facts layer skipped: {e}\n")
    # Her own narrative documents, always in front of the composer (issue #6: prefer these over code and decks).
    # Item 12: owner_facts.md pinned first; the AI & Cloud Engineering Portfolio is unpinned.
    of = ROOT / "state" / "owner_facts.md"
    if of.exists():
        out.insert(0, {"kind": "owner_facts", "repo": "DeveloperAlly/owner", "path": "state/owner_facts.md", "url": "",
                       "text": of.read_text(encoding="utf-8")})
    # Never cite a private repo or the recruiter-email docx; strip private repo names from owner facts text.
    import facts_layer
    out = [e for e in out if not facts_layer.is_private(e["repo"]) and not is_not_evidence(e["path"], e.get("url", ""), e.get("text", "")[:300])]
    for e in out:
        if e["kind"] == "owner_facts":
            for r in facts_layer.PRIVATE:
                e["text"] = re.sub(r"\b(" + re.escape(r) + "|" + re.escape(r.split("/")[-1]) + r")\b(?=[\s.,;)])", "a private repo", e["text"]) if len(r.split("/")[-1]) > 6 else e["text"]
    have = {e["path"] for e in out}
    for stem, path in PINNED:
        p = _IDX.get(stem)
        if p and path not in have:
            t = re.sub(r"[ \t]+", " ", re.sub(r"<[^>]{0,400}>", " ", p.read_text(encoding="utf-8")))
            out.append({"kind": "narrative", "repo": "DeveloperAlly/drive", "path": path,
                        "url": "https://drive.google.com/drive/folders/13vtP57CJYxmBtNAG6fFsUBOGNC7fi9p2", "text": t})
    return out


def stages_html() -> bytes:
    import html as H, compose
    prof, cards = compose.role_profile(), compose.story_cards()
    def esc(x): return H.escape(str(x))
    reqs = "".join(f"<li><b>{esc(r.get('id'))}</b> {esc(r.get('text'))} <span class=m>{esc(r.get('source',''))}</span>"
                   + ("<ul>" + "".join(f"<li>{esc(q)}</li>" for q in r.get('sample_questions', [])) + "</ul>" if r.get('sample_questions') else "")
                   + "</li>" for r in prof.get("requirements", []))
    def slot(c, k):
        v = c.get(k, "")
        return f"<div><b>{k}</b>: " + (f"<span class=miss>missing</span>" if v == "missing" else esc(v)) + "</div>"
    cs = "".join(f"<section><h3>{esc(c.get('id'))} {esc(c.get('project'))} <span class=m>{esc(','.join(c.get('requirement_ids', [])))} | role: {esc(c.get('her_role'))}</span></h3>"
                 + "".join(slot(c, k) for k in ("situation", "task", "action", "result", "metric"))
                 + "<div class=m>sources: " + "; ".join(esc(s.get('path_or_url', '')) for s in c.get('sources', [])) + "</div></section>"
                 for c in cards.get("cards", []))
    drive = len(list((ROOT / "state" / "drive-docs" / "corpus" / "ds-code").glob("*.html"))) if (ROOT / "state" / "drive-docs").exists() else 0
    gaps = (ROOT / "state" / "story_cards_gaps.md")
    gaps_t = esc(gaps.read_text(encoding="utf-8")) if gaps.exists() else "not yet written"
    page = f"""<!doctype html><html><head><meta charset=utf-8><meta http-equiv=refresh content=30><title>Nexus stages</title>
<style>body{{font:15px/1.5 system-ui;max-width:1000px;margin:0 auto;padding:16px;background:#f6f7f8;color:#1b2228}}
section{{background:#fff;border:1px solid #dde2e6;border-radius:8px;padding:10px 14px;margin:10px 0}}.m{{color:#667;font-size:12px}}
.miss{{color:#b00;font-weight:600}}h2{{margin-top:28px}}pre{{white-space:pre-wrap;background:#fff;padding:10px;border:1px solid #dde2e6}}
@media (prefers-color-scheme:dark){{body{{background:#121416;color:#e4e7ea}}section,pre{{background:#1b1e21;border-color:#2c3136}}}}</style></head><body>
<h1>Nexus: build stages</h1><p class=m>Refreshes every 30 seconds. <a href="/">Ask a question</a></p>
<h2>C1 Drive ingest</h2><p>{drive} Drive documents extracted and indexed.</p>
<h2>C2 Role profile: what Google is hiring for ({len(prof.get('requirements', []))} requirements)</h2><ul>{reqs}</ul>
<h2>C3 Story cards ({len(cards.get('cards', []))})</h2>{cs or '<p>None yet.</p>'}
<h2>Gap questions for the owner</h2><pre>{gaps_t}</pre></body></html>"""
    return page.encode()


def make_handler(nexus: Nexus):
    page = (ROOT / "web" / "index.html").read_bytes()

    class H(BaseHTTPRequestHandler):
        def _send(self, code, body: bytes, ctype="application/json"):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path in ("/", "/answer"):
                self._send(200, (ROOT / "web" / "answer.html").read_bytes(), "text/html; charset=utf-8")
            elif self.path in ("/search", "/index.html"):
                self._send(200, page, "text/html; charset=utf-8")
            elif self.path == "/api/questions":  # the owner's question bank: practice, ask-them and logistics lists
                import compose
                lists = {"practice": [], "ask_them": [], "logistics": []}
                for q in compose.bank_questions():
                    k = "practice" if q.get("kind") in ("interview", "probe") else q.get("kind")
                    if k in lists:
                        lists[k].append({x: q.get(x) for x in ("id", "text", "category", "kind")})
                self._send(200, json.dumps(lists).encode())
            elif self.path == "/stages":
                self._send(200, stages_html(), "text/html; charset=utf-8")
            else:
                self._send(404, b'{"error":"not found"}')

        def do_POST(self):
            if self.path == "/api/answer":
                try:
                    n = max(0, int(self.headers.get("Content-Length", "0") or 0))
                    body = json.loads(self.rfile.read(min(n, 20000)) or b"{}")
                    q = str(body.get("question", "")).strip()[:1000]
                    if not q:
                        return self._send(400, b'{"error":"empty question"}')
                    import compose
                    qid = str(body.get("qid") or "") or None
                    if body.get("match") == "gemini":  # only when the user asks: Gemini picks the bank question
                        bq, _how = compose.match_bank(q)
                        qid = bq["id"] if bq else qid
                    out = compose.fast(q, qid)  # instant from cards; Gemini only to match a low-confidence question
                    if body.get("match") == "gemini" and out.get("matched"):
                        out["matched"]["how"] = "nearest bank question by meaning (Gemini)"
                    return self._send(200, json.dumps(out).encode())
                except Exception as e:
                    return self._send(502, json.dumps({"error": str(e)[:400]}).encode())
            if self.path == "/api/tailor":  # one Gemini call for one card
                try:
                    n = max(0, int(self.headers.get("Content-Length", "0") or 0))
                    body = json.loads(self.rfile.read(min(n, 20000)) or b"{}")
                    q = str(body.get("question", "")).strip()[:1000]
                    if not q or not body.get("story_ref"):
                        return self._send(400, b'{"error":"question and story_ref required"}')
                    import compose
                    out = compose.tailor(q, evidence_for(nexus, q), str(body["story_ref"]), str(body.get("qid") or "") or None)
                    out = json.loads(compose.scrub_names(json.dumps(out, ensure_ascii=False)))
                    return self._send(200, json.dumps(out).encode())
                except Exception as e:
                    return self._send(502, json.dumps({"error": str(e)[:400]}).encode())
            if self.path != "/api/ask":
                return self._send(404, b'{"error":"not found"}')
            try:
                n = max(0, int(self.headers.get("Content-Length", "0") or 0))
                req = json.loads(self.rfile.read(min(n, 20000)) or b"{}")
                q = str(req.get("question", "")).strip()[:1000]
                scope = "all" if req.get("scope") == "all" else "demo"
                if not q:
                    return self._send(400, b'{"error":"empty question"}')
                self._send(200, json.dumps(nexus.ask(q, scope)).encode())
            except Exception as e:  # shown to the user as an error; never replaced with a canned answer
                self._send(502, json.dumps({"error": str(e)[:500]}).encode())

        def log_message(self, fmt, *args):  # no question text or answers in logs
            sys.stderr.write(f"{self.command} {self.path.split('?')[0]} {args[1] if len(args) > 1 else ''}\n")

    return H


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default="ally-nexus-poc")
    ap.add_argument("--engine", default="nexus-lite")
    ap.add_argument("--port", type=int, default=8765)
    a = ap.parse_args()
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), make_handler(Nexus(a.project, a.engine)))
    print(f"Nexus interview assistant on http://127.0.0.1:{a.port}  (local only; Ctrl+C to stop)")
    srv.serve_forever()


if __name__ == "__main__":
    main()
