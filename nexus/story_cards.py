"""C3 story cards: draft one interview story per recruiter topic from on-disk sources.

Gemini drafts each slot with a verbatim quote and the source path it came from.
This script then checks every quote against the source text. A slot whose quote is
not found, whose numbers are not in its quotes, or which carries a disproved figure
is replaced with "missing". The output file is rewritten after every card so it is
always valid JSON.

Usage: python nexus/story_cards.py [R1 R2 ...]
Run from the main checkout root (it reads state/ there).
"""
import html
import json
import os
import re
import sys
import time
import zipfile
from pathlib import Path

ROOT = Path(os.environ.get("NEXUS_ROOT", Path(__file__).resolve().parents[1]))  # nexus/ -> repo root
STATE = ROOT / "state"
OUT = STATE / "story_cards.json"
MC = "state/clones/DeveloperAlly/my-content"
DRIVE = "state/drive"
# Owner decisions on #5 (6 to 11). Overrides any other source; cited as self-reported.
OWNER_FACTS = "state/owner_facts.md"
REPO_URL = "https://github.com/DeveloperAlly/google-interview-poc/blob/main/"

# Figures disproved or unverified by the build (issue #8 addendum). Never on a card.
BANNED = [r"240\+", r"\b57\b", r"\b113\b", r"37 model", r"zero hallucination", r"100% recall",
          r"\$45", r"8x", r"15\+ hours", r"sub-second", r"450 ?ms", r"\b830", r"99\.9", r"100% uptime"]

SLOTS = ["situation", "task", "action", "result", "metric"]

RESUMES = [f"{MC}/resumes/Ally_Haire_Resume_n8n_DevAdvocate_v4.md",
           f"{MC}/resumes/Ally_Haire_Resume_NVIDIA_ANZ_DevRel.md"]
EVIDENCE = [f"{MC}/brand/evidence/achievement-inventory.md",
            f"{MC}/brand/evidence/role-functions-and-skills.md",
            f"{MC}/brand/evidence/corroboration-ledger.md"]
GUIDE = f"{DRIVE}/Lilypad Architecture & Engineering Direction: Executive Leadership Guide.docx"
PORTFOLIO = f"{DRIVE}/AI & Cloud Engineering Portfolio (2024–2026).docx"

TOPICS = {
    "R1": ("AI platform integration",
           "Lilypad: Module Framework and the anura OpenAI-compatible API gateway with LiteLLM failover",
           [GUIDE, PORTFOLIO] + EVIDENCE + RESUMES),
    "R2": ("program management",
           "Filecoin Virtual Machine (FVM) developer experience launch and the Space Warp hackathon",
           EVIDENCE + RESUMES + [f"{MC}/brand/story/career-story.md"]),
    "R3": ("technical execution",
           "Lilypad v0: the FVM smart contract to Bacalhau compute bridge, hands-on prototype",
           [GUIDE] + EVIDENCE + RESUMES),
    "R4": ("feasibility assessments",
           "Nexus: feasibility of indexing her repositories into Google Agent Search (this repo's engagement record)",
           ["docs/01-discovery-and-feasibility.md", "docs/05-cost-and-commercials.md", "docs/03-delivery-log.md"]),
    "R5": ("code-level context",
           "Nexus: ingestion pipeline and answer layer over Google Agent Search (this repo's engagement record)",
           ["docs/00-architecture.md", "docs/02-solution-design.md", "docs/03-delivery-log.md",
            "docs/08-answer-layer.md"]),
    "R6": ("multi-stakeholder engagement",
           "Livepeer DocsOS: docs-as-infrastructure across Livepeer core teams and community contributors",
           [f"{DRIVE}/Livepeer DocsOS: Product & Engineering Architecture.pptx", GUIDE, f"{MC}/brand/evidence/corroboration-ledger.md"]),
    "R7": ("pre-sales to post-sales",
           "Dell enterprise partnership: permissioned, licensable Lilypad for enterprise AI",
           [f"{DRIVE}/dell/Dell <> Lilypad Deck.docx", f"{DRIVE}/dell/Lilypad Product Deck & Dell Proposal.pptx"]
           + EVIDENCE + RESUMES),
}


