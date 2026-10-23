"""C1: pull the owner's project Drive folder, extract text from .docx/.pptx, and write harvest-shaped narrative docs.

Output <state>/drive-docs (corpus, scan copy, docs.jsonl) for ingest_inline.py. Kind is "narrative", source "drive".
"""
import argparse, html, re, subprocess, sys, zipfile
from pathlib import Path
from harvest import doc_id, write_doc


def text_of(p: Path) -> str:
    z = zipfile.ZipFile(p)
    if p.suffix == ".docx":
        x = z.read("word/document.xml").decode("utf-8")
        paras = re.findall(r"<w:p[ >].*?</w:p>", x, re.S)
        return "\n\n".join(t for t in ("".join(html.unescape(s) for s in re.findall(r"<w:t[^>]*>(.*?)</w:t>", q)) for q in paras) if t.strip())
    out = []
    slides = sorted((n for n in z.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", n)), key=lambda n: int(re.findall(r"\d+", n)[0]))
    for n in slides:
        num = re.findall(r"\d+", n)[0]
        x = z.read(n).decode("utf-8")
        lines = ["".join(html.unescape(t) for t in re.findall(r"<a:t>(.*?)</a:t>", q)) for q in re.findall(r"<a:p>(.*?)</a:p>", x, re.S)]
        out.append(f"## Slide {num}\n\n" + "\n".join(l for l in lines if l.strip()))
        notes = f"ppt/notesSlides/notesSlide{num}.xml"
        if notes in z.namelist():
            nt = " ".join(html.unescape(t) for t in re.findall(r"<a:t>(.*?)</a:t>", z.read(notes).decode("utf-8")))
            if nt.strip():
                out.append("Speaker notes: " + nt.strip())
    return "\n\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", required=True)
    ap.add_argument("--folder", required=True, help="Drive folder id")
    ap.add_argument("--remote", default="gdrive:")
    a = ap.parse_args()
    state = Path(a.state)
    raw = state / "drive"
    raw.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["rclone", "copy", "--drive-root-folder-id", a.folder, a.remote, str(raw)], capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"FAIL rclone: {r.stderr[-300:]}")
    out_dir = state / "drive-docs"
    (out_dir / "corpus/ds-code").mkdir(parents=True, exist_ok=True)
    (out_dir / "metadata/ds-code").mkdir(parents=True, exist_ok=True)
    n = 0
    with open(out_dir / "metadata/ds-code/docs.jsonl", "w") as out:
        for p in sorted(raw.glob("*")):
            if p.suffix not in (".docx", ".pptx"):
                continue
            body = f"# {p.stem}\n\n- source: owner's project Drive folder\n- file: {p.name}\n\n" + text_of(p)
            did = doc_id("dr", f"drive://{a.folder}/{p.name}")
            write_doc(out_dir, "ds-code", did, body, {"source": "drive", "owner": "DeveloperAlly", "repo": "drive", "path": p.name,
                      "kind": "narrative", "language": "", "visibility": "public", "commit_sha": "",
                      "html_url": f"https://drive.google.com/drive/folders/{a.folder}", "updated_at": "", "pr_number": None},
                      "text/html", "html", "unused", out)
            n += 1
            print(f"{did} chars={len(body)}", flush=True)
    print(f"drive docs={n}")


if __name__ == "__main__":
    main()
