# 04. Field feedback to Product and Engineering

Engagement phase: liaison to core Product and Engineering. Each item is something hit in delivery, with the
evidence, the customer impact and the feature request it turns into.

| # | Finding | Evidence | Customer impact | Feature request |
|---|---|---|---|---|
| F1 | Docs disagree on Markdown | The data preparation page lists Markdown as a supported format. The v1 `Document.Content` reference does not list `text/markdown` as a mimeType | A team following the prose page builds a Markdown pipeline, then has to convert everything | Either accept `text/markdown` in `Content.mimeType`, or remove Markdown from the prose list and say to send HTML |
| F2 | Docs disagree on the default search result mode | The search guide says the default is chunks when chunking is on, and calls `searchResultMode` a v1alpha preview. The v1 `ContentSearchSpec` reference lists it on v1 and says it defaults to DOCUMENTS | Silent behaviour difference between API versions; results come back as documents when chunks were expected | One stated default per API version, on both pages |
| F3 | Chunking is only available with the paid layout parser | "The layout parser is available only when using document chunking for RAG"; chunking needs layout parsing; the digital parser is free | For a code or text corpus, chunking costs USD 10 per 1,000 x 3,000 characters. Here: about USD 504 for 204 repos, which put chunked RAG out of reach of a zero budget | Plain text-boundary chunking on the free digital parser, priced separately from layout detection |
| F4 | No pre-import cost estimate | Nothing in the import path reports pages or projected parsing cost | The pilot import was billed before the cost was known | A dry-run or `estimate` flag on `documents:import` that returns page count and projected cost |
| F5 | Misleading 403 on a brand-new project | Project owner got `Permission 'discoveryengine.dataStores.list' denied ... (or it may not exist)` minutes after project creation; succeeded on retry | Looks like a missing role, sends people to IAM for a propagation delay | Distinguish "IAM still propagating" from "denied", or document the expected delay in the quickstart |
| F6 | Data preparation page references a missing table | "The following table lists the file size limits of each file type" with no table rendered | 200 MB is the only documented limit; per-format limits are unknown | Restore the table |
| F7 | Data store to app binding is permanent and one-to-one | "A data store can be attached to only one app and can't be removed from the app later" | Trying a second app configuration means re-importing into a new data store | Allow detaching, or attaching a store to more than one app |
| F8 | Product rename mid-flight | Vertex AI Search is now Agent Search; console says AI Applications; API is still Discovery Engine | Three names for one thing in one session; search and support conversations miss each other | A single names table at the top of the overview page |
| F9 | Pricing page and API disagree on core generative answers | Pricing: Enterprise "includes core Generative Answers (AI Mode). Provide answers, summaries and follow ups at no additional cost". API: the answer method returns `FAILED_PRECONDITION: This feature is only available when Large Language Model add-on is enabled` on an Enterprise app without the add-on | A customer budgets for free answers, then finds the answer method needs the billed add-on | State on the pricing page which methods core answers cover (search summary) and which need the add-on (answer method) |
| F10 | Summary responses flag a skip while returning a summary | Search with `summarySpec` returns `summarySkippedReasons: ["LLM_ADDON_NOT_ENABLED"]` and a complete `summaryText` in the same response | Client code that trusts the skip reason discards a valid answer | Only report a skip reason when the summary was actually skipped |
| F11 | Citation metadata is intermittent | The same query returned `citationMetadata.citations` on 3 of 5 calls; inline markers in `summaryText` mix formats (`[3:43, 6]`, `[1:3:43, 8:2:00]`) | Answers cannot be shown as cited without retries | Always return citation metadata when `includeCitations` is set, and keep inline markers in one documented format |

Integration finding, not a Google defect, recorded so the next team does not repeat it:

| # | Finding | Evidence | Fix |
|---|---|---|---|
| I1 | Secret scanners miss credentials after HTML escaping | gitleaks found 47 findings in the raw pilot text and 15 in the same content as HTML | Scan the unescaped text. Scan both copies and require both clean |
