"""Turn the owner's role map into citable documents, one per role, so answers retrieve "her role at X" with the code.

Input  <state>/profile/role-map.md: one "- Organisation, Title, dates: facts" line per role (gitignored, owner-written)
Output <state>/profile-docs as a harvest-shaped state dir (corpus, scan copy, docs.jsonl) for ingest_inline.py.
Kind is "profile" and visibility is "public": these are the owner's own CV facts, safe for the demo scope.
"""
import argparse, re
from pathlib import Path
from harvest import doc_id, write_doc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", required=True)
    ap.add_argument("--person", default="Ally Haire")
    ap.add_argument("--owner", default="DeveloperAlly")
    a = ap.parse_args()
    state = Path(a.state)
    src = (state / "profile" / "role-map.md").read_text(encoding="utf-8")
    out_dir = state / "profile-docs"
    (out_dir / "corpus/ds-code").mkdir(parents=True, exist_ok=True)
    (out_dir / "metadata/ds-code").mkdir(parents=True, exist_ok=True)
    n = 0
    with open(out_dir / "metadata/ds-code/docs.jsonl", "w") as out:
        for line in src.splitlines():
            m = re.match(r"^- ([^,]+(?:/[^,]+)?),\s*(.+)$", line.strip())
            if not m:
                continue
            org, rest = m.group(1).strip(), m.group(2).strip()
            body = (f"# {a.person}'s role at {org}\n\n- person: {a.person}\n- organisation: {org}\n- kind: career profile\n\n"
                    f"## Role\n\n{a.person} at {org}: {rest}\n")
            did = doc_id("pf", f"profile://{a.owner}/{org}")
            write_doc(out_dir, "ds-code", did, body, {"source": "profile", "owner": a.owner, "repo": "profile",
                      "path": org, "kind": "profile", "language": "", "visibility": "public", "commit_sha": "",
                      "html_url": "", "updated_at": "", "pr_number": None}, "text/html", "html", "unused", out)
            n += 1
    print(f"profile docs={n}")


if __name__ == "__main__":
    main()
