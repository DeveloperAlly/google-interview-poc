"""Harvest included repos into HTML documents plus Agent Search JSONL metadata.

Reads  <state>/manifest/repos.json   (built by manifest.py)
Writes <state>/corpus/<ds>/<id>.html (plus an unescaped .md copy under scan/ for the secret scanner), <state>/metadata/<ds>/docs.jsonl, <state>/reports/harvest.json

Logs counts and hashed IDs only: repo names and paths from private repos never reach stdout.
"""
from __future__ import annotations

import argparse, hashlib, html, json, os, re, subprocess, sys
from pathlib import Path

import markdown

# Content goes up as text/html: Document.Content does not list text/markdown, and only HTML (not TXT or
# Markdown) reaches the layout parser that layout-based chunking requires.
MD = markdown.Markdown(extensions=["fenced_code", "tables"])


def to_html(md_text: str, title: str) -> str:
    MD.reset()
    return (f"<!doctype html><html><head><meta charset=\"utf-8\"><title>{html.escape(title)}</title></head>"
            f"<body>{MD.convert(md_text)}</body></html>")

MAX_BYTES = 200 * 1024  # quality threshold: larger files are data dumps or generated, not authored code
VENDORED = re.compile(r"(^|/)(node_modules|vendor|dist|build|out|\.next|coverage|__pycache__|\.venv|venv|target|\.git)/")
LOCKFILES = {"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock", "Cargo.lock", "go.sum",
             "Gemfile.lock", "composer.lock", "Pipfile.lock", "bun.lockb", "uv.lock"}
GENERATED = re.compile(r"(\.min\.(js|css)|\.map|\.pb\.go|_pb2\.py|\.generated\.\w+|\.snap)$")
SECRET_NAMES = re.compile(r"(^|/)(\.env[^/]*|id_rsa[^/]*|[^/]*\.(pem|key|p12|pfx|keystore)|[^/]*(credential|secret|service[-_]?account)[^/]*\.json)$", re.I)
BINARY_EXT = {"png", "jpg", "jpeg", "gif", "webp", "ico", "bmp", "tiff", "svg", "psd", "mp4", "mov", "webm", "mp3",
              "wav", "ogg", "flac", "pdf", "zip", "gz", "tgz", "tar", "rar", "7z", "jar", "war", "class", "so",
              "dylib", "dll", "exe", "bin", "wasm", "woff", "woff2", "ttf", "otf", "eot", "pyc", "db", "sqlite",
              "parquet", "pkl", "pt", "onnx", "safetensors", "h5", "ckpt", "glb", "gltf", "fbx", "obj", "stl",
              "docx", "pptx", "xlsx", "key", "numbers", "pages", "sketch", "fig", "car"}
DOC_EXT = {"md", "mdx", "rst", "txt", "adoc"}
LANG = {"py": "python", "ts": "typescript", "tsx": "tsx", "js": "javascript", "jsx": "jsx", "go": "go", "rs": "rust",
        "sol": "solidity", "java": "java", "kt": "kotlin", "swift": "swift", "rb": "ruby", "sh": "bash",
        "yml": "yaml", "yaml": "yaml", "toml": "toml", "json": "json", "md": "markdown", "mdx": "mdx",
        "html": "html", "css": "css", "scss": "scss", "sql": "sql", "dart": "dart", "c": "c", "cpp": "cpp",
        "h": "c", "ino": "cpp", "vue": "vue", "svelte": "svelte", "tf": "hcl", "dockerfile": "dockerfile"}


def doc_id(prefix: str, canonical: str) -> str:
    return f"{prefix}-{hashlib.sha256(canonical.encode()).hexdigest()[:32]}"


