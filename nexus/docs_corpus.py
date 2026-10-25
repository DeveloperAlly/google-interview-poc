"""Build the work-docs evidence store (ds-docs-lite) from Drive and Notion documents extracted as text.

Input:  <state>/docs/raw/<id>.txt  (line 1 "TITLE: ...", blank line, then text)
        <state>/docs/raw/manifest.json  (Drive extraction manifest: fileId, title, group, skipped_reason)
        <state>/docs/raw/notion-*.txt  (Notion exports; group "notion")
Output: <state>/docs/corpus/ds-docs-lite/<id>.html and <state>/docs/metadata/ds-docs-lite/docs.jsonl,
        the shape ingest_inline.py expects.

These are her own work documents (Lilypad Network, Livepeer, speaking log), so they are evidence, not reference.
Include rule and the excluded categories are documented in docs/06; the list itself is the manifest.
"""
from __future__ import annotations
import argparse, hashlib, html, json, re
from pathlib import Path

ERA = {"lilypad": "Lilypad Network (Founder & CEO, Sep 2023 to Oct 2025)",
       "livepeer": "Livepeer",
       "notion": "Speaking and developer relations log"}


def doc_id(key: str) -> str:
    return "wd-" + hashlib.sha1(key.encode()).hexdigest()[:32]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", required=True)
    a = ap.parse_args()
    st = Path(a.state)
    raw = st / "docs" / "raw"
    man = {m["fileId"]: m for m in json.loads((raw / "manifest.json").read_text())} if (raw / "manifest.json").exists() else {}
    corpus = st / "docs" / "corpus" / "ds-docs-lite"; corpus.mkdir(parents=True, exist_ok=True)
    meta = st / "docs" / "metadata" / "ds-docs-lite"; meta.mkdir(parents=True, exist_ok=True)
    rows, skipped = [], []
    for p in sorted(raw.glob("*.txt")):
        t = p.read_text(encoding="utf-8", errors="replace")
        first, _, body = t.partition("\n")
        title = first.removeprefix("TITLE:").strip() or p.stem
        body = re.sub(r"\n{3,}", "\n\n", body).strip()
        if p.stem.startswith("notion-"):
            group, url, fid = "notion", "", p.stem
        else:
            m = man.get(p.stem)
            if not m or m.get("skipped_reason"):
                skipped.append(p.name); continue
            group, fid = m.get("group", "lilypad"), p.stem
            url = f"https://drive.google.com/open?id={fid}"
        if len(body) < 200:
            skipped.append(f"{p.name} (under 200 chars)"); continue
        did = doc_id(fid)
        sd = {"source": "work-docs", "store": "work-docs", "owner": "DeveloperAlly", "repo": group, "path": title,
              "title": title, "kind": "doc", "era": ERA.get(group, ""), "visibility": "evidence",
              "html_url": url, "language": "en"}
        page = (f"<!doctype html><html><head><meta charset='utf-8'><title>{html.escape(title)}</title></head><body>"
                f"<h1>{html.escape(title)}</h1><ul><li>source: her own work document ({html.escape(group)})</li>"
                f"<li>era: {html.escape(sd['era'])}</li></ul><pre>{html.escape(body)}</pre></body></html>")
        (corpus / f"{did}.html").write_text(page, encoding="utf-8")
        rows.append({"id": did, "structData": sd,
                     "content": {"mimeType": "text/html", "uri": f"gs://unused/corpus/ds-docs-lite/{did}.html"}})
    (meta / "docs.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n")
    rep = {"docs": len(rows), "by_group": {g: sum(r["structData"]["repo"] == g for r in rows) for g in ERA},
           "bytes": sum((corpus / f"{r['id']}.html").stat().st_size for r in rows), "skipped": skipped}
    (st / "docs" / "build-report.json").write_text(json.dumps(rep, indent=1))
    print(json.dumps(rep))


if __name__ == "__main__":
    main()