def extract(path: Path) -> str:
    if path.suffix not in (".docx", ".pptx"):
        return path.read_text(errors="replace")
    z = zipfile.ZipFile(path)
    names = z.namelist()
    parts = []
    if "word/document.xml" in names:
        x = z.read("word/document.xml").decode()
        parts.append(re.sub(r"<[^>]+>", "", re.sub(r"</w:p>", "\n", x)))
    else:
        num = lambda n: int(re.findall(r"(\d+)\.xml", n)[0])
        for pat in (r"ppt/slides/slide\d+\.xml", r"ppt/notesSlides/notesSlide\d+\.xml"):
            for n in sorted((n for n in names if re.match(pat, n)), key=num):
                x = z.read(n).decode()
                parts.append(f"[{n}]\n" + re.sub(r"<[^>]+>", "", re.sub(r"</a:p>", "\n", x)))
    return html.unescape("\n".join(parts))


def norm(s: str) -> str:
    s = s.replace("\\", "").replace("*", "").replace("’", "'").replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", s).strip().lower()


NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")


def numbers(s: str) -> set:
    """Whole numbers in s, commas removed, so '1,534' matches '1534' but '15' does not match '1534'."""
    return {n.replace(",", "") for n in NUM.findall(s)}


def url_for(path: str) -> str:
    """A link that opens: repo docs on GitHub, cloned repos on their own GitHub. Drive and state files stay local."""
    if path.startswith("docs/"):
        return REPO_URL + path
    m = re.match(r"state/clones/([^/]+)/([^/]+)/(.+)", path)
    if m:
        return f"https://github.com/{m[1]}/{m[2]}/blob/HEAD/{m[3]}"
    return ""


def self_reported(path: str) -> bool:
    # Only this repo's engagement record counts as a record; decks, portfolio and CV-derived files are self-reported.
    return not path.startswith("docs/")


def gemini(prompt: str) -> dict:
    from google import genai
    from google.genai import types
    key = None
    for line in (STATE / ".env").read_text().splitlines():
        if line.startswith("GEMINI_API_KEY="):
            key = line.split("=", 1)[1].strip().strip('"')
    client = genai.Client(api_key=key)
    cfg = types.GenerateContentConfig(response_mime_type="application/json", temperature=0.2)
    last = None
    for model in ("gemini-3-flash-preview", "gemini-3.1-flash-lite", "gemini-3-flash-preview"):
        try:
            r = client.models.generate_content(model=model, contents=prompt, config=cfg)
            return json.loads(r.text)
        except Exception as e:  # 503/429 and malformed JSON both fall through to the next model
            last = e
            time.sleep(3)
    raise RuntimeError(f"gemini failed: {last}")


PROMPT = """You are drafting ONE interview story for Ally Haire (she/her) for a Google AI Outcome Customer
Engineer interview. Recruiter topic: {topic}. Project: {project}.

Use ONLY the sources below. Each source starts with SOURCE: <path>. Where {owner_facts} conflicts with any other
source, {owner_facts} wins (titles, dates, scale, role); quote it for those slots.
Return JSON:
{{"project": "<short project name>",
  "her_role": {{"value": "built|led|directed|missing", "source": "<path>", "quote": "<verbatim>"}},
  "situation": {{"text": "...", "evidence": [{{"source": "<path>", "quote": "<verbatim>"}}]}},
  "task": ..., "action": ..., "result": ..., "metric": ...,
  "gap_questions": {{"<slot>": "<short direct question to Ally, answerable in under two minutes>"}}}}

Rules:
- "text" is first person ("I ..."), 1 to 3 plain sentences she can say aloud, restating ONLY what the quotes say.
- Every quote is copied character for character from its source, 8 to 40 words, no ellipses.
- Every number in "text" must appear in one of its quotes. Never round, infer or combine figures.
- If no source states a slot, set it to {{"text": "missing", "evidence": []}} and add a gap question for it.
- "metric" is a number or measurable outcome stated in a source; otherwise missing.
- her_role: "built" only if a source says she built/wrote/coded it; "directed" if a source says she directed it;
  "led" if a source says she led it. Never choose by judgement.
- Never use these figures: 240+ repos, 57 or 113 repos, 37 model specs, zero hallucinations, 100% recall,
  $45/month, 8x ROI, 15+ hours/week, sub-second, 450 ms, 830 files, 99.9% or 100% uptime.
- No em dashes. No emojis.

{sources}
"""


