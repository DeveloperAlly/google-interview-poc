"""Secret-scan the corpus with gitleaks and drop every flagged document before upload.

Writes <state>/reports/secret-scan.json (redacted: rule, hashed doc id, line) and rewrites docs.jsonl without them.
"""
import argparse, collections, json, subprocess, sys
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--state", required=True)
a = ap.parse_args()
state = Path(a.state)
raw = state / "reports/gitleaks.json"
r = subprocess.run(["gitleaks", "dir", str(state / "scan"), "--no-banner", "--redact",
                    "--report-format", "json", "--report-path", str(raw), "--exit-code", "0"], capture_output=True, text=True)
if r.returncode != 0:
    sys.exit(f"FAIL: gitleaks exit {r.returncode}: {r.stderr[-500:]}")
findings = json.load(open(raw))
flagged = {Path(f["File"]).stem for f in findings}

for ds_dir in (state / "metadata").iterdir():
    jl = ds_dir / "docs.jsonl"
    lines = jl.read_text().splitlines()
    keep = [l for l in lines if json.loads(l)["id"] not in flagged]
    jl.write_text("\n".join(keep) + ("\n" if keep else ""))
    quarantine = state / "quarantine" / ds_dir.name
    quarantine.mkdir(parents=True, exist_ok=True)
    for did in flagged:  # moved, not deleted: kept local for review, never uploaded
        for sub in ("corpus", "scan"):
            for p in (state / sub / ds_dir.name).glob(f"{did}.*"):
                p.rename(quarantine / f"{sub}-{p.name}")
    print(f"{ds_dir.name}: before={len(lines)} after={len(keep)} dropped={len(lines) - len(keep)}")

json.dump({"findings": len(findings), "files_dropped": len(flagged),
           "by_rule": collections.Counter(f["RuleID"] for f in findings),
           "dropped": sorted({(Path(f["File"]).stem, f["RuleID"], f["StartLine"]) for f in findings})},
          open(state / "reports/secret-scan.json", "w"), indent=1)
raw.rename(state / "quarantine/gitleaks-raw.json")  # raw report stays local; the summary is the record

# Re-scan: the upload set must now be clean.
remaining = 0
for sub in ("scan", "corpus"):  # both the raw text and the HTML that will actually upload
    r2 = subprocess.run(["gitleaks", "dir", str(state / sub), "--no-banner", "--redact", "--report-format", "json",
                         "--report-path", "-", "--exit-code", "0"], capture_output=True, text=True)
    remaining += len(json.loads(r2.stdout or "[]"))
print(f"findings={len(findings)} files_dropped={len(flagged)} remaining_after_rescan={remaining}")
if remaining:
    sys.exit("FAIL: findings remain in upload set")
