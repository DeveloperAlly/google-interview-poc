"""Build a role profile (contract 1) from any job description and any list of topics.

Usage:
  python nexus/role_profile.py --jd <job description .docx|.pdf|.txt|.md> \
      --topics <topics file, one per line> [--topic-source "recruiter topic"] \
      [--out state/role_profile.json] [--env state/.env]

Nothing about a specific role is in this file. The role name, every requirement
and every sample question come from the job description and the topics file.

Output (contract 1):
  {"role": str, "requirements": [{"id","text","source","sample_questions",...}]}
Topics become R1..Rn in the order given. Posting requirements follow, each with
"posting_line": the verbatim line of the job description it comes from.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import zipfile
from pathlib import Path

PRIMARY_MODEL = "gemini-3-flash-preview"
FALLBACK_MODEL = "gemini-3.1-flash-lite"


def read_jd(path: Path) -> str:
    if path.suffix.lower() == ".docx":
        xml = zipfile.ZipFile(path).read("word/document.xml").decode("utf-8")
        paras = re.findall(r"<w:p[ >].*?</w:p>", xml, re.S)
        lines = [re.sub(r"<[^>]+>", "", p) for p in paras]
        import html
        return "\n".join(html.unescape(l).strip() for l in lines if l.strip())
    if path.suffix.lower() == ".pdf":
        from pypdf import PdfReader  # pip install pypdf
        return "\n".join(pg.extract_text() or "" for pg in PdfReader(str(path)).pages)
    return path.read_text(encoding="utf-8")


def read_topics(path: Path) -> list[str]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip().lstrip("-*0123456789.) ").strip()
        if line and not line.startswith("#"):
            out.append(line)
    return out


def load_key(env_path: Path) -> str:
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        return key
    for line in env_path.read_text().splitlines():
        if line.startswith("GEMINI_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    sys.exit("GEMINI_API_KEY not found")


PROMPT = """You are preparing a candidate for interviews for the role described in the
JOB DESCRIPTION below. The document may also contain other material (emails, a cover
letter, a CV). Use ONLY the job posting itself (title, qualifications, responsibilities,
about-the-job) as the source of requirements. Ignore anything written by the candidate.

Return JSON only, with this shape:
{
  "role": "<the job title and organisation as the posting names it>",
  "summary": "<3 sentences, plain English: what this employer is hiring for, the core of the job, and what separates a strong candidate>",
  "topics": [
    {"topic": "<topic exactly as given>",
     "meaning": "<one sentence: what this topic means for THIS role, citing the posting>",
     "source_line": "<the sentence in the document that names this topic (e.g. in a recruiter email), copied verbatim, or empty>",
     "posting_ids": ["<ids of the posting requirements that evidence this topic>"],
     "sample_questions": ["<4 questions>"],
     "listen_for": "<one sentence: what the interviewer is listening for in a strong answer>"}
  ],
  "posting_requirements": [
    {"text": "<short plain-English name of the requirement, 3 to 10 words>",
     "category": "minimum qualification | preferred qualification | responsibility | role summary",
     "posting_line": "<the exact sentence from the posting, copied verbatim>",
     "topic_ids": ["<ids of the topics this requirement relates to, e.g. R3>"],
     "sample_questions": ["<3 questions>"],
     "listen_for": "<one sentence: what the interviewer is listening for in a strong answer>"}
  ]
}

Rules:
- "topics" must contain exactly these topics, in this order, with ids R1..R{n}:
{topics}
  (if no topics are listed, return "topics": [])
- "posting_requirements": one entry for EVERY minimum qualification, EVERY preferred
  qualification and EVERY responsibility in the posting, in posting order. Also add one
  entry per distinct expectation in the about-the-job summary (e.g. the hats the role
  wears, the scope it bridges, the integration concerns it names). Do not merge lines.
