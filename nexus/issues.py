"""Harvest issues (with comment threads) and the owner's contributions to repos they do not own.

1. Every issue in every non-fork owned repo, including repos with no code (issue-only planning repos),
   except repos the owner excluded at G1. Pull requests are skipped here; prs.py covers owned PRs.
2. Every issue and PR the owner authored in other people's repos (GitHub search), with comments, and for
   PRs the changed paths. This is where work on other organisations' projects lives.

Writes HTML documents + JSONL to <state> under ds-prs (the work-item store). Logs counts and hashed ids only.
"""
import argparse, json, sys
from pathlib import Path
from harvest import doc_id, write_doc
from prs import GH


def thread(gh, url, n):
    if not n:
        return ""
    out = []
    for c in gh.pages(url.replace("https://api.github.com/", "")):
        out.append(f"### {c['user']['login']} ({c['created_at'][:10]})\n\n{c.get('body') or ''}\n")
    return "\n## Comments\n\n" + "\n".join(out)


def doc_for(gh, it, key, visibility, external):
    is_pr = "pull_request" in it
    kind = ("pr-external" if is_pr else "issue-external") if external else "issue"
    files = ""
    if is_pr:
        fr = gh.get(f"repos/{key}/pulls/{it['number']}/files", per_page=100)
        if fr.status_code not in (200, 404):
            sys.exit(f"FAIL: GitHub HTTP {fr.status_code} reading PR files; refusing to write a PR with no files")
        if fr.status_code == 200:
            files = "\n## Changed paths\n\n" + "\n".join(f"- `{f['filename']}`" for f in fr.json()) + "\n"
    labels = ", ".join(l["name"] for l in it.get("labels", []))
    merged = (it.get("pull_request") or {}).get("merged_at")
    body = (f"# {key} {'PR' if is_pr else 'Issue'} #{it['number']}: {it['title']}\n\n- repo: {key}\n"
            f"- author: {it['user']['login']}\n- state: {it['state']}{' (merged)' if merged else ''}\n"
            f"- created: {it['created_at']}\n- closed: {it.get('closed_at') or ''}\n- labels: {labels}\n"
            f"- comments: {it['comments']}\n- url: {it['html_url']}\n\n## Description\n\n{it.get('body') or '(no description)'}\n"
            + thread(gh, it["comments_url"], it["comments"]) + files)
    owner, name = key.split("/")
    struct = {"source": "github", "owner": owner, "repo": name, "path": "", "kind": kind, "language": "",
              "visibility": visibility, "commit_sha": "", "html_url": it["html_url"], "updated_at": it["updated_at"],
              "pr_number": it["number"] if is_pr else None}
    return doc_id("is" if not is_pr else "pr", f"github://{key}/{'pull' if is_pr else 'issues'}/{it['number']}"), body, struct


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", required=True)
    ap.add_argument("--author", required=True, help="GitHub login whose external contributions to collect")
    a = ap.parse_args()
    state = Path(a.state)
    rows = json.load(open(state / "manifest/repos.json"))
    owners = {r["owner"] for r in rows}
    repos = [r for r in rows if not r["reason"].startswith("G1 owner exclusion")
             and (not r["fork"] or r["reason"].startswith("G1 owner inclusion"))]
    ds = "ds-prs"
    (state / f"corpus/{ds}").mkdir(parents=True, exist_ok=True)
    (state / f"metadata/{ds}").mkdir(parents=True, exist_ok=True)
    gh, ids, counts = GH(), set(), {"owned_issues": 0, "external_issues": 0, "external_prs": 0, "repos_with_issues": 0}
    with open(state / f"metadata/{ds}/docs.jsonl", "w") as out:
        for i, r in enumerate(repos, 1):
            key, n = f"{r['owner']}/{r['name']}", 0
            for it in gh.pages(f"repos/{key}/issues", state="all"):
                if "pull_request" in it:
                    continue
                did, body, struct = doc_for(gh, it, key, r["visibility"], external=False)
                if did in ids:
                    continue
                write_doc(state, ds, did, body, struct, "text/html", "html", "unused", out)
                ids.add(did); n += 1
            counts["owned_issues"] += n
            counts["repos_with_issues"] += bool(n)
            print(f"[{i}/{len(repos)}] {doc_id('rp', f'github://{key}')} issues={n}", flush=True)
        seen_ext, vis_cache = 0, {}
        for kind in ("is:issue", "is:pr"):
            q = f"author:{a.author} " + " ".join(f"-user:{o}" for o in sorted(owners)) + f" {kind}"
            head = gh.get("search/issues", q=q, per_page=1).json()
            if head.get("incomplete_results") or head.get("total_count", 0) > 1000:
                sys.exit(f"FAIL: search for {kind} is incomplete or over the 1,000-result cap; split the query")
            for it in gh.pages("search/issues", q=q):
                seen_ext += 1
                key = "/".join(it["repository_url"].split("/")[-2:])
                if key not in vis_cache:  # real visibility: other people's repos can be private or internal too
                    rr = gh.get(f"repos/{key}")
                    vis_cache[key] = rr.json().get("visibility", "private") if rr.status_code == 200 else "private"
                did, body, struct = doc_for(gh, it, key, vis_cache[key], external=True)
                if did in ids:
                    continue
                write_doc(state, ds, did, body, struct, "text/html", "html", "unused", out)
                ids.add(did)
                counts["external_prs" if "pull_request" in it else "external_issues"] += 1
        print(f"external search results={seen_ext}", flush=True)
    counts["docs"] = len(ids)
    (state / "reports").mkdir(exist_ok=True)
    json.dump(counts, open(state / "reports/issues.json", "w"), indent=1)
    print(counts)


if __name__ == "__main__":
    main()
