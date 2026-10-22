"""Build the repo manifest from the GitHub API for each owner. Read-only.

Rules: empty repos (size 0) and forks are excluded. Owner exclusions from gate G1 come from
<state>/exclusions.json ({"owner/name": "reason category"}), which lives in gitignored state so private
repo names never reach this public repo. Prints counts only.
"""
import argparse, collections, json, sys
from pathlib import Path
from prs import GH


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", required=True)
    ap.add_argument("--owners", required=True, help="comma list; the authenticated user is listed via /user/repos")
    a = ap.parse_args()
    state = Path(a.state)
    gh = GH()
    me = gh.get("user").json()["login"]
    rows = []
    for owner in a.owners.split(","):
        src = (gh.pages("user/repos", affiliation="owner") if owner == me
               else gh.pages(f"orgs/{owner}/repos", type="all"))
        for r in src:
            rows.append({"owner": r["owner"]["login"], "name": r["name"], "visibility": r["visibility"], "fork": r["fork"],
                         "archived": r["archived"], "size": r["size"], "default_branch": r["default_branch"],
                         "pushed_at": r["pushed_at"], "language": r["language"], "description": r["description"],
                         "html_url": r["html_url"]})
    ex_path = state / "exclusions.json"
    exclusions = json.load(open(ex_path)) if ex_path.exists() else {}
    for r in rows:
        key = f"{r['owner']}/{r['name']}"
        reason = ("empty repo (size 0)" if r["size"] == 0 else
                  "fork: upstream code, not owner work" if r["fork"] else
                  f"G1 owner exclusion: {exclusions[key]}" if key in exclusions else None)
        r["include"], r["reason"] = reason is None, reason or "owner repo"
    (state / "manifest").mkdir(parents=True, exist_ok=True)
    json.dump(rows, open(state / "manifest/repos.json", "w"), indent=1)
    c = collections.Counter((r["owner"], r["visibility"], r["include"]) for r in rows)
    for k, v in sorted(c.items()):
        print(v, *k)
    unmatched = set(exclusions) - {f"{r['owner']}/{r['name']}" for r in rows}
    print(f"total={len(rows)} included={sum(r['include'] for r in rows)} exclusions_unmatched={len(unmatched)}")
    if unmatched:
        sys.exit("FAIL: exclusions name repos that do not exist")


if __name__ == "__main__":
    main()