- "posting_line" must be copied character for character from the posting.
- Sample questions are what a real interviewer at this company would ask for this role:
  mix behavioural ("Tell me about a time..."), situational ("A customer...what do you
  do?") and technical probes. Specific to the role, never generic. No placeholders
  such as [Field]; every question must be askable as written.
- Posting requirement ids continue after the topics: the first is R{first}.

TOPICS:
{topic_list}

JOB DESCRIPTION:
{jd}
"""


def call_gemini(key: str, prompt: str) -> dict:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=key)
    cfg = types.GenerateContentConfig(response_mime_type="application/json", temperature=0.3)
    attempts = [PRIMARY_MODEL, PRIMARY_MODEL, FALLBACK_MODEL]
    last = None
    for i, model in enumerate(attempts):
        try:
            r = client.models.generate_content(model=model, contents=prompt, config=cfg)
            return json.loads(r.text)
        except Exception as e:  # 503/429 retry once, then fall back
            last = e
            print(f"[{model}] failed: {str(e)[:160]}", file=sys.stderr)
            time.sleep(2)
    raise SystemExit(f"Gemini failed: {last}")


def norm(s: str) -> str:
    s = s.replace("-\n", "").lower()
    return re.sub(r"[^a-z0-9]+", "", s)


def build(jd_text: str, topics: list[str], topic_source: str, key: str) -> dict:
    topic_list = "\n".join(f"R{i+1}: {t}" for i, t in enumerate(topics))
    prompt = (PROMPT.replace("{topics}", topic_list).replace("{n}", str(len(topics)))
              .replace("{first}", str(len(topics) + 1))
              .replace("{topic_list}", topic_list).replace("{jd}", jd_text))
    data = call_gemini(key, prompt)

    reqs = []
    got = {norm(t.get("topic", "")): t for t in data.get("topics", [])}
    for i, t in enumerate(topics):
        g = got.get(norm(t)) or (data.get("topics", [])[i] if i < len(data.get("topics", [])) else {})
        reqs.append({
            "id": f"R{i+1}", "text": t, "source": topic_source,
            "meaning": g.get("meaning", ""),
            "source_line": g.get("source_line", ""),
            "source_line_verified": bool(g.get("source_line")) and norm(g["source_line"]) in norm(jd_text),
            "related_posting_requirements": g.get("posting_ids", []),
            "sample_questions": g.get("sample_questions", []),
            "listen_for": g.get("listen_for", ""),
        })
    jd_norm = norm(jd_text)
    n = len(topics)
    for p in data.get("posting_requirements", []):
        line = p.get("posting_line", "")
        n += 1
        reqs.append({
            "id": f"R{n}", "text": p.get("text", ""),
            "source": f"job posting: {p.get('category', '')}".strip(),
            "posting_line": line,
            "posting_line_verified": bool(line) and norm(line) in jd_norm,
            "related_topics": p.get("topic_ids", []),
            "sample_questions": p.get("sample_questions", []),
            "listen_for": p.get("listen_for", ""),
        })
    return {"role": data.get("role", ""), "summary": data.get("summary", ""), "requirements": reqs}


def write_atomic(obj: dict, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, out)


def render_md(profile: dict) -> str:
    """Readable rendering of a profile, for the owner and the verifier."""
    out = [f"# {profile['role']}: what they are hiring for", "", profile.get("summary", ""), ""]
    for r in profile["requirements"]:
        line = r.get("posting_line") or r.get("source_line") or ""
        rel = r.get("related_posting_requirements") or r.get("related_topics") or []
        out.append(f"## {r['id']} {r['text']} ({r['source']})")
        if r.get("meaning"):
            out += [f"*{r['meaning']}*", ""]
        if line:
            out += [f"> {line}", ""]
        if rel:
            out += [f"Related: {', '.join(rel)}", ""]
        out += [f"- {q}" for q in r["sample_questions"]]
        if r.get("listen_for"):
            out += ["", f"**Listen for:** {r['listen_for']}"]
        out.append("")
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jd", type=Path)
    ap.add_argument("--topics", type=Path, help="optional; without it only posting requirements are produced")
    ap.add_argument("--topic-source", default="recruiter topic")
    ap.add_argument("--out", type=Path, default=Path("state/role_profile.json"))
    ap.add_argument("--env", type=Path, default=Path("state/.env"))
    ap.add_argument("--render", type=Path, help="render an existing profile JSON to Markdown on stdout")
    a = ap.parse_args()
    if a.render:
        print(render_md(json.loads(a.render.read_text())))
        return
    if not a.jd:
        sys.exit("--jd is required")
    profile = build(read_jd(a.jd), read_topics(a.topics) if a.topics else [], a.topic_source, load_key(a.env))
    write_atomic(profile, a.out)
    reqs = profile["requirements"]
    unverified = [r["id"] for r in reqs if r.get("posting_line_verified") is False]
    print(f"{profile['role']}: {len(reqs)} requirements, "
          f"{sum(len(r['sample_questions']) for r in reqs)} questions, "
          f"unverified posting lines: {unverified or 'none'}")


if __name__ == "__main__":
    main()
