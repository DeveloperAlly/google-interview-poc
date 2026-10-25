"""Build the Google reference corpus (second RAG store) from the owner's "How Google Sees Things" folder.

    python google_corpus.py --src "<folder>" --state <repo>/state/google

Writes <state>/corpus/ds-google-lite/<id>.html and <state>/metadata/ds-google-lite/docs.jsonl in the same shape
ingest_inline.py imports. Zero-cost path: text is extracted locally and imported as HTML (digital parser, no
layout parsing, no Cloud Storage).

Reference only: this corpus describes Google's products, positioning and customers. It is never evidence of the
owner's own work (structData.store = "google-reference").

Kinds:
  talk        full speaker-labelled transcript, cleaned (walk-on music and sub-4-word fragments removed)
  summary     the AI-written summary/notes for a talk, linked to its transcript by pair_id
  case_study  Google Cloud customer case study (PDF text)
Audio (.mp3) is not indexed; talks with audio but no transcript are reported as gaps.
"""
from __future__ import annotations
import argparse, hashlib, html, json, re
from pathlib import Path

TURN = re.compile(r"^\*\*(Speaker \d+|[^*]{1,60})\*\*\s*\*\[(\d{1,2}:\d{2}(?::\d{2})?)\]\*:\s*(.*)$")


def norm_title(t: str) -> str:
    t = re.sub(r"\.mp3.*$", "", t, flags=re.I)
    t = re.sub(r"-mp3-[0-9a-f]{8}-[0-9a-f]{4}$", "", t)
    return re.sub(r"[^a-z0-9]+", " ", t.lower()).strip()


def doc_id(rel: str) -> str:
    return "gg-" + hashlib.sha1(rel.encode()).hexdigest()[:32]


def clean_transcript(text: str) -> tuple[str, int, int]:
    """Keep speaker turns; drop the walk-on segment (everything before the first turn of 20+ words) and fragments."""
    lines, kept, dropped, started = text.splitlines(), [], 0, False
    for ln in lines:
        m = TURN.match(ln.strip())
        if not m:
            continue
        spk, ts, said = m.groups()
        words = len(said.split())
        if not started and words < 20:
            dropped += 1
            continue
        started = True
        if words < 4:
            dropped += 1
            continue
        kept.append(f"[{ts}] {spk}: {said}")
    return "\n".join(kept), len(kept), dropped


def pdf_text(p: Path) -> str:
    from pypdf import PdfReader
    r = PdfReader(str(p))
    return "\n".join((pg.extract_text() or "") for pg in r.pages)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--state", required=True)
    a = ap.parse_args()
    src, st = Path(a.src), Path(a.state)
    corpus, meta = st / "corpus" / "ds-google-lite", st / "metadata" / "ds-google-lite"
    corpus.mkdir(parents=True, exist_ok=True); meta.mkdir(parents=True, exist_ok=True)
    rows, report = [], {"talk": 0, "summary": 0, "case_study": 0, "skipped": [], "audio_only": [], "dropped_lines": 0}
    titles = {}  # norm title -> {"talk": id, "summary": id}
    items = []
    for p in sorted(src.rglob("*")):
        if not p.is_file() or p.name == ".DS_Store" or p.suffix.lower() == ".mp3":
            continue
        rel = str(p.relative_to(src))
        parts = rel.split("/")
        event = "Google Cloud Next '26" if parts[0].startswith("Google Next 26") else "Google (other)"
        category = parts[1] if event.startswith("Google Cloud Next") and len(parts) > 2 else parts[0] if len(parts) > 1 else ""
        if p.suffix.lower() == ".md":
            raw = p.read_text(encoding="utf-8", errors="replace")
            head = next((l[2:].strip() for l in raw.splitlines() if l.startswith("# ")), p.stem)
            if "**Speaker" in raw or TURN.search(raw):
                body, n, dropped = clean_transcript(raw)
                kind = "talk"; report["dropped_lines"] += dropped
                if n == 0:
                    report["skipped"].append(rel); continue
            else:
                body, kind = raw, "summary"
        elif p.suffix.lower() == ".pdf":
            head = re.sub(r"\s*_\s*Google Cloud$", "", p.stem).strip()
            body, kind = pdf_text(p), "case_study"
            if len(body.split()) < 50:
                report["skipped"].append(rel + " (no extractable text)"); continue
        else:
            report["skipped"].append(rel); continue
        title = re.sub(r"\.mp3$", "", head, flags=re.I).strip()
        did = doc_id(rel)
        items.append((did, rel, kind, title, event, category, body))
        if kind in ("talk", "summary"):
            titles.setdefault(norm_title(title), {})[kind] = did
    for did, rel, kind, title, event, category, body in items:
        pair = titles.get(norm_title(title), {})
        other = pair.get("summary" if kind == "talk" else "talk", "") if kind != "case_study" else ""
        sd = {"source": "google-reference", "store": "google-reference", "owner": "Google", "repo": category or event,
              "path": rel, "title": title, "kind": kind, "event": event, "category": category, "pair_id": other,
              "visibility": "reference", "html_url": "", "language": "en"}
        page = (f"<!doctype html><html><head><meta charset='utf-8'><title>{html.escape(title)}</title></head><body>"
                f"<h1>{html.escape(title)}</h1><ul><li>source: Google reference material (not the owner's work)</li>"
                f"<li>event: {html.escape(event)}</li><li>category: {html.escape(category)}</li><li>kind: {kind}</li>"
                f"<li>file: {html.escape(rel)}</li></ul><pre>{html.escape(body)}</pre></body></html>")
        (corpus / f"{did}.html").write_text(page, encoding="utf-8")
        rows.append({"id": did, "structData": sd,
                     "content": {"mimeType": "text/html", "uri": f"gs://unused/corpus/ds-google-lite/{did}.html"}})
        report[kind] += 1
    # audio with no transcript
    for mp3 in src.rglob("*.mp3"):
        t = norm_title(mp3.stem)
        if "talk" not in titles.get(t, {}):
            report["audio_only"].append(str(mp3.relative_to(src)))
    (meta / "docs.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n")
    report["docs"] = len(rows)
    report["unpaired"] = sorted(t for t, v in titles.items() if len(v) == 1)
    (st / "build-report.json").write_text(json.dumps(report, indent=1))
    print(json.dumps({k: (v if not isinstance(v, list) else len(v)) for k, v in report.items()}))
    print("audio_only:", sorted(set(report["audio_only"])))
    print("skipped:", report["skipped"])


if __name__ == "__main__":
    main()
