"""Harvest merged pull requests for every included repo into HTML documents plus JSONL metadata (ds-prs).

One document per merged PR: title, body, author, merged_at, base branch, changed-file count and paths.
Uses the gh CLI token. Backs off on 403/429 rate limits. Logs counts and hashed ids only.
"""
import argparse, json, subprocess, sys, time
from pathlib import Path
import requests
from harvest import doc_id, write_doc

API = "https://api.github.com"


class GH:
    def __init__(self):
        tok = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, check=True).stdout.strip()
        self.s = requests.Session()
        self.s.headers.update({"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json",
                               "X-GitHub-Api-Version": "2022-11-28"})

    def get(self, url, **params):
        for attempt in range(8):
            try:
                r = self.s.get(url if url.startswith("http") else f"{API}/{url}", params=params, timeout=60)
            except (requests.ConnectionError, requests.Timeout, requests.exceptions.ChunkedEncodingError):
                time.sleep(min(120, 5 * 2 ** attempt))  # transient network failure: back off and retry
                continue
            if r.status_code in (403, 429) and ("rate limit" in r.text.lower() or r.status_code == 429):
                reset = int(r.headers.get("x-ratelimit-reset", time.time() + 60))
                wait = max(5, min(900, reset - time.time() + 2))
                print(f"rate limited, sleeping {wait:.0f}s", flush=True)
                time.sleep(wait)
                continue
            return r
        sys.exit("FAIL: GitHub request did not succeed after 8 attempts (rate limit or network)")

    def pages(self, path, **params):
        url, params, first = f"{API}/{path}", {"per_page": 100, **params}, True
        while url:
            r = self.get(url, **params)
            if first and r.status_code in (404, 409, 410):
                return  # first page only: repo gone (404), git repo empty (409), issues disabled (410)
            first = False
            if r.status_code != 200:
                sys.exit(f"FAIL: GitHub HTTP {r.status_code} while paging; refusing a partial list")
            j = r.json()
            yield from (j["items"] if isinstance(j, dict) and "items" in j else j)  # search API wraps results
            url, params = r.links.get("next", {}).get("url"), {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", required=True)
    ap.add_argument("--bucket", required=True)
    a = ap.parse_args()
    state = Path(a.state)
    repos = [r for r in json.load(open(state / "manifest/repos.json")) if r["include"]]
    ds = "ds-prs"
    (state / f"corpus/{ds}").mkdir(parents=True, exist_ok=True)
    (state / f"metadata/{ds}").mkdir(parents=True, exist_ok=True)
    gh, total, per_repo, ids = GH(), 0, {}, set()
    with open(state / f"metadata/{ds}/docs.jsonl", "w") as out:
        for i, r in enumerate(repos, 1):
            key = f"{r['owner']}/{r['name']}"
            n = 0
            for pr in gh.pages(f"repos/{key}/pulls", state="closed", sort="updated", direction="desc"):
                if not pr.get("merged_at"):
                    continue
                fr = gh.get(f"repos/{key}/pulls/{pr['number']}/files", per_page=100)
                if fr.status_code not in (200, 404):
                    sys.exit(f"FAIL: GitHub HTTP {fr.status_code} reading PR files; refusing to write a PR with no files")
                files = [f["filename"] for f in fr.json()] if fr.status_code == 200 else []
                more = " (first 100 shown)" if len(files) == 100 else ""
                # Conversation, review summaries and inline review comments: where direction and decisions show up.
                talk = [f"### {c['user']['login']} ({c['created_at'][:10]})\n\n{c.get('body') or ''}\n"
                        for c in gh.pages(f"repos/{key}/issues/{pr['number']}/comments")]
                talk += [f"### review by {v['user']['login']}: {v['state']}\n\n{v.get('body') or ''}\n"
                         for v in gh.pages(f"repos/{key}/pulls/{pr['number']}/reviews") if v.get("body")]
                talk += [f"### {c['user']['login']} on `{c.get('path', '')}`\n\n{c.get('body') or ''}\n"
                         for c in gh.pages(f"repos/{key}/pulls/{pr['number']}/comments")]
                thread = ("\n## Discussion and review\n\n" + "\n".join(talk)) if talk else ""
                body = (f"# {key} PR #{pr['number']}: {pr['title']}\n\n- repo: {key}\n- author: {pr['user']['login']}\n"
                        f"- merged_at: {pr['merged_at']}\n- base: {pr['base']['ref']}\n- url: {pr['html_url']}\n"
                        f"- changed files: {len(files)}{more}\n\n## Description\n\n{pr.get('body') or '(no description)'}\n\n"
                        f"## Changed paths\n\n" + "\n".join(f"- `{f}`" for f in files) + "\n" + thread)
                did = doc_id("pr", f"github://{key}/pull/{pr['number']}")
                write_doc(state, ds, did, body, {"source": "github", "owner": r["owner"], "repo": r["name"], "path": "",
                          "kind": "pr", "language": "", "visibility": r["visibility"], "commit_sha": pr.get("merge_commit_sha") or "",
                          "html_url": pr["html_url"], "updated_at": pr["merged_at"], "pr_number": pr["number"]},
                          "text/html", "html", a.bucket, out)
                ids.add(did)
                n += 1
            per_repo[key] = n
            total += n
            print(f"[{i}/{len(repos)}] {doc_id('rp', f'github://{key}')} merged_prs={n}", flush=True)
    (state / "reports").mkdir(exist_ok=True)
    json.dump({"total": total, "repos_with_prs": sum(1 for v in per_repo.values() if v), "per_repo": per_repo},
              open(state / "reports/prs.json", "w"), indent=1)
    print(f"merged PR docs={total} unique_ids={len(ids)} across {sum(1 for v in per_repo.values() if v)} repos")
    if len(ids) != total:
        sys.exit("FAIL: duplicate document ids")


if __name__ == "__main__":
    main()
