# 05. Cost and commercials

Engagement phase: shaping for adoption and viable delivery. A solution the customer cannot afford to run is
not delivered, whatever the demo shows.

## Price points used (Agent Search pricing page, read 2026-10-23)

| Item | Price |
|---|---|
| Free trial | 10,000 queries per account per month at no cost; excludes Advanced Generative Answers |
| Search Standard | USD 1.50 per 1,000 queries |
| Search Enterprise (includes core generative answers) | USD 4.00 per 1,000 queries |
| Advanced Generative Answers add-on | + USD 4.00 per 1,000 user input queries |
| Index storage | First 10 GiB per month free |
| Layout parser, including initial chunking | USD 10 per 1,000 pages. HTML: up to 3,000 characters = 1 page |
| Digital parser | "Offered without charge" (parse and chunk docs) |

## Cost of the corpus under each design

| Design | Basis | Estimate |
|---|---|---|
| Layout parser + chunking, full corpus | 125,573,958 characters = 50,430 pages | about USD 504, one-off at import |
| Layout parser, pilot only (8 repos, 900 docs) | 3,675 pages | about USD 37, **incurred** |
| Digital parser, no chunking, inline import | free parser, under 10 GiB index, queries in free trial | USD 0 |

## Correction of error: billable pilot before the cost check

- **What happened.** The pilot import into a layout-parser data store ran before the pricing page was read.
  The cost check was promised as a gate before the full import, so it sat after the first billable action.
- **Impact.** About USD 37 estimated (3,675 pages). The full import, about USD 504, was stopped before
  submission. The customer then set the budget to zero.
- **Why it happened.** The gate list put cost at "before the full run", treating the pilot as free because it
  was small. Size is not price: parsing is billed per page from the first page.
- **Fix in this engagement.** Every billable resource now has a stated price source and a zero-cost path
  (digital parser, inline import, no LLM add-on). A budget with alerts at 50, 90 and 100 percent is on the project.
- **Fix in the method.** Cost estimate is a feasibility check (phase 01), computed from the real corpus before
  any import, and every resource-creating step names its price line. See F4 in [04](04-field-feedback.md)
  for the product-side ask.

## What the customer should check

- Billing > Credits: whether new-account or trial credits cover the pilot figure.
- Remaining billable state: none. The bucket from the abandoned GCS-staged path (about 26 MB) and the unused
  layout-parser stores and app were deleted on owner approval on 2026-10-23.
