"""Harvest commit history: one document per repo per month, listing every commit message with author and date.

Shallow clones only hold the latest commit, so history comes from the GitHub API (default branch).
Monthly grouping keeps the document count proportional to activity, not to commit count, and each
document reads as "what happened in this repo that month, and who did it".
"""
import argparse, collections, json
from pathlib import Path
from harvest import doc_id, write_doc
from prs import GH


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", required=True)
    a = ap.parse_args()
    state = Path(a.state)
    repos = [r for r in json.load(open(state / "manifest/repos.json")) if r["include"]]
    ds = "ds-prs"
    (state / f"corpus/{ds}").mkdir(parents=True, exist_ok=True)
    (state / f"metadata/{ds}").mkdir(parents=True, exist_ok=True)
    gh, docs, commits = GH(), 0, 0
    with open(state / f"metadata/{ds}/docs.jsonl", "w") as out:
        for i, r in enumerate(repos, 1):
            key = f"{r['owner']}/{r['name']}"
            months = collections.defaultdict(list)
            for c in gh.pages(f"repos/{key}/commits", sha=r["default_branch"]):
                who = (c.get("author") or {}).get("login") or c["commit"]["author"]["name"]
                when = c["commit"]["author"]["date"]
                months[when[:7]].append(f"- {when[:10]} **{who}** [{c['sha'][:7]}]({c['html_url']}): "
                                        + c["commit"]["message"].strip().replace("\n", "\n  "))
            for month, lines in sorted(months.items()):
                authors = collections.Counter(l.split("**")[1] for l in lines)
                body = (f"# {key} commit history {month}\n\n- repo: {key}\n- month: {month}\n- commits: {len(lines)}\n"
                        f"- authors: {', '.join(f'{k} ({v})' for k, v in authors.most_common())}\n\n## Commits\n\n"
                        + "\n".join(reversed(lines)) + "\n")
                did = doc_id("cm", f"github://{key}/commits/{month}")
                write_doc(state, ds, did, body, {"source": "github", "owner": r["owner"], "repo": r["name"], "path": "",
                          "kind": "commits", "language": "", "visibility": r["visibility"], "commit_sha": "",
                          "html_url": f"{r['html_url']}/commits/{r['default_branch']}", "updated_at": f"{month}-01T00:00:00Z",
                          "pr_number": None}, "text/html", "html", "unused", out)
                docs += 1
                commits += len(lines)
            print(f"[{i}/{len(repos)}] {doc_id('rp', f'github://{key}')} months={len(months)}", flush=True)
    (state / "reports").mkdir(exist_ok=True)
    json.dump({"docs": docs, "commits": commits, "repos": len(repos)}, open(state / "reports/commits.json", "w"), indent=1)
    print(f"commit-history docs={docs} commits={commits} repos={len(repos)}")


if __name__ == "__main__":
    main()
