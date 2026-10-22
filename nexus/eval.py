"""Smoke eval: run golden queries through the real servingConfigs/default_search:search endpoint, score recall@5.

No generative features are requested (no summarySpec), so every query stays inside the free query allowance.
Writes <state>/reports/eval-<engine>.json. Prints PASS/FAIL per query only from a real HTTP 200 response.
"""
import argparse, json, sys
from pathlib import Path
import yaml
from datastores import Client


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--engine", required=True)
    ap.add_argument("--golden", required=True)
    ap.add_argument("--state", required=True)
    ap.add_argument("--k", type=int, default=5)
    a = ap.parse_args()
    qs = yaml.safe_load(open(a.golden))["queries"]
    c = Client(a.project)
    sc = f"{c.base}/engines/{a.engine}/servingConfigs/default_search"
    rows, made = [], 0
    for q in qs:
        r = c.call("POST", f"{sc}:search", json={"servingConfig": sc, "query": q["q"], "pageSize": a.k})
        made += 1
        if r.status_code != 200:
            rows.append({**q, "http": r.status_code, "hit": None, "error": r.text[:300]})
            print(f"ERROR http={r.status_code} q={q['q'][:60]}")
            continue
        top = []
        for res in r.json().get("results", [])[: a.k]:
            sd = res.get("document", {}).get("structData", {})
            top.append({"repo": f"{sd.get('owner')}/{sd.get('repo')}", "path": sd.get("path", ""), "kind": sd.get("kind"),
                        "pr_number": sd.get("pr_number")})
        paths = q.get("path_any") or [q.get("path_contains", "")]
        prs = q.get("pr_any")
        match = [t["repo"] == q["repo"] and any(p in t["path"] for p in paths)
                 and (prs is None or (t["pr_number"] is not None and int(t["pr_number"]) in prs)) for t in top]
        hit = any(match)
        rank = match.index(True) + 1 if hit else None
        rows.append({**q, "http": 200, "hit": hit, "rank": rank, "returned": len(top), "top": top})
        print(f"{'HIT ' if hit else 'MISS'} rank={rank} returned={len(top)} q={q['q'][:70]}")
    scored = [x for x in rows if x["hit"] is not None]
    recall = sum(x["hit"] for x in scored) / len(scored) if scored else None
    out = {"engine": a.engine, "k": a.k, "requests_made": made, "scored": len(scored),
           "errors": len(rows) - len(scored), "recall_at_k": recall, "rows": rows}
    Path(a.state, "reports").mkdir(parents=True, exist_ok=True)
    json.dump(out, open(Path(a.state, f"reports/eval-{a.engine}.json"), "w"), indent=1)
    print(f"requests={made} scored={len(scored)} errors={len(rows) - len(scored)} recall@{a.k}="
          f"{'n/a' if recall is None else f'{recall:.2f}'}")
    if not scored:
        sys.exit("FAIL: no query returned a scorable response")


if __name__ == "__main__":
    main()
