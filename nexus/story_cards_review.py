"""Hand-review pass over state/story_cards.json (C3).

Each edit below replaces a Gemini-drafted slot after reading the source. Every replacement
quote is re-checked verbatim against its source by story_cards.verify, so a hand edit
cannot introduce an unsourced fact either.
"""
import json, sys
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import story_cards as sc

MC = sc.MC
NV = f"{MC}/resumes/Ally_Haire_Resume_NVIDIA_ANZ_DevRel.md"
COTI = f"{MC}/resumes/Ally_Haire_Resume_COTI.md"
COPY = f"{MC}/resumes/Copy - Resume.md"
INV = f"{MC}/brand/evidence/achievement-inventory.md"
RF = f"{MC}/brand/evidence/role-functions-and-skills.md"
DELLP = f"{sc.DRIVE}/dell/Lilypad Product Deck & Dell Proposal.pptx"
DELLD = f"{sc.DRIVE}/dell/Dell <> Lilypad Deck.docx"
LP = f"{sc.DRIVE}/Livepeer DocsOS: Product & Engineering Architecture.pptx"
GUIDE = sc.GUIDE
MISSING = "missing"

def ev(*pairs):
    return {"evidence": [{"source": s, "quote": q} for s, q in pairs]}

EDITS = {
  "S1": {
    "metric": dict(text="Because models were pluggable Git-versioned modules, our ecosystem could deploy DeepSeek R1 or Wan2.1 Video within 24 hours of release without touching the core Go solver daemon.",
                   **ev((GUIDE, "By treating AI models as pluggable Git-versioned modules rather than core protocol primitives, our ecosystem could deploy DeepSeek R1 or Wan2.1 Video within 24 hours of release without touching a single line of the core Go solver daemon."))),
  },
  "S2": {
    "result": dict(text="Space Warp, the flagship FVM developer activation event that I designed and ran, drew 1,000+ hackers and 276 submissions.",
                   **ev((NV, "Designed and ran the Space Warp Hackathon: 1,000+ hackers, 276 submissions, the flagship FVM developer activation event."))),
    "metric": dict(text="Space Warp: 1,000+ hackers, 276 submissions.",
                   **ev((NV, "Designed and ran the Space Warp Hackathon: 1,000+ hackers, 276 submissions, the flagship FVM developer activation event."))),
  },
  "S3": {
    "situation": dict(text="Lilypad started as a single Filecoin smart contract proof-of-concept, built on the Bacalhau team at Protocol Labs.",
                      **ev((INV, "took a single Filecoin smart contract proof-of-concept (Lilypad v0, built on the Bacalhau team at Protocol Labs)"))),
  },
  "S4": {
    "_role": MISSING,
    "situation": dict(text="My experience was spread across hundreds of repos, talks, writing and documents, and much of it was direction I set rather than code I wrote, so I could not quickly pull up verifiable evidence for a claim.",
                      **ev(("docs/01-discovery-and-feasibility.md", "Her experience is spread across hundreds of repos, talks, writing and documents, and much of it is direction she set rather than code she wrote."))),
    "task": dict(text="Before anything billable or permanent was created, we had to establish whether indexing every repository I own into Google Agent Search could be delivered inside my real constraints.",
                 **ev(("docs/01-discovery-and-feasibility.md", "The question this phase answers is whether the solution can be delivered as asked, inside the customer's real constraints, before anything billable or permanent is created."))),
    "action": dict(text="Every feasibility check was a real call: network path to the API, read access to both GitHub owners, supported document formats, chunking prerequisites, import limits, a credential scan and cost. Every figure in the brief was treated as a claim until it was re-derived from the system of record.",
                   **ev(("docs/01-discovery-and-feasibility.md", "Lesson carried forward: every figure in a brief is a claim until it is re-derived from the system of record."),
                        ("docs/01-discovery-and-feasibility.md", "Feasibility checks (each one a real call)"))),
    "result": dict(text="The paginated API count was 293 repos and none of the brief's earlier figures matched. The full import on the layout parser was priced at about USD 504 and stopped before submission, and I set the budget to zero.",
                   **ev(("docs/01-discovery-and-feasibility.md", "293 repos from the API, counted by paginating both owners. None of the earlier figures matched; the manifest is the source of truth"),
                        ("docs/03-delivery-log.md", "Full import on layout parser about USD 504; pilot about USD 37 already incurred. Full import stopped before submission. Owner set budget to zero"))),
    "metric": dict(text="293 repos counted, 204 in scope at the go decision; full import of about USD 504 avoided after a pilot of about USD 37.",
                   **ev(("docs/01-discovery-and-feasibility.md", "Result at the time: 204 repos in scope"),
                        ("docs/01-discovery-and-feasibility.md", "293 repos from the API, counted by paginating both owners."),
                        ("docs/03-delivery-log.md", "Full import on layout parser about USD 504; pilot about USD 37 already incurred. Full import stopped before submission. Owner set budget to zero"))),
  },
  "S5": {
    "situation": dict(text="The goal was a first-person answer to any interview question with a citation on every claim, and answers that know my role, because founding and directing a project is different from writing its code.",
                      **ev(("docs/00-architecture.md", "Ask what an interviewer would ask; get a first-person answer with a citation on every claim, with no model key"),
                           ("docs/00-architecture.md", "Answers that know the candidate's role: founding and directing a project is different from writing its code"))),
    "task": dict(text="Every piece of evidence of the work had to go in complete, with no secrets uploaded.",
                 **ev(("docs/00-architecture.md", "Every piece of evidence of the work (code, PRs and review threads, issues, commit history, contributions to other organisations' projects, talks, resumes, writing), complete, with no secrets uploaded"))),
    "action": dict(text="The full harvest covered 204 repos and 16,772 documents. A gitleaks scan on raw text found 483 findings, 217 documents were dropped and a re-scan came back at 0, leaving 16,555 to upload.",
                   **ev(("docs/03-delivery-log.md", "204 repos, 16,772 docs, 16,772 unique ids"),
                        ("docs/03-delivery-log.md", "483 findings, 217 docs dropped, re-scan 0; 16,555 to upload"))),
    "result": dict(text="The code import ran in 166 inline batches with 16,555 succeeded and 0 failed, and reconciliation found 0 missing and 0 extra.",
                   **ev(("docs/03-delivery-log.md", "166 inline batches; 16,555 succeeded, 0 failed"),
                        ("docs/03-delivery-log.md", "expected 16,555, present 16,555, missing 0, extra 0, 204 repos, 0 with gaps"))),
    "metric": dict(text="16,555 of 16,555 documents imported and reconciled, 0 missing.",
                   **ev(("docs/03-delivery-log.md", "expected 16,555, present 16,555, missing 0, extra 0, 204 repos, 0 with gaps"))),
  },
  "S6": {
    "result": dict(text="Contributor onboarding went from hours of troubleshooting to a single automated command.",
                   **ev((LP, "Reduced contributor onboarding time from hours of troubleshooting to a single automated command."))),
  },
  "S7": {
    "_role": ("led", RF, "Managed Dell relationship through product development and commercial conversations"),
    "_project": "Dell enterprise partnership for Lilypad",
    "situation": dict(text="Dell partners buying Dell infrastructure could mitigate costs with Lilypad's DeAI factory by monetizing idle compute, and Dell could gain new users in open source communities, web3 and AI.",
                      **ev((DELLP, "Dell partners buying Dell infrastructure can mitigate costs with the DeAI factory to monetize idle compute."),
                           (DELLP, "Unlock new markets with our module marketplace. Gain new users in open source  communities, web3, and  AI."))),
    "task": dict(text="I structured an enterprise partnership with Dell to develop a permissioned, licensable version of Lilypad for enterprise AI adoption.",
                 **ev((COTI, "Structured an enterprise partnership with Dell to develop a permissioned, licensable version of Lilypad for enterprise AI adoption."))),
    "action": dict(text="I presented the About Lilypad and protocol section of our Dell proposal, which also covered a NativeEdge integration, and I managed the Dell relationship through product development and commercial conversations.",
                   **ev((DELLP, "About Lilypad & the Protocol (AH)"),
                        (RF, "Managed Dell relationship through product development and commercial conversations"))),
    "result": dict(text="Dell is listed among Lilypad's strategic partnerships, and I led a DeSci research partnership with Dell, Dr. Michael Levin at Tufts and Hugging Face that produced a novel protein-folding drug candidate now in wet-lab validation.",
                   **ev((DELLD, "Strategic Partnerships with Dell, Morpheus, Cedars-Sinai & deAI projects"),
                        (COPY, "Led a DeSci research partnership (Dell, Dr. Michael Levin/Tufts, Hugging Face) that produced a novel protein-folding drug candidate now in wet-lab validation."))),
    "metric": MISSING,
  },
}

