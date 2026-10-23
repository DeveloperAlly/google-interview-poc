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
            if self.path in ("/", "/index.html"):
                self._send(200, page, "text/html; charset=utf-8")
            else:
                self._send(404, b'{"error":"not found"}')

        def do_POST(self):
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