def verify(slot: dict, texts: dict) -> tuple:
    """Return (text, sources) with the slot reduced to missing if any check fails."""
    if not isinstance(slot, dict):
        slot = {}
    text = slot.get("text", "missing") or "missing"
    ev = slot.get("evidence", []) or []
    if text.strip().lower() == "missing" or not ev:
        return "missing", [], "no source"
    good = []
    for e in ev:
        src, q = e.get("source", ""), e.get("quote", "")
        # Every quote must verify. One invented quote voids the slot, even if another quote is real.
        if not (src in texts and len(norm(q)) > 15 and norm(q) in norm(texts[src])):
            return "missing", [], f"quote not found in {src or 'unnamed source'}"
        good.append({"path_or_url": src, "url": url_for(src), "quote": q, "self_reported": self_reported(src)})
    quoted = set().union(*(numbers(g["quote"]) for g in good))
    for n in numbers(text):
        if n not in quoted:
            return "missing", [], f"number {n} not in quotes"
    for b in BANNED:
        if re.search(b, text, re.I):
            return "missing", [], f"banned figure {b}"
    if "—" in text:
        text = text.replace(" — ", ", ").replace("—", ", ")
    return text, good, ""


def load_out() -> dict:
    if OUT.exists():
        try:
            return json.loads(OUT.read_text())
        except json.JSONDecodeError:
            pass
    return {"cards": []}


def write_out(doc: dict) -> None:
    tmp = OUT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(doc, indent=2, ensure_ascii=False))
    tmp.replace(OUT)  # atomic: the Stages page never sees half a file


def build(rid: str) -> dict:
    topic, project, paths = TOPICS[rid]
    paths = [OWNER_FACTS] + [p for p in paths if p != OWNER_FACTS]
    texts = {}
    for p in paths:
        f = ROOT / p
        if f.exists():
            texts[p] = extract(f)
    sources = "\n\n".join(f"SOURCE: {p}\n{t}" for p, t in texts.items())
    d = gemini(PROMPT.format(topic=topic, project=project, sources=sources, owner_facts=OWNER_FACTS))
    if isinstance(d, list):
        d = d[0] if d and isinstance(d[0], dict) else {}
    card = {"id": "S" + rid[1:], "requirement_ids": [rid], "topic": topic,
            "project": d.get("project") or project}
    srcs, rejects, sr_slots = [], {}, []
    role = d.get("her_role") if isinstance(d.get("her_role"), dict) else {}
    rv = role.get("value", "missing")
    rq, rs = role.get("quote", ""), role.get("source", "")
    if rv in ("built", "led", "directed") and rs in texts and norm(rq) and norm(rq) in norm(texts[rs]):
        card["her_role"] = rv
        srcs.append({"path_or_url": rs, "url": url_for(rs), "supports": "role", "quote": rq,
                     "self_reported": self_reported(rs)})
        if self_reported(rs):
            sr_slots.append("role")
    else:
        card["her_role"] = "missing"
        rejects["role"] = "role quote not found" if rv != "missing" else "no source"
    for s in SLOTS:
        text, good, why = verify(d.get(s), texts)
        card[s] = text
        if why:
            rejects[s] = why
        for g in good:
            srcs.append({"path_or_url": g["path_or_url"], "url": g["url"], "supports": s, "quote": g["quote"],
                         "self_reported": g["self_reported"]})
        if good and all(g["self_reported"] for g in good):
            sr_slots.append(s)
    card["sources"] = srcs
    card["self_reported_slots"] = sr_slots
    gq = d.get("gap_questions") or {}
    card["gaps"] = {k: gq.get(k, f"Which document states the {k} for {card['project']}?")
                    for k in rejects}
    card["sources_read"] = list(texts)
    card["sources_absent"] = [p for p in paths if p not in texts]
    return card


def main(ids):
    import fcntl
    for rid in ids:
        card = build(rid)
        lock = open(STATE / "story_cards.lock", "w")
        fcntl.flock(lock, fcntl.LOCK_EX)  # parallel runs, one per topic, merge safely
        doc = load_out()
        doc["cards"] = [c for c in doc["cards"] if c["id"] != card["id"]] + [card]
        doc["cards"].sort(key=lambda c: int(c["id"][1:]))
        write_out(doc)
        fcntl.flock(lock, fcntl.LOCK_UN)
        filled = sum(card[s] != "missing" for s in SLOTS)
        print(f"{card['id']} {card['topic']}: role={card['her_role']} filled={filled}/5 gaps={list(card['gaps'])}")


if __name__ == "__main__":
    main(sys.argv[1:] or list(TOPICS))
