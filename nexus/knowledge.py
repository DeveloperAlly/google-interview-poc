"""Two RAG stores, queried together (no frozen answer-path file is touched).

  evidence   nexus-lite    her own work: repos, PRs, issues, my-content, Drive narrative, profile docs
  reference  nexus-google  Google's view: Next '26 talk transcripts and summaries, Google Cloud case studies

Rule: reference material is never evidence of her experience. A composed answer may say what Google says or
how Google positions something, cited [G#]; anything about what she did must cite an evidence source [E#].
"""
from __future__ import annotations
import html, json, os, re, time
from pathlib import Path
from datastores import Client

MAIN = Path(os.environ.get("NEXUS_MAIN", Path(__file__).resolve().parents[3] if ".worktrees" in str(Path(__file__)) else Path(__file__).resolve().parents[1]))
STATE = MAIN / "state"
PROJECT = os.environ.get("NEXUS_PROJECT", "ally-nexus-poc")
ENGINES = {"evidence": "nexus-lite", "docs": "nexus-docs", "reference": "nexus-google"}
NOT_EVIDENCE = ("customer engineering case study", "scaled ai knowledge engine", "solutions lifecycle",
                "autonomous technical knowledge engine", "enterprise repository knowledge engine",
                "drive export master archive")
LIBRARY = re.compile(r"(^|/)litellm/llms/|docs/my-website/|node_modules/")
# Background research notes about other companies' products: her work, but not evidence of her experience.
RESEARCH = re.compile(r"(^|/)(context/)?research/|competitor|(^|/)drafts/|job-search|linkedin-job|(^|/)foundation/(OUTCOMES|PRD)\.md$", re.I)
MODELS = ["gemini-3.1-flash-lite", "gemini-3.1-flash-lite-preview", "gemini-flash-lite-latest"]
_C = None
_IDX = None


def client() -> Client:
    global _C
    if _C is None:
        _C = Client(PROJECT)
    return _C


def _index() -> dict:
    """doc id -> local text file, for both stores (the index returns ids and metadata, not full text)."""
    global _IDX
    if _IDX is None:
        _IDX = {p.stem: p for p in STATE.glob("*/scan/*/*.md")}
        _IDX.update({p.stem: p for p in STATE.glob("*/*/scan/*/*.md")})
        _IDX.update({p.stem: p for p in (STATE / "google" / "corpus" / "ds-google-lite").glob("*.html")})
        _IDX.update({p.stem: p for p in (STATE / "docs" / "corpus" / "ds-docs-lite").glob("*.html")})
    return _IDX


def _text(doc_id: str) -> str:
    p = _index().get(doc_id)
    if not p:
        return ""
    t = p.read_text(encoding="utf-8", errors="replace")
    if p.suffix == ".html" and "<pre>" in t:
        t = html.unescape(t.split("<pre>", 1)[1].rsplit("</pre>", 1)[0])
    return re.sub(r"[ \t]+", " ", re.sub(r"<[^>]{0,400}>", " ", t))


