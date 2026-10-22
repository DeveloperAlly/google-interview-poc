"""Import a harvested corpus straight into a data store with inlineSource: no Cloud Storage involved.

Zero-cost path (DECISIONS D5): GCS storage and per-object upload operations are billable outside the free-tier
regions, the digital parser "is offered without charge", and index storage under 10 GiB is free.
Batches are capped at 100 documents and ~8 MB of content per request. Resumable: finished batches are recorded.
"""
import argparse, base64, json, sys, time
from pathlib import Path
from datastores import Client

MAX_DOCS, MAX_BYTES = 100, 8 * 1024 * 1024


def batches(state: Path, ds: str):
    cur, size = [], 0
    for line in (state / f"metadata/{ds}/docs.jsonl").read_text().splitlines():
        m = json.loads(line)
        raw = (state / "corpus" / ds / m["content"]["uri"].rsplit("/", 1)[-1]).read_bytes()
        doc = {"id": m["id"], "structData": m["structData"],
               "content": {"mimeType": m["content"]["mimeType"], "rawBytes": base64.b64encode(raw).decode()}}
        if cur and (len(cur) == MAX_DOCS or size + len(raw) > MAX_BYTES):
            yield cur
            cur, size = [], 0
        cur.append(doc)
        size += len(raw)
    if cur:
        yield cur


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--state", required=True)
    ap.add_argument("--ds", required=True, help="corpus name under <state>/corpus")
    ap.add_argument("--target", required=True, help="data store id")
    ap.add_argument("--run", required=True)
    a = ap.parse_args()
    state = Path(a.state)
    log = state / f"reports/import-{a.target}-{a.run}.jsonl"
    log.parent.mkdir(exist_ok=True)
    done = {json.loads(l)["batch"] for l in log.read_text().splitlines()} if log.exists() else set()
    c = Client(a.project)
    url = f"{c.base}/dataStores/{a.target}/branches/default_branch/documents:import"
    tot_ok = tot_fail = 0
    for i, docs in enumerate(batches(state, a.ds)):
        if i in done:
            continue
        for attempt in range(8):
            r = c.call("POST", url, json={"inlineSource": {"documents": docs}, "reconciliationMode": "INCREMENTAL"})
            if r.status_code not in (429, 500, 503):
                break
            time.sleep(min(60, 2 ** attempt * 5))
        if r.status_code != 200:
            sys.exit(f"FAIL batch {i}: HTTP {r.status_code} {r.text[:400]}")
        op = r.json()
        while not op.get("done"):
            time.sleep(5)
            op = c.call("GET", op["name"]).json()
        m = op.get("metadata", {})
        ok, fail = int(m.get("successCount", 0)), int(m.get("failureCount", 0))
        rec = {"batch": i, "docs": len(docs), "success": ok, "failure": fail, "error": op.get("error"),
               "errorSamples": op.get("response", {}).get("errorSamples", [])[:5]}
        with open(log, "a") as f:
            f.write(json.dumps(rec) + "\n")
        tot_ok, tot_fail = tot_ok + ok, tot_fail + fail
        print(f"batch {i}: docs={len(docs)} success={ok} failure={fail} error={bool(op.get('error'))}", flush=True)
    print(f"run total this invocation: success={tot_ok} failure={tot_fail}")


if __name__ == "__main__":
    main()
