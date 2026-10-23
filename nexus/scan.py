"""Secret-scan the corpus with gitleaks and drop every flagged document before upload.

Writes <state>/reports/secret-scan.json (redacted: rule, hashed doc id, line) and rewrites docs.jsonl without them.
"""
import argparse, collections, json, subprocess, sys
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--state", required=True)
a = ap.parse_args()
state = Path(a.state)
(state / "reports").mkdir(parents=True, exist_ok=True)
raw = state / "reports/gitleaks.json"
r = subprocess.run(["gitleaks", "dir", str(state / "scan"), "--no-banner", "--redact",
                    "--report-format", "json", "--report-path", str(raw), "--exit-code", "0"], capture_output=True, text=True)
if r.returncode != 0:
    sys.exit(f"FAIL: gitleaks exit {r.returncode}: {r.stderr[-500:]}")
findings = json.load(open(raw))
# Repo-summary docs (rp-*) are redacted line by line instead of dropped: dropping one hides the whole repo from
# search, and its only risky content is the README excerpt. Every other flagged document is held back whole.
from harvest import to_html
redact = collections.defaultdict(set)
for f in findings:
    if Path(f["File"]).stem.startswith("rp-"):
        redact[Path(f["File"]).stem].update(range(f["StartLine"], f["EndLine"] + 1))
for did, lines in redact.items():
    for md in (state / "scan").glob(f"*/{did}.md"):
        text = md.read_text(encoding="utf-8").split("\n")
        text = ["[line redacted: possible credential]" if i + 1 in lines else t for i, t in enumerate(text)]
        md.write_text("\n".join(text), encoding="utf-8")
        html = state / "corpus" / md.parent.name / f"{did}.html"
        html.write_text(to_html("\n".join(text), text[0].lstrip("# ")), encoding="utf-8")
flagged = {Path(f["File"]).stem for f in findings} - set(redact)

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

json.dump({"findings": len(findings), "files_dropped": len(flagged), "summaries_redacted": len(redact),
           "by_rule": collections.Counter(f["RuleID"] for f in findings),
           "dropped": sorted({(Path(f["File"]).stem, f["RuleID"], f["StartLine"]) for f in findings})},
          open(state / "reports/secret-scan.json", "w"), indent=1)
raw.rename(state / "quarantine/gitleaks-raw.json")  # raw report stays local; the summary is the record

# Re-scan: the upload set must now be clean.
remaining = 0
for sub in ("scan", "corpus"):  # both the raw text and the HTML that will actually upload
    r2 = subprocess.run(["gitleaks", "dir", str(state / sub), "--no-banner", "--redact", "--report-format", "json",
                         "--report-path", "-", "--exit-code", "0"], capture_output=True, text=True)
    if r2.returncode != 0:
        sys.exit(f"FAIL: verification scan of {sub} exited {r2.returncode}: {r2.stderr[-300:]}")
    try:
        remaining += len(json.loads(r2.stdout))
    except json.JSONDecodeError:
        sys.exit(f"FAIL: verification scan of {sub} produced no JSON report")
print(f"findings={len(findings)} files_dropped={len(flagged)} summaries_redacted={len(redact)} remaining_after_rescan={remaining}")
if remaining:
    sys.exit("FAIL: findings remain in upload set")
