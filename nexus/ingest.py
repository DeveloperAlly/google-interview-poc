"""Upload a harvested corpus to GCS and import it into a data store (INCREMENTAL), polling to completion.

Splits metadata into <=90k-line JSONL files (import limit is 100k files per call).
Import errors land in gs://<bucket>/state/errors/<ds>/ and are summarised to <state>/reports/import-<ds>.json.
"""
import argparse, json, subprocess, sys, time
from pathlib import Path
from datastores import Client

BATCH = 90_000


def sh(*args):
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"FAIL {' '.join(args[:3])}: {r.stderr[-800:]}")
    return r.stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--bucket", required=True)
    ap.add_argument("--state", required=True)
    ap.add_argument("--ds", required=True)
    ap.add_argument("--target", help="data store to import into; defaults to --ds (the corpus name)")
    ap.add_argument("--run", required=True, help="run label, keeps metadata from different runs apart")
    a = ap.parse_args()
    state = Path(a.state)
    target = a.target or a.ds
    lines = (state / f"metadata/{a.ds}/docs.jsonl").read_text().splitlines()
    for l in lines:  # every uri must point at this bucket, or the import silently reads nothing
        if not json.loads(l)["content"]["uri"].startswith(f"gs://{a.bucket}/"):
            sys.exit("FAIL: metadata uri points at a different bucket; re-run harvest with --bucket")
    out = state / f"metadata/{a.ds}/batches-{a.run}"
    out.mkdir(parents=True, exist_ok=True)
    batches = []
    for i in range(0, len(lines), BATCH):
        p = out / f"part-{i // BATCH:03d}.jsonl"
        p.write_text("\n".join(lines[i:i + BATCH]) + "\n")
        batches.append(p)
    print(f"{a.ds}: {len(lines)} docs in {len(batches)} batch(es)")

    t = time.time()
    sh("gcloud", "storage", "rsync", "-r", str(state / f"corpus/{a.ds}"), f"gs://{a.bucket}/corpus/{a.ds}", "--quiet")
    sh("gcloud", "storage", "rsync", "-r", str(out), f"gs://{a.bucket}/metadata/{a.ds}/{a.run}", "--quiet")
    n = len(sh("gcloud", "storage", "ls", f"gs://{a.bucket}/corpus/{a.ds}/").split())
    print(f"uploaded in {time.time() - t:.0f}s; objects under corpus/{a.ds}: {n}")

    c = Client(a.project)
    ops = []
    for p in batches:
        body = {"gcsSource": {"inputUris": [f"gs://{a.bucket}/metadata/{a.ds}/{a.run}/{p.name}"], "dataSchema": "document"},
                "reconciliationMode": "INCREMENTAL",
                "errorConfig": {"gcsPrefix": f"gs://{a.bucket}/state/errors/{target}/{a.run}/"}}
        r = c.call("POST", f"{c.base}/dataStores/{target}/branches/default_branch/documents:import", json=body)
        print(f"import {p.name}: HTTP {r.status_code}")
        if r.status_code != 200:
            sys.exit(f"FAIL import submit: {r.text[:500]}")
        ops.append(r.json()["name"])
    (state / "reports").mkdir(exist_ok=True)
    results = []
    for name in ops:
        print(f"polling {name.rsplit('/', 1)[-1]}", flush=True)
        while True:
            op = c.call("GET", name).json()  # Client refreshes the user credential as needed
            if op.get("done"):
                break
            m = op.get("metadata", {})
            print(f"  success={m.get('successCount', 0)} failure={m.get('failureCount', 0)} total={m.get('totalCount', '?')}", flush=True)
            time.sleep(30)
        m = op.get("metadata", {})
        res = {"operation": name, "done": True, "error": op.get("error"), "successCount": int(m.get("successCount", 0)),
               "failureCount": int(m.get("failureCount", 0)), "errorSamples": op.get("response", {}).get("errorSamples", [])[:20]}
        results.append(res)
        print(f"done: success={res['successCount']} failure={res['failureCount']} error={res['error']}")
    json.dump({"ds": target, "corpus": a.ds, "run": a.run, "submitted": len(lines), "operations": results},
              open(state / f"reports/import-{target}-{a.run}.json", "w"), indent=1)
    if any(r["error"] for r in results):
        sys.exit("FAIL: an import operation returned an error")


if __name__ == "__main__":
    main()
