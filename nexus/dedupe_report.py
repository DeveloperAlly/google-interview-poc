"""Measure duplicate file content across the corpus. Read-only; changes nothing it reports on.

Hashes the scanner copy (<state>/scan/<ds>/<id>.md) after its header block, since repo, path, commit and
permalink differ between copies of the same file. Writes <state>/reports/dedupe-<ds>.json.
"""
import argparse, collections, hashlib, json
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", required=True)
    ap.add_argument("--ds", default="ds-code")
    a = ap.parse_args()
    state = Path(a.state)
    groups = collections.defaultdict(list)
    for line in (state / f"metadata/{a.ds}/docs.jsonl").read_text().splitlines():
        m = json.loads(line)
        if m["structData"]["kind"] == "repo":
            continue
        text = (state / f"scan/{a.ds}/{m['id']}.md").read_text(encoding="utf-8")
        body = text.split("\n\n", 2)[-1]  # drop the title line and the metadata list
        groups[hashlib.sha256(body.encode()).hexdigest()].append(m["id"])
    docs = sum(len(v) for v in groups.values())
    redundant = sum(len(v) - 1 for v in groups.values() if len(v) > 1)
    in_dup_groups = sum(len(v) for v in groups.values() if len(v) > 1)
    out = {"file_docs": docs, "unique_bodies": len(groups), "redundant_copies": redundant,
           "docs_sharing_a_body": in_dup_groups, "redundant_pct": round(100 * redundant / docs, 1)}
    (state / "reports").mkdir(exist_ok=True)
    json.dump(out, open(state / f"reports/dedupe-{a.ds}.json", "w"), indent=1)
    print(out)


if __name__ == "__main__":
    main()
