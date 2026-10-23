"""Run the interview test set through the live answer server and record every answer for human judgement.

Tests live in gitignored state (they carry the candidate's facts). Each test has: must (all patterns present),
should (counted, not required), must_not (none present), role (pattern for the role named). The automatic check is a
first filter only: every answer is saved in full so a person can judge it. Prints measured results only.
"""
import json, re, sys, time, urllib.request
from pathlib import Path

STATE = Path(__file__).resolve().parent.parent / "state"


def ask(q):
    req = urllib.request.Request("http://127.0.0.1:8765/api/ask", data=json.dumps({"question": q, "scope": "demo"}).encode(),
                                 headers={"Content-Type": "application/json"})
    t = time.time()
    d = json.load(urllib.request.urlopen(req, timeout=180))
    return d, time.time() - t


def main():
    spec = json.load(open(STATE / "interview-tests.json"))
    rows, passed = [], 0
    for t in spec["tests"]:
        try:
            d, secs = ask(t["q"])
        except Exception as e:
            rows.append({**t, "error": str(e)}); print(f"ERROR {t['id']}: {e}"); continue
        a = (d.get("answer") or "").lower()
        miss = [p for p in t["must"] if not re.search(p, a)]
        bad = [p for p in t["must_not"] if re.search(p, a)]
        should = sum(bool(re.search(p, a)) for p in t["should"])
        role_ok = True if not t.get("role") else bool(re.search(t["role"], a))
        cited = not d.get("uncited") and bool(re.search(r"\[\d", a))
        ok = not miss and not bad and role_ok and (cited or t["id"].startswith(("G", "S")))
        passed += ok
        rows.append({**t, "answer": d.get("answer", ""), "references": d.get("references", []), "seconds": round(secs, 1),
                     "attempts": d.get("attempts"), "uncited": d.get("uncited"), "missing": miss, "forbidden": bad,
                     "should_hits": f"{should}/{len(t['should'])}", "role_ok": role_ok, "auto_pass": ok})
        print(f"{'PASS' if ok else 'FAIL'} {t['id']:3} {secs:5.1f}s cited={cited} missing={miss} forbidden={bad} "
              f"should={should}/{len(t['should'])} role={role_ok} :: {t['q'][:60]}", flush=True)
    secs = sorted(r["seconds"] for r in rows if "seconds" in r)
    p95 = secs[max(0, int(round(0.95 * len(secs))) - 1)] if secs else None
    out = {"auto_passed": passed, "tests": len(spec["tests"]), "p95_seconds": p95, "rows": rows}
    (STATE / "evidence").mkdir(exist_ok=True)
    (STATE / "evidence" / "interview-test-results.json").write_text(json.dumps(out, indent=1))
    print(f"auto-check: {passed} of {len(spec['tests'])} passed; p95 answer time {p95}s; full answers saved for human review")


if __name__ == "__main__":
    main()
