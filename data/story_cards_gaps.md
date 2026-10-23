# Story card gaps (C3 round 2, A2b; A2c 2026-10-23: S10 rewritten, Nexus roles settled)

Cards live in `state/story_cards.json` (16 cards, S1 to S16; A2e added S13 to S16 and R15 on S10). Every role requirement R1 to R29 now has a card. A `missing` slot stays `missing`. These questions are optional: a card reads as is with its gap stated.

## Roles and dates

Settled by the owner in `state/owner_facts.md` (overrides every other source): Lilypad "Founder & CEO, Sep 2023 to Oct 2025", "thousands of GPU nodes"; Dell partnership "structured", not signed; Lilypad v0 built at Protocol Labs (2022 to 2023).

| Organisation | Title and dates (source) | Role per card |
|---|---|---|
| Lilypad Network | Founder & CEO, Sep 2023 to Oct 2025 (owner_facts) | S1 anura and modules: **directed**. S7 Dell: **led**. S10 Tufts and Hugging Face: **directed** (owner_facts: hired, paid, directed and embedded) |
| Protocol Labs / Filecoin Foundation | Jan 2022 to Nov 2023; titles differ across resumes ("PM, FVM Developer Experience", "Product & Developer Relations Lead, FVM", CV "Developer Relations Engineer to Technical Product DX Lead") | S2 FVM DX and Space Warp: **led**. S3 Lilypad v0: **built** |
| IBM ANZ | Developer Relations Manager & Enterprise Account Technical Partner, Apr 2020 to Jan 2022 (CV) | S8: **missing** |
| Livepeer | Startup Advisor & Agentic Systems Consultant, Nov 2025 to present (CV) | S6 DocsOS: **built** (authored PRs) |
| Nexus (this repo) | owner_facts: "I built and led it, directing AI agents that wrote the code" | S4, S5, S9, S11, S12, S13, S15: **led** |
| Geo-Monitor (gamerslab repo) | Portfolio document, role not stated in words | S14: **built** |
| University of Wollongong | BE (Mechatronics) / BCompSci (Hons), 2012 to 2017 (CV, corroboration ledger) | S16: **studied** |

## Gap questions

- **S1 metric:** the "within 24 hours" model-deploy figure is from the direction guide only. Recorded anywhere?
- **S3 metric:** any number for Lilypad v0 (jobs run, teams using it)? If none, it stays missing.
- **S6:** the deck's hot-reload figure (30+ s to under 500 ms) is self-reported. Is it recorded in a PR or CI run?
- **S7 action and metric:** who at Dell did you work with, and what did the partnership produce (pilot, licence terms)? Not signed, per owner_facts.
- **S8 IBM:** did you architect, build or lead the BHP and Telstra solutions and the NSW Police and Defence Force PoCs? What did each account need? Did any PoC convert?
- **S10 Tufts:** which model was deployed: AlphaFold 2 (your talk notes) or ColabFold (the Lilypad blog, written by another author)? Your LinkedIn draft says "with Dell and Tufts": was Dell part of it? The draft also says "Nobody on my team wrote it": superseded by owner_facts? Any figure (runs, time to deploy)? Metric stays missing until sourced.
- **R12 (S14), honest partial gap:** the posting names LangGraph, AutoGen and CrewAI. No source shows any of the three. Closest real experience: n8n as the orchestration hub in Geo-Monitor (S14), n8n agent orchestration on your resumes, and the LangChain-compatible anura gateway (S1). Have you used any of the three?
- **R8 (S16):** the corroboration ledger names a BA at ANU in Philosophy/Politics/French; other records differ on the majors. The card omits the BA until you confirm.
- **R19, R29, R23 (S13) and R26 (S15):** the customer is your own GitHub estate in a POC. For an external enterprise example the closest are S7 (Dell) and S8 (IBM ANZ), both self-reported.
- **R15 (S10):** added to the Tufts and Hugging Face card: you hired, paid and directed the researchers (owner_facts).
- **S11:** was any field finding (F1 to F11) filed with Google or acted on?

## Self-reported (CV, deck, guide or resume is the only source)

S1, S2, S3, S6 (result, metric), S7, S8, S10 (situation, task, result; action and role from owner_facts): marked in `self_reported_slots` or `self_reported` per source. S4, S5, S9, S11, S12 cite this repo's docs/01, docs/03, docs/04 (record). S6 PR counts are a GitHub record.

Not used anywhere: the Case Study, Lifecycle, Nexus Autonomous Technical Knowledge Engine and Vertex AI Search decks, the Drive Export Master Archive; from the Livepeer deck, "830+ files", "Completed in landmark PR #730", "100% ... at zero engineering cost", "Staff+", "8+ months before MCP mainstream".
