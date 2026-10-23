"""Reconcile: documents present in a data store (documents.list) against the harvested manifest, per repo.

Writes <state>/reports/coverage-<ds>.json. Exits non-zero unless every expected id is present.
Prints counts and hashed repo ids only.
"""
import argparse, collections, json, sys
from pathlib import Path
from datastores import Client


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--state", required=True)
    ap.add_argument("--ds", required=True, help="corpus name under <state>/metadata")
    ap.add_argument("--target", required=True, help="data store id")
    ap.add_argument("--manifest", help="repos.json: require a present repo-summary doc for every included repo")
    a = ap.parse_args()
    state = Path(a.state)
    expected = {}
    for l in (state / f"metadata/{a.ds}/docs.jsonl").read_text().splitlines():
        m = json.loads(l)
        expected[m["id"]] = f"{m['structData']['owner']}/{m['structData']['repo']}"
    c = Client(a.project)
    url = f"{c.base}/dataStores/{a.target}/branches/default_branch/documents"
    present, token, calls = set(), None, 0
    while True:
        r = c.call("GET", url, params={"pageSize": 1000, **({"pageToken": token} if token else {})})
        calls += 1
        if r.status_code != 200:
            sys.exit(f"FAIL documents.list HTTP {r.status_code}: {r.text[:300]}")
        j = r.json()
        present |= {d["id"] for d in j.get("documents", [])}
        token = j.get("nextPageToken")
        if not token:
            break
    missing = set(expected) - present
    extra = present - set(expected)
    by_repo = collections.defaultdict(lambda: {"expected": 0, "present": 0})
    for did, repo in expected.items():
        by_repo[repo]["expected"] += 1
        by_repo[repo]["present"] += did in present
    gaps = {k: v for k, v in by_repo.items() if v["expected"] != v["present"]}
    (state / "reports").mkdir(exist_ok=True)
    json.dump({"target": a.target, "list_calls": calls, "expected": len(expected), "present": len(present),
               "missing": len(missing), "extra_in_store": len(extra), "repos": len(by_repo),
               "repos_with_gaps": gaps, "missing_ids": sorted(missing)[:500]},
              open(state / f"reports/coverage-{a.target}.json", "w"), indent=1)
    print(f"{a.target}: expected={len(expected)} present={len(present)} missing={len(missing)} "
          f"extra={len(extra)} repos={len(by_repo)} repos_with_gaps={len(gaps)} list_calls={calls}")
    uncovered = []
    if a.manifest:
        from harvest import doc_id
        for r in json.load(open(a.manifest)):
            if r["include"] and doc_id("rp", f"github://{r['owner']}/{r['name']}") not in present:
                uncovered.append(doc_id("rp", f"github://{r['owner']}/{r['name']}"))
        print(f"manifest coverage: included repos without a summary doc in the store = {len(uncovered)}")
    if missing:
        sys.exit("FAIL: documents missing from the data store")
    if uncovered:
        sys.exit("FAIL: harvest did not cover every included repo in the manifest")


if __name__ == "__main__":
    main()