def eligible(path: str, size: int) -> str | None:
    """Return an exclusion reason, or None if the file is eligible."""
    name = path.rsplit("/", 1)[-1]
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if SECRET_NAMES.search(path): return "secret-pattern"
    if VENDORED.search(path): return "vendored"
    if name in LOCKFILES: return "lockfile"
    if GENERATED.search(name): return "generated"
    if ext in BINARY_EXT: return "binary-ext"
    if size > MAX_BYTES: return "too-large"
    if size == 0: return "empty"
    return None


def fence_for(text: str) -> str:
    longest = max((len(m) for m in re.findall(r"`{3,}", text)), default=2)
    return "`" * max(3, longest + 1)


def git(args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout


def clone(repo, cache: Path) -> Path:
    dest = cache / repo["owner"] / repo["name"]
    if (dest / ".git").exists():  # refresh, so an incremental run never re-indexes a stale commit
        git(["fetch", "--depth=1", "--quiet", "origin", repo["default_branch"]], dest)
        git(["reset", "--hard", "--quiet", "FETCH_HEAD"], dest)
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    url = f"https://github.com/{repo['owner']}/{repo['name']}.git"
    subprocess.run(["gh", "repo", "clone", f"{repo['owner']}/{repo['name']}", str(dest), "--", "--depth=1", "--quiet"],
                   check=True, capture_output=True)
    return dest


def write_doc(state: Path, ds: str, did: str, body: str, struct: dict, mime: str, ext: str, bucket: str, out):
    rel = f"corpus/{ds}/{did}.{ext}"
    title = body.split("\n", 1)[0].lstrip("# ")
    (state / rel).write_text(to_html(body, title) if mime == "text/html" else body, encoding="utf-8")
    # Unescaped copy for the secret scanner: HTML entities hide tokens from gitleaks (47 findings raw vs 15 as HTML).
    (state / f"scan/{ds}").mkdir(parents=True, exist_ok=True)
    (state / f"scan/{ds}/{did}.md").write_text(body, encoding="utf-8")
    out.write(json.dumps({"id": did, "structData": struct,
                          "content": {"mimeType": mime, "uri": f"gs://{bucket}/{rel}"}}) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", required=True)
    ap.add_argument("--cache", required=True, help="clone cache dir, outside the repo")
    ap.add_argument("--bucket", required=True)
    ap.add_argument("--mime", default="text/html")
    ap.add_argument("--ext", default="html")
    ap.add_argument("--only", default="", help="comma list owner/name to restrict to (pilot)")
    ap.add_argument("--path-exclusions", default="", help="JSON file {owner/name: [regex, ...]} kept in gitignored state")
    a = ap.parse_args()
    state, cache = Path(a.state), Path(a.cache)
    path_ex = {k: [re.compile(p) for p in v] for k, v in json.load(open(a.path_exclusions)).items()} if a.path_exclusions else {}
    repos = [r for r in json.load(open(state / "manifest/repos.json")) if r["include"]]
    if a.only:
        want = set(a.only.split(","))
        repos = [r for r in repos if f"{r['owner']}/{r['name']}" in want]
    ds = "ds-code"
    (state / f"corpus/{ds}").mkdir(parents=True, exist_ok=True)
    (state / f"metadata/{ds}").mkdir(parents=True, exist_ok=True)
    report = {"repos": {}, "excluded_reasons": {}, "docs": 0, "ids": set()}
    with open(state / f"metadata/{ds}/docs.jsonl", "w") as out:
        for i, r in enumerate(repos, 1):
            key = f"{r['owner']}/{r['name']}"
            rkey = doc_id("rp", f"github://{key}")
            try:
                path = clone(r, cache)
                sha = git(["rev-parse", "HEAD"], path).strip()
            except subprocess.CalledProcessError:
                report["repos"][key] = {"files": 0, "reason": "clone-failed"}
                print(f"[{i}/{len(repos)}] {rkey} clone-failed", flush=True)
                continue
            files = [f for f in git(["ls-files", "-z"], path).split("\0") if f]  # tracked only, so .gitignore holds
            base = {"source": "github", "owner": r["owner"], "repo": r["name"], "visibility": r["visibility"],
                    "commit_sha": sha, "updated_at": r["pushed_at"], "pr_number": None}
            n, readme = 0, ""
            for f in files:
                fp = path / f
                if not fp.is_file() or fp.is_symlink():
                    continue
                why = ("owner-path-exclusion" if any(p.search(f) for p in path_ex.get(key, []))
                       else eligible(f, fp.stat().st_size))
                raw = fp.read_bytes() if why is None else b""
                if why is None and b"\0" in raw[:8192]: why = "binary-content"
                if why is None:
                    try: text = raw.decode("utf-8")
                    except UnicodeDecodeError: why = "not-utf8"
                if why:
                    report["excluded_reasons"][why] = report["excluded_reasons"].get(why, 0) + 1
                    continue
                ext = f.rsplit(".", 1)[-1].lower() if "." in f.rsplit("/", 1)[-1] else f.rsplit("/", 1)[-1].lower()
                lname = f.rsplit("/", 1)[-1].lower()
                kind = ("readme" if lname.startswith("readme") else
                        "adr" if re.search(r"(^|/)(adr|decisions?)/", f, re.I) else
                        "doc" if ext in DOC_EXT else "code")
                if kind == "readme" and "/" not in f and not readme: readme = text[:4000]
                url = f"{r['html_url']}/blob/{sha}/{f}"
                did = doc_id("gh", f"github://{key}/{f}")
                fence = fence_for(text)
                body = (f"# {key}/{f}\n\n- repo: {key}\n- path: {f}\n- language: {LANG.get(ext, ext or 'text')}\n"
                        f"- commit: {sha}\n- permalink: {url}\n- last_pushed: {r['pushed_at']}\n\n"
                        + (text if kind in ("readme", "doc", "adr") and ext in ("md", "mdx")
                           else f"{fence}{LANG.get(ext, '')}\n{text}\n{fence}\n"))
                write_doc(state, ds, did, body, {**base, "path": f, "kind": kind, "language": LANG.get(ext, ext),
                          "html_url": url}, a.mime, a.ext, a.bucket, out)
                report["ids"].add(did); n += 1
            top = sorted({f.split("/", 1)[0] + ("/" if "/" in f else "") for f in files})[:80]
            body = (f"# Repository {key}\n\n- description: {r.get('description') or ''}\n- visibility: {r['visibility']}\n"
                    f"- primary language: {r.get('language') or ''}\n- default branch: {r['default_branch']}\n"
                    f"- last pushed: {r['pushed_at']}\n- url: {r['html_url']}\n- eligible files: {n}\n\n"
                    f"## Top-level tree\n\n" + "\n".join(f"- {t}" for t in top) + f"\n\n## README excerpt\n\n{readme}\n")
            write_doc(state, ds, rkey, body, {**base, "path": "", "kind": "repo", "language": r.get("language") or "",
                      "html_url": r["html_url"]}, a.mime, a.ext, a.bucket, out)
            report["ids"].add(rkey)
            report["repos"][key] = {"files": n, "id": rkey, "reason": None if n else "no-eligible-files"}
            report["docs"] += n + 1
            print(f"[{i}/{len(repos)}] {rkey} files={n}", flush=True)
    report["ids"] = len(report["ids"])
    (state / "reports").mkdir(exist_ok=True)
    json.dump(report, open(state / "reports/harvest.json", "w"), indent=1)
    print(f"repos={len(repos)} docs={report['docs']} unique_ids={report['ids']} excluded={report['excluded_reasons']}")
    if report["ids"] != report["docs"]:
        sys.exit("FAIL: duplicate document ids")
    failed = [k for k, v in report["repos"].items() if v["reason"] == "clone-failed"]
    if failed:
        sys.exit(f"FAIL: {len(failed)} repo(s) failed to clone; see reports/harvest.json")


if __name__ == "__main__":
    main()