def window(text: str, query: str, n: int) -> str:
    """The n-character passage of text that best matches the query terms (long docs: the first n chars often miss)."""
    if len(text) <= n:
        return text
    terms = {w for w in re.findall(r"[a-z0-9]{4,}", query.lower())}
    if not terms:
        return text[:n]
    step = max(n // 4, 200)
    best, best_i = -1, 0
    for i in range(0, len(text) - n + step, step):
        seg = text[i:i + n].lower()
        sc = sum(seg.count(t) for t in terms)
        if sc > best:
            best, best_i = sc, i
    return text[best_i:best_i + n]


def search(store: str, query: str, k: int = 8, repo: str | None = None) -> list[dict]:
    c = client()
    sc = f"{c.base}/engines/{ENGINES[store]}/servingConfigs/default_search"
    body = {"servingConfig": sc, "query": query, "pageSize": 50 if repo else 25,
            "contentSearchSpec": {"snippetSpec": {"returnSnippet": True}}}
    r = c.call("POST", f"{sc}:search", json=body)
    if r.status_code != 200:
        raise RuntimeError(f"{store} search HTTP {r.status_code}: {r.text[:200]}")
    out, seen = [], set()
    for res in r.json().get("results", []):
        d = res.get("document", {}); sd = d.get("structData", {}) or {}
        path, title = sd.get("path", ""), sd.get("title", "")
        if store == "evidence":
            if any(x in f"{path} {title}".lower() for x in NOT_EVIDENCE) or LIBRARY.search(path) or RESEARCH.search(path):
                continue
            if repo and sd.get("repo") != repo:
                continue
        snip = " ".join(s.get("snippet", "") for s in (d.get("derivedStructData", {}) or {}).get("snippets", []) if s.get("snippet"))
        if store == "reference" and sd.get("pair_id"):
            key = min(d.get("id", ""), sd["pair_id"])  # pair_id names the partner doc, so key on the pair
            if key in seen:
                continue  # a talk and its summary are one source; keep the higher-ranked
            seen.add(key)
        out.append({"store": store, "id": d.get("id"), "kind": sd.get("kind"), "owner": sd.get("owner"),
                    "repo": sd.get("repo"), "path": path, "title": title or path.rsplit("/", 1)[-1],
                    "event": sd.get("event", ""), "url": sd.get("html_url", ""), "era": sd.get("era", ""),
                    "snippet": re.sub(r"<[^>]+>", "", html.unescape(snip))[:400]})
        if len(out) >= k:
            break
    return out


def gemini_key() -> str:
    for line in (STATE / ".env").read_text().splitlines():
        if line.startswith("GEMINI_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError("GEMINI_API_KEY missing from state/.env")


def compose(question: str, ev: list[dict], ref: list[dict]) -> dict:
    from google import genai
    from google.genai import types
    owner = (STATE / "owner_facts.md").read_text(encoding="utf-8") if (STATE / "owner_facts.md").exists() else ""
    def block(tag, rows, n):
        return "\n\n".join(f'<source id="{tag}{i+1}" title="{x["title"]}" path="{x["path"]}" repo="{x.get("owner") or ""}/{x.get("repo") or ""}"{(" era=" + chr(34) + x["era"] + chr(34)) if x.get("era") else ""}>\n'
                           f'{window(_text(x["id"]), question + " " + x["snippet"], n) or x["snippet"]}\n</source>' for i, x in enumerate(rows))
    prompt = f"""You help Ally Haire prepare for a Google Cloud AI Outcome Customer Engineer interview.
Answer the question using two kinds of sources.

EVIDENCE sources [E#] are her own work. Only these, or the OWNER FACTS cited as [F], can support anything about
what she did, built, led or directed. Cite [E#] only for a claim that appears in that source's text; a claim that
comes from the owner facts cites [F]. Never attach an [E#] to a claim the source does not contain.
REFERENCE sources [G#] are Google's talks and customer case studies. Use them only for what Google says, ships,
recommends, or what a named Google customer did. NEVER present reference content as her experience, and never
merge a Google customer's result into her story.

OWNER FACTS (authoritative about her; never contradict):
{owner}

Write a spoken first-person answer of 120 to 280 words where the question is about her; where it is about Google's
platform or approach, answer as she would explain it, attributing Google's points ("Google positions...", "At Next
'26 Google showed..."). Cite every factual sentence with [E#] or [G#]. If the evidence does not cover something she
would need to have done, say so plainly instead of filling it. Keep the era straight: Lilypad v0 and Waterlily
were built at Protocol Labs; Lilypad Network (Sep 2023 to Oct 2025) work she directed as Founder & CEO.
Attribute each fact to the employer or project its own source names (the repo attribute shows where it came from:
Lilypad-Tech repos and Lilypad work docs are Lilypad Network; DeveloperAlly repos are her own projects; talk
transcripts carry the employer they mention). If a source names no employer, assign none: say "in a talk I gave on
X" or describe the work without an employer. Do not open a sentence with "As Founder & CEO of Lilypad" unless that
sentence's facts come from a Lilypad source. Nexus is her own build (October 2026), after Lilypad, not Lilypad work.
Use only the owner facts and sources that answer THIS question; do not add an unrelated project (for example
Nexus) or an unrelated achievement just because it is listed. Do not connect two facts (one tool "to ensure"
another outcome) unless a single source states that link. Two to four specific, relevant facts beat eight loose ones.
Return JSON only.

EVIDENCE:
{block("E", ev, 3000)}

REFERENCE:
{block("G", ref, 4000)}

QUESTION: {question}"""
    schema = {"type": "object", "properties": {
        "answer": {"type": "string"},
        "evidence_used": {"type": "array", "items": {"type": "string"}},
        "reference_used": {"type": "array", "items": {"type": "string"}},
        "gaps": {"type": "array", "items": {"type": "string"}}},
        "required": ["answer", "evidence_used", "reference_used", "gaps"]}
    texts = {f"E{i+1}": _text(x["id"]) + " " + x["snippet"] + " " + x["path"] + " " + (x.get("owner") or "")
             for i, x in enumerate(ev)}
    cli = genai.Client(api_key=gemini_key())
    last, base = None, prompt
    for m in MODELS:
        feedback = []
        for attempt in range(3):
            try:
                ask_prompt = base + ("\n\nFIX THESE PROBLEMS IN YOUR PREVIOUS ANSWER:\n- " + "\n- ".join(feedback) if feedback else "")
                r = cli.models.generate_content(model=m, contents=ask_prompt, config=types.GenerateContentConfig(
                    response_mime_type="application/json", response_schema=schema, temperature=0.2))
                out = json.loads(r.text); out["model"] = m
                problems = check(out.get("answer", ""), texts, bool(ev or ref))
                if problems and attempt < 2:
                    feedback = problems
                    continue
                if problems:
                    out["unresolved"] = problems
                bad = sorted(set(re.findall(r"\[?E(\d+)", out.get("answer", ""))) - {str(i + 1) for i in range(len(ev))})
                if bad:
                    out["citation_errors"] = [f"E{b}" for b in bad]
                out["retries"] = attempt
                return out
            except Exception as e:  # 429/503: retry, then next model
                last = e; time.sleep(2)
    raise RuntimeError(f"Gemini unavailable: {str(last)[:200]}")


ORG = {"Lilypad": "lilypad", "Protocol Labs": "protocol labs|filecoin|fvm", "IBM": "ibm", "Livepeer": "livepeer"}


def check(answer: str, texts: dict, has_sources: bool) -> list[str]:
    """Deterministic checks the model must pass: inline citations exist, and a sentence that places work at an
    employer cites [F] or at least one source whose text names that employer."""
    out = []
    if has_sources and not re.search(r"\[(?:[EG]\d+|F)", answer):
        out.append("No inline citations. End every factual sentence with its tag, e.g. [E2], [G1] or [F].")
    for sent in re.split(r"(?<=[.!?])\s+(?=[A-Z])", answer):
        if re.search(r"\bF\]|\[F\b|Owner", sent):
            continue
        cited = re.findall(r"E(\d+)", sent)
        if re.search(r"\b(I|I've|I'm|my|we|our)\b", sent) and re.search(r"G\d", sent) and not cited:
            out.append(f'This sentence makes a first-person claim supported only by a Google source: "{sent[:160]}". '
                       f'Attribute the point to Google without "I"/"we", or cite her own source.')
        for org, pat in ORG.items():
            if re.search(rf"\b{org}", sent) and cited and not any(
                    re.search(pat, texts.get(f"E{c}", ""), re.I) for c in cited):
                out.append(f'This sentence places work at {org}, but none of its sources ({", ".join("E" + c for c in cited)}) '
                           f'mention {org}: "{sent[:160]}". Remove the employer or cite a source that names it.')
    return out


def plan(question: str) -> dict:
    """Split a question into short keyword queries per store. One question often asks about her AND about Google;
    sending the whole sentence to both stores retrieves neither well. Falls back to the raw question."""
    try:
        from google import genai
        from google.genai import types
        schema = {"type": "object", "properties": {
            "evidence_queries": {"type": "array", "items": {"type": "string"}},
            "reference_query": {"type": "string"}}, "required": ["evidence_queries", "reference_query"]}
        r = genai.Client(api_key=gemini_key()).models.generate_content(model=MODELS[0], contents=(
            "Write search queries for two indexes. EVIDENCE holds one person's own code repos, PRs, docs and career "
            "material; REFERENCE holds Google Cloud talks and customer case studies. Give 1 to 3 short keyword "
            "queries (2 to 6 words, concrete technical or project terms, no pronouns) for evidence of her experience "
            "relevant to the question, and one short query for what Google says about it. QUESTION: " + question),
            config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=schema, temperature=0))
        p = json.loads(r.text)
        q = [x for x in p.get("evidence_queries", []) if x.strip()][:3]
        return {"evidence_queries": q or [question], "reference_query": p.get("reference_query") or question}
    except Exception:
        return {"evidence_queries": [question], "reference_query": question}


def _merge(lists: list[list[dict]], k: int) -> list[dict]:
    """Round-robin merge so every query contributes its best hits; dedupe by id."""
    out, seen = [], set()
    for i in range(max((len(l) for l in lists), default=0)):
        for l in lists:
            if i < len(l) and l[i]["id"] not in seen:
                seen.add(l[i]["id"]); out.append(l[i])
    return out[:k]


def ask(question: str, k: int = 6, evidence_repo: str | None = None, compose_answer: bool = True) -> dict:
    t0 = time.time()
    p = plan(question)
    lists = [search("evidence", q, k, repo=evidence_repo) for q in p["evidence_queries"]]
    if evidence_repo in (None, "docs"):
        for q in p["evidence_queries"]:
            try:
                lists.append(search("docs", q, k))
            except RuntimeError:
                pass  # docs store not created yet
    if evidence_repo == "docs":
        lists = lists[len(p["evidence_queries"]):]
    ev = _merge(lists, k + 2)
    ref = search("reference", p["reference_query"], k)
    out = {"question": question, "plan": p, "evidence": ev, "reference": ref}
    if compose_answer:
        try:
            out["composed"] = compose(question, ev, ref)
        except Exception as e:
            out["composed"] = {"error": str(e)[:300]}
    out["seconds"] = round(time.time() - t0, 1)
    return out
