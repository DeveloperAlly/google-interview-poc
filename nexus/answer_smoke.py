"""Smoke test the interview assistant end to end: every sample question must produce a cited answer through the
real local server, and role questions must name the role from the owner's role facts. Prints only measured results."""
import json, re, sys, urllib.request
from pathlib import Path

STATE = Path(__file__).resolve().parent.parent / "state"
# Owner-only expectations live in gitignored state: the demo-scope repos and the role pattern per role question.
SCOPE = tuple(json.load(open(STATE / "demo-scope.json")).get("repos", [])) if (STATE / "demo-scope.json").exists() else ()
EXPECT = json.load(open(STATE / "smoke-expect.json")) if (STATE / "smoke-expect.json").exists() else {}

CASES = [
    ("Tell me about a time you set technical direction for a team building a product.", None),
    ("How have you bridged pre-sales agreement shaping and post-sales execution?", None),
    ("Describe an enterprise integration you designed, including identity and data constraints.", None),
    ("Tell me about a complex bug or production issue you diagnosed.", None),
    ("How did you design Lilypad's architecture, and what was your role?", EXPECT.get("architecture")),
    ("How do you turn field feedback into product requirements?", None),
    ("Tell me about a partnership you structured with an enterprise customer.", EXPECT.get("partnership")),
    ("What have you built with AI agents and orchestration frameworks?", None),
]
ok = 0
for q, must in CASES:
    req = urllib.request.Request("http://127.0.0.1:8765/api/ask", data=json.dumps({"question": q, "scope": "demo"}).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        d = json.load(urllib.request.urlopen(req, timeout=120))
    except Exception as e:
        print(f"FAIL request error: {e} :: {q[:60]}"); continue
    ans, refs = d.get("answer", ""), d.get("references", [])
    cites = {int(m.strip().split(":")[0]) for g in re.findall(r"\[([\d:,\s]+)\]", ans) for m in g.split(",") if m.strip()}
    bad = [c for c in cites if c < 1 or c > len(refs)]
    nonpublic = [r["repo"] for r in d.get("results", []) if r.get("visibility") != "public" and r["repo"].split("/")[-1] not in SCOPE]
    checks = {"answer": bool(ans), "cited": bool(cites) and not d.get("uncited"), "citations_valid": not bad, "scope_held": not nonpublic,
              "role": (re.search(must, ans, re.I) is not None) if must else True}
    passed = all(checks.values()); ok += passed
    print(f"{'PASS' if passed else 'FAIL'} attempts={d.get('attempts')} refs={len(refs)} cites={sorted(cites)} {[k for k, v in checks.items() if not v]} :: {q[:60]}")
print(f"{ok} of {len(CASES)} passed")
(STATE / "reports").mkdir(exist_ok=True)
(STATE / "reports" / "answer-smoke.json").write_text(json.dumps({"passed": ok, "cases": len(CASES)}))
sys.exit(0 if ok == len(CASES) else 1)