GAPS = {
  "S1": {"metric": "The '24 hours to deploy a new model' figure comes only from the engineering-direction guide's interview script. Is it true, and is it recorded anywhere (a release note, PR or tweet)?"},
  "S2": {},
  "S3": {"metric": "Is there any number for Lilypad v0 (jobs run, demo users, hackathon teams using it)? If none, say none."},
  "S4": {"role": "On Nexus, did you build it, lead it or direct it (docs/03 shows you approving gates G0 to G5)?"},
  "S5": {"role": "Same as S4: built, led or directed on Nexus?"},
  "S6": {"metric": "One number from Livepeer DocsOS you can stand behind, with where it is recorded (a PR, issue or CI run)?",
         "role": "Livepeer: built or led? The guide says 'Hands-On Lead Architect & Product Strategist'; the CV says consultant from Nov 2025."},
  "S7": {"metric": "What did the Dell partnership produce commercially: a signed agreement, pilot or licence? Date and value if any.",
         "action": "Who at Dell did you work with (team or title, not a name), and what did you personally run after the proposal?"},
}

def apply():
    doc = sc.load_out()
    cards = {c["id"]: c for c in doc["cards"]}
    for cid, edits in EDITS.items():
        c = cards[cid]
        texts = {p: sc.extract(sc.ROOT / p) for p in set(c["sources_read"]) | {s for e in edits.values() if isinstance(e, dict) for s in (x["source"] for x in e["evidence"])} if (sc.ROOT / p).exists()}
        if "_project" in edits:
            c["project"] = edits["_project"]
        if "_role" in edits:
            c["sources"] = [s for s in c["sources"] if s["supports"] != "role"]
            c["self_reported_slots"] = [s for s in c["self_reported_slots"] if s != "role"]
            if edits["_role"] == MISSING:
                c["her_role"] = MISSING
            else:
                v, src, q = edits["_role"]
                assert sc.norm(q) in sc.norm(texts[src]), (cid, "role", q)
                c["her_role"] = v
                c["sources"].append({"path_or_url": src, "supports": "role", "quote": q, "self_reported": sc.self_reported(src)})
                c["self_reported_slots"].append("role")
        for slot, e in edits.items():
            if slot.startswith("_"):
                continue
            c["sources"] = [s for s in c["sources"] if s["supports"] != slot]
            c["self_reported_slots"] = [s for s in c["self_reported_slots"] if s != slot]
            if e == MISSING:
                c[slot] = MISSING
                continue
            text, good, why = sc.verify(e, texts)
            assert not why, (cid, slot, why)
            c[slot] = text
            for g in good:
                c["sources"].append({"path_or_url": g["path_or_url"], "supports": slot, "quote": g["quote"], "self_reported": g["self_reported"]})
            if all(g["self_reported"] for g in good):
                c["self_reported_slots"].append(slot)
        c["sources_read"] = sorted(set(c["sources_read"]) | set(texts))
    for cid, c in cards.items():
        missing = [s for s in sc.SLOTS if c[s] == MISSING] + (["role"] if c["her_role"] == MISSING else [])
        q = dict(GAPS.get(cid, {}))
        c["gaps"] = {k: q.get(k, f"For {c['project']}, what is the {k}, and where is it written down?") for k in missing}
        c["gaps"].update({k: v for k, v in q.items() if k not in c["gaps"]})
        c["reviewed"] = "hand-reviewed against sources by A2, 2026-10-23"
    sc.write_out(doc)

if __name__ == "__main__":
    apply()
