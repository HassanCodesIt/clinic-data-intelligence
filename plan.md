# plan.md — Task 1: AI Skills & Prompt Engineering Assessment

**Role:** AI Growth & Automation Associate (WFH)
**Submit to:** jobs@gokulinfocare.com (first-come, first-served, no fixed deadline, so speed + quality both matter)
**Project name (proposed):** **GP Atlas AU** — an AI-powered healthcare data-intelligence and outreach copilot

---

## 0. Before you start (5 minutes)

- [ ] Open the job description (https://www.naukri.com/job-listings-221026000604) and confirm you meet the **mandatory requirements**, and that the salary, working days and start time are acceptable. The PDF says these are fixed and non-negotiable.
- [ ] Decide to build it **once, well, and fast**: early submissions are favoured.

---

## 1. Understanding the task

### What they want
One project in **healthcare or technology**, in **one** of five areas (website, digital marketing, web scraping and data intelligence, automation, innovation). AI must play a *meaningful* role, and they want to see something **working**, not an idea.

### What you must submit (all three, or the application is incomplete)

| # | Deliverable | Requirement |
|---|---|---|
| 1 | Video presentation | Handled separately by you (not covered in this plan) |
| 2 | Prompt documentation | Handled separately by you (not covered in this plan) |
| 3 | Project link | GitHub repo and/or live app, accessible to the assessors. You push to GitHub yourself; this plan only prepares the project folder |

### How you'll be scored (and how this plan answers each)

| Criterion | How this plan covers it |
|---|---|
| Practical use of AI tools | AI is used for building (coding assistant) **and** inside the product (Groq gpt-oss-120b) |
| Prompt engineering and iteration | Versioned prompts (v1, v2, v3) with before/after outputs and test cases |
| Creativity and innovation | Natural-language "ask the data" filter, AI field extraction with confidence scores, outreach drafting |
| Problem-solving and technical execution | Rate-limit handling, validation, caching, robots.txt compliance |
| Quality and usefulness | Real public data, search, map, CSV export, deployed link |
| Explaining decisions | Decision log and architecture notes in the README |

---

## 2. Research findings (what I checked, and what it means for the build)

### 2.1 Data source: use an official open dataset, not a scraped directory
- Geoscience Australia publishes a free, queryable **National HealthDirect Health Facilities** service. Layer `0` is `GENERAL_PRACTICE`, with locations of active General Practices drawn from the National Health Services Directory. It supports JSON/GeoJSON queries.
- Endpoint to start from:
  `https://services.ga.gov.au/gis/rest/services/National_HealthDirect_Health_Facilities/MapServer/0`
- Why this beats scraping a commercial directory: **no terms-of-service risk**, stable structured data, and it matches the example in the task ("list of General Practitioners in Australia and their publicly listed practice contact details").
- Caveat: the layer is a snapshot (data extracted March 2024 per its metadata), and **it may not contain email or website fields**. Part 1 checks this. DuckDuckGo search (section 2.5) fills the website gap, and Plan B is in section 11.
- The fuller NHSD datasets on data.gov.au / AURIN need an application form, so skip them.

### 2.2 LLM: Groq + `openai/gpt-oss-120b`
- OpenAI-compatible API, base URL `https://api.groq.com/openai/v1`, so the standard `openai` Python SDK works (or Groq's own SDK).
- Free plan sample limits for gpt-oss-120b (per organisation, check your console's limits page for the authoritative numbers):
  **30 requests/min, 1,000 requests/day, 8,000 tokens/min, 200,000 tokens/day.**
- Design consequences:
  - Keep prompts **short**, truncate scraped HTML to the relevant text, and **cache** every LLM result in SQLite.
  - Add retry with exponential backoff on HTTP 429.
  - Use `reasoning_effort` = `low` for extraction/classification tasks (supported on gpt-oss models) to save tokens.
  - Prefer **JSON-schema structured output**; validate with Pydantic anyway. If strict schema mode fails, fall back to `json_object` plus Pydantic validation.
  - Never loop the LLM over thousands of rows. Use code for bulk work and the LLM only for the "intelligence" steps.

### 2.3 Free tooling (everything below costs ₹0)
FastAPI, Uvicorn, httpx, BeautifulSoup4, Pydantic, SQLite, pytest, Leaflet.js + OpenStreetMap tiles, `ddgs` (DuckDuckGo search), GitHub, VS Code, Groq free tier, Google Drive for backups. Hosting options: Render free web service or Hugging Face Spaces (Docker). Free tiers change, so check current terms on the day. A GitHub repo plus run instructions is an accepted fallback.

### 2.4 Ethics and compliance (put this in the README, it shows maturity)
- Business-level information only (practice name, address, phone, public website). **No patient data. No personal data about individual doctors beyond what the dataset publishes for the practice.**
- Respect `robots.txt` and rate-limit any website fetching; identify with a clear User-Agent.
- Outreach emails are **drafts only**, never auto-sent. Australia has anti-spam rules for commercial electronic messages (Spam Act 2003), so add a note in the README that real campaigns need consent and an unsubscribe mechanism (verify details before any real use).
- LLM never gives medical advice anywhere in this product.
- When submitting, share a **sample dataset** (for example one state or a few hundred rows), not a full national export.

### 2.5 DuckDuckGo search (free, no API key)
- **Package:** `ddgs` (`pip install ddgs`). The older `duckduckgo_search` package was renamed to `ddgs`, so use the new name. Basic use: `DDGS().text("query", max_results=5)`, which returns title, URL and snippet.
- **Important caveat:** it is an **unofficial** library that reads DuckDuckGo's search pages (it can also use other engines such as Bing or Brave as backends). DuckDuckGo may rate-limit or block it, results can occasionally be empty, and it can break if their markup changes. DuckDuckGo's official Instant Answer API is more stable but only returns short answers, not a list of websites, so it is a weak fallback for this use.
- **How the project uses it (small, careful, user-triggered):**
  1. User clicks **"Find website"** on one clinic.
  2. Backend runs **one** DuckDuckGo query such as `"{clinic name} {suburb} {state} GP clinic"` and takes the top 5 results.
  3. Code removes directory and aggregator domains using a denylist (booking sites, health directories, social media, maps) so only the clinic's own site is considered.
  4. The LLM gets only **titles, URLs and snippets** (cheap on tokens) and picks the most likely official website, with a confidence score and a one-line reason. It may answer "none".
  5. The chosen URL is saved as `website_candidate` and the user confirms it before enrichment runs.
- **Rules to keep it safe and reliable:** never loop over the whole dataset, wait 2–3 seconds between searches, cache every query in SQLite, handle empty results and rate-limit errors gracefully, and always allow a manual "paste URL" fallback. Mention in the README that it is for demo-scale use.

---

## 3. The idea

**GP Atlas AU** turns raw public data about Australian GP practices into an **actionable, searchable, AI-enriched intelligence tool** for a healthcare growth team.

**Primary area:** Web Scraping & Data Intelligence.
**Bonus layers:** Automation (an enrichment pipeline) and Growth (lead scoring plus outreach drafts), which is the heart of an "AI Growth & Automation" role.

### The user story
> "I'm a growth associate at a healthtech company. I want to find GP practices in a region, see which have complete contact details, understand what each practice offers, and get a tailored first-touch email draft, in minutes instead of days."

### Feature list

**MVP (must ship):**
1. **Ingest:** pull GP practices from the Geoscience Australia service by state, with pagination, into SQLite, with cleaning and deduplication.
2. **Search and filter UI:** state, postcode/suburb, name, "has phone", "has website"; sortable table; pagination.
3. **Map view:** Leaflet map with clusters or markers for filtered results.
4. **CSV export** of the current filtered view.
5. **AI "Ask the data":** type "GP clinics in Victoria with a phone number near 3000" → LLM converts it to a **validated filter JSON** → code applies the filter (the LLM never writes SQL).
6. **Website finder (DuckDuckGo + AI):** one click finds a clinic's likely official website using DuckDuckGo search, filters out directory sites, and lets the LLM pick and justify the best match; the user confirms it.
7. **AI enrichment (single clinic):** given a clinic website URL, fetch the page (robots-aware), and use gpt-oss-120b to extract structured fields: email, phone, services, bulk-billing mention, languages, opening hours, with a **confidence score** and a `source_snippet` for each field.
8. **AI outreach draft:** generates a short, personalised first-touch email using **only** known fields (it must say "unknown" rather than invent anything).

**Stretch (only if time allows):**
- Lead score (0–100) computed by transparent rules (data completeness, region priority, services found) plus a one-line AI rationale.
- Batch "find website + enrich" queue for a small selected set (for example 10–20 clinics) with a progress bar, respecting Groq and DuckDuckGo limits.
- Dashboard cards: counts by state, % with phone/website/email.
- Docker file for one-command run.

---

## 4. Architecture

```
Browser (HTML + CSS + vanilla JS, Leaflet)
        │  fetch() JSON
        ▼
FastAPI (Python)
 ├── /api/practices       search, filter, paginate, export
 ├── /api/ingest          pull from Geoscience Australia ArcGIS REST
 ├── /api/ask             NL → filter JSON (Groq) → validated → applied
 ├── /api/find-website    clinic → DuckDuckGo search → filter → Groq picks official site
 ├── /api/enrich          URL → fetch → clean text → Groq extraction → store
 ├── /api/outreach        practice → Groq email draft
 └── static files         serves the frontend
        │
        ▼
SQLite (practices, enrichments, llm_cache, prompt_runs)
        │
        └── External: Geoscience Australia REST (data) · DuckDuckGo via ddgs (search) · Groq API (LLM)
```

### Folder structure
```
clinic-data-intelligence/
├── backend/
│   ├── main.py              # FastAPI app, routers, static mount
│   ├── config.py            # env vars (GROQ_API_KEY), constants
│   ├── db.py                # SQLite helpers
│   ├── models.py            # Pydantic schemas (Filter, Enrichment, ...)
│   ├── services/
│   │   ├── ga_ingest.py     # ArcGIS pagination + cleaning
│   │   ├── search.py        # ddgs wrapper: delay, cache, denylist filter, error handling
│   │   ├── fetcher.py       # robots.txt-aware page fetch + text cleaning
│   │   ├── llm.py           # Groq client, retry/backoff, cache, JSON validation
│   │   └── prompts.py       # versioned prompt templates (v1, v2, v3)
│   └── routers/             # one file per endpoint group
├── frontend/
│   ├── index.html
│   ├── styles.css
│   └── app.js
├── tests/                   # pytest: cleaning, filter validation, prompt outputs
├── docs/
│   └── screenshots/
├── sample_data/             # small CSV for reviewers
├── .env.example             # GROQ_API_KEY=
├── requirements.txt
└── README.md                # setup, architecture, decisions, ethics note
```

### Data model (SQLite)
- `practices(id, source_id, name, address, suburb, state, postcode, phone, website, lat, lon, raw_json)`
- `enrichments(practice_id, email, phone, services_json, bulk_billing, languages_json, hours, confidence_json, source_snippets_json, prompt_version, created_at)`
- `website_candidates(practice_id, url, source_query, ddg_title, ddg_snippet, ai_confidence, ai_reason, confirmed, created_at)`
- `search_cache(query_hash, results_json, created_at)`
- `llm_cache(key_hash, prompt_version, response_json, created_at)`
- `prompt_runs(id, task, prompt_version, input_hash, output_ok, notes)`: lets you compare prompt versions during testing

*(Exact fields depend on what the dataset returns: confirm in Part 1.)*

---

## 5. Prompt engineering plan (this is what they grade hardest)

Treat prompts as versioned code. For each task, keep **v1 → v2 → v3** with the failure that caused each revision.

| Task | v1 (naive) | Likely failure | v2/v3 improvement |
|---|---|---|---|
| Filter parsing ("Ask the data") | "Turn this into a filter" | Free text, invented fields | Strict JSON schema, allowed field list, few-shot examples, "return `null` for unknown", Pydantic validation |
| Website picker (DuckDuckGo results) | "Which of these is the clinic's website?" | Picks directories or a different clinic with a similar name | Give name, suburb, state, phone; list results with domains; rule "official site of this exact practice only"; allow `none`; confidence plus reason; code-side check that the URL was in the results |
| Field extraction from clinic page | "Extract contact info" | Hallucinated emails, mixed formats | Role prompt, schema, "only from the text provided", require `source_snippet`, confidence 0–1, reject if snippet isn't in the text |
| Outreach email | "Write a sales email" | Generic, invents facts, too long | Persona, tone, 90-word limit, only provided facts, one clear CTA, "no medical claims", subject line option |
| (Stretch) lead rationale | "Explain the score" | Contradicts the score | Feed score breakdown, ask for one sentence |

**Techniques to show off and name in the README:** role/system prompts, structured output with schema, few-shot examples, negative constraints ("do not invent"), grounding with source snippets, self-check/verification step in code, temperature and reasoning-effort tuning, prompt versioning with test cases.

---

## 6. API sketch

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/ingest?state=VIC` | Pull and store practices for a state |
| GET | `/api/practices` | Query params: `state, postcode, q, has_phone, has_website, page, page_size` |
| GET | `/api/practices/export.csv` | Same filters, CSV download |
| POST | `/api/ask` | `{ "question": "..." }` → `{ filter, results }` |
| POST | `/api/practices/{id}/find-website` | Runs DuckDuckGo + AI pick, returns candidate URL(s) with confidence |
| POST | `/api/practices/{id}/enrich` | `{ "website": "https://..." }` → structured enrichment |
| POST | `/api/practices/{id}/outreach` | Returns email draft |
| GET | `/api/stats` | Counts for dashboard cards |

---

## 7. Frontend plan (plain HTML/CSS/JS)

- **Layout:** top bar with search and "Ask AI" input; left filter panel; main area with table and map tabs; right-side drawer for a clinic's details, a **"Find website"** button (DuckDuckGo + AI, with confirm/reject and a manual paste-URL box), enrichment and outreach draft.
- **JS:** one `app.js` with small functions (`fetchPractices`, `renderTable`, `renderMap`, `askAI`, `findWebsite`, `enrichPractice`). No framework needed.
- **UX details that impress:** loading skeletons, clear "AI-generated, verify before use" badges, confidence chips on extracted fields, copy-to-clipboard on the email draft, empty and error states, mobile-friendly layout.
- Accessibility basics: labels, contrast, keyboard focus.

---

## 8. Build plan in 4 parts

Work through the parts **in order**. Do not start the next part until the "Done when" line of the current one is true. Each part ends with something you can see working, so you always have a fallback to submit.

**Current status**
- [x] Project folder created: `clinic-data-intelligence`
- [x] `.env` file created in the project root with the Groq API key
- [ ] Everything below

### Part 1 — Setup, recon and data pipeline (about 1 day)
**Goal:** a clean project, working secrets, and real GP data stored in SQLite.

**1A. Project setup and secrets**
- [ ] Rename the variable in `.env` to the standard uppercase form: `GROQ_API_KEY=your_key` (no spaces, no quotes). Environment variable names are case-sensitive, and `GROQ_api` will not be found by most libraries and examples.
- [ ] Add `GROQ_MODEL=openai/gpt-oss-120b` on a second line in `.env`.
- [ ] Create `.gitignore` containing at least `.env`, `.venv/`, `__pycache__/`, `*.db`. **Do this before the first `git add`.**
- [ ] Create `.env.example` with the same variable names but fake values (`GROQ_API_KEY=your_key_here`). This one is safe to push.
- [ ] Create a virtual environment and a `requirements.txt` with: `fastapi`, `uvicorn`, `httpx`, `beautifulsoup4`, `pydantic`, `python-dotenv`, `openai`, `ddgs`, `pytest`.
- [ ] Create the folder structure from section 4 (empty files are fine).
- [ ] `backend/config.py`: load `.env` with `python-dotenv` and expose `GROQ_API_KEY` and `GROQ_MODEL`. Fail with a clear message if the key is missing.
- [ ] Never print the key or commit it.

**1B. Recon (1–2 hours)**
- [ ] Open the layer's `?f=pjson` page and list the **field names**.
- [ ] Run a test query: `.../MapServer/0/query?where=1%3D1&outFields=*&f=json&resultRecordCount=5`
- [ ] Note the max records per request; plan `resultOffset` pagination.
- [ ] Check whether website/email fields exist. Decide Plan A or B (section 11).
- [ ] `pip install ddgs` and test one query in a Python shell; confirm it returns results from your network.
- [ ] Make one test call to Groq with `openai/gpt-oss-120b` ("say hello in JSON") to confirm the key works, and check your **limits page**.

**1C. Data pipeline**
- [ ] `db.py`: SQLite schema from section 4.
- [ ] `ga_ingest.py`: paginated fetch, normalise fields (phone formats, state codes, postcodes), dedupe.
- [ ] Run ingestion for one state first, then add others if time allows.
- [ ] Tests for the cleaning functions.

**Done when:** `python -m backend.services.ga_ingest` fills SQLite with clean practice rows, and one test Groq call succeeds.

### Part 2 — Backend API and frontend core (about 1 day)
**Goal:** a working app with no AI yet: search, filter, map, export.

- [ ] `main.py`: FastAPI app, routers, static-file mount for `frontend/`.
- [ ] `GET /api/practices` with filters (state, postcode, name, has phone, has website), pagination and sorting.
- [ ] `GET /api/practices/export.csv` using the same filters.
- [ ] `GET /api/stats` for dashboard cards.
- [ ] `frontend/index.html`, `styles.css`, `app.js`: filter panel, results table, pagination.
- [ ] Leaflet map with markers for the filtered results.
- [ ] Details drawer for one clinic (empty slots for AI features to fill in Part 3).
- [ ] Loading, empty and error states.

**Done when:** you can run `uvicorn backend.main:app --reload`, filter clinics in the browser, see them on the map and download a CSV.

### Part 3 — AI features (about 1–1.5 days)
**Goal:** all the intelligence: this is the part they grade hardest, so keep notes on each prompt version as you go.

- [ ] `llm.py`: Groq client, retry with backoff on 429, SQLite cache, JSON parsing, Pydantic validation.
- [ ] **Ask the data:** `POST /api/ask` with prompt v1 → v3; test with 15–20 sample questions and keep a short pass/fail note for each version.
- [ ] `search.py`: `ddgs` wrapper with 2–3 s delay, SQLite cache, domain denylist, graceful errors.
- [ ] **Website finder:** prompt v1 → v3 and `POST /api/practices/{id}/find-website`; test on 15–20 clinics and note hits and misses.
- [ ] **Enrichment:** `fetcher.py` (robots.txt, timeout, text cleaning, size cap, block private IP ranges), extraction prompt v1 → v3, snippet verification, `POST /api/practices/{id}/enrich`.
- [ ] **Outreach draft:** prompt v1 → v3 and `POST /api/practices/{id}/outreach`.
- [ ] Connect all four features to the details drawer and the "Ask AI" bar; add "AI-generated, verify before use" badges and confidence chips.
- [ ] Pre-enrich 15–20 clinics so the demo is instant.
- [ ] Stretch only if everything above works: lead score, batch queue.

**Done when:** from one clinic's drawer you can find its website, enrich it, and generate an outreach draft, and the "Ask AI" bar returns correct filtered results for your test questions.

### Part 4 — Testing, polish, deploy and submit (about 1 day)
**Goal:** a reviewer-ready project and a complete submission.

- [ ] Run the testing checklist in section 10.
- [ ] Fix error handling: missing API key, Groq 429, DuckDuckGo empty or blocked, website that blocks fetching.
- [ ] Write the README: what it does, screenshots, architecture diagram, setup steps (including creating `.env` from `.env.example`), ethics note, known limitations.
- [ ] Export a small `sample_data/` CSV (one state or a few hundred rows).
- [ ] Double-check that no secret appears anywhere in the project files (search for `gsk_` before you push).
- [ ] Deploy (Render or Hugging Face Spaces), adding `GROQ_API_KEY` in the host's environment-variable settings, **not** in the code. Test the public link in an incognito window. Keep local-run steps as a fallback.
- [ ] Finish your video, prompt document and GitHub push (you are handling these yourself).
- [ ] Send the email (section 12) and verify every link opens without logging in.

**Done when:** the definition of done in section 14 is fully ticked.

---

## 9. Rate-limit and reliability rules (Groq free tier and DuckDuckGo)

1. One LLM call per user action; no background loops over the whole dataset.
2. Cache by `hash(prompt_version + input)`; repeated demo clicks cost zero tokens.
3. Trim page text to roughly 3–4k characters of relevant content (contact, about, services sections).
4. On 429: wait and retry (exponential backoff, max 3 tries), then show a friendly "try again shortly".
5. Show a small "AI calls left today (approx.)" counter for your own safety during the demo.
6. Pre-enrich 15–20 clinics beforehand so any demo is instant and predictable.
7. DuckDuckGo: one search per click, 2–3 s delay, cached results, and pre-resolved websites for the demo clinics.

---

## 10. Testing checklist

- [ ] Ingest is idempotent (running twice doesn't duplicate rows).
- [ ] Filter JSON from the LLM is always validated; bad output returns a clear message.
- [ ] Website picker only returns URLs that were actually in the search results, and can answer "none".
- [ ] A DuckDuckGo failure or empty result shows a friendly message and the manual "paste URL" option.
- [ ] Extraction rejects any value whose `source_snippet` isn't found in the fetched text.
- [ ] Outreach draft never contains a fact missing from the input record.
- [ ] Works with the API key missing (shows a helpful message) and with the network off (cached data still browsable).
- [ ] Public link opens for someone not logged in.

---

## 11. Risks and Plan B

| Risk | Plan B |
|---|---|
| Dataset has no email or website | Use the DuckDuckGo website finder; if it fails, fall back to "paste the clinic's website URL" (still real AI extraction); the demo uses 15–20 clinics whose sites you have pre-checked |
| DuckDuckGo rate-limits, blocks or returns empty results (unofficial library) | Cache every query, 2–3 s delay, one search per click, try a different `ddgs` backend, pre-resolve demo clinics, manual URL paste as fallback |
| Wrong website chosen (similar clinic names, directories) | Domain denylist, LLM must justify, code verifies URL came from results, user confirms before enrichment |
| Groq rate-limited during demo | Cached results plus pre-enriched clinics |
| Strict JSON schema errors on gpt-oss | Fall back to `json_object` plus Pydantic plus one automatic retry with the error message appended |
| Free hosting sleeps or fails | Provide `README` run steps plus screenshots plus the link to your repo |
| Scope creep | Freeze at the MVP list in section 3; stretch goals only after a deployed MVP exists |
| Other candidates submit first | Ship the MVP quickly; polish after the first email only if the rules allow it (don't resubmit unless you tell them) |

---

## 12. Submission email template

**To:** jobs@gokulinfocare.com
**Subject:** Task 1 Submission – AI Growth & Automation Associate – Hassan Huda

```
Dear Hiring Team,

Please find my Task 1 submission for the AI Growth & Automation Associate role.

Project: GP Atlas AU – AI-powered healthcare data intelligence and outreach copilot
(Web Scraping & Data Intelligence, with Automation and Growth layers)

1. Video presentation: <your Google Drive link>
2. Prompt documentation: <your Google Doc / PDF link>
3. Project link: <your GitHub repo> | Live demo: <URL>

Tools: FastAPI, HTML/CSS/JS, SQLite, Groq (openai/gpt-oss-120b), Leaflet. All free tools.
All links are set to "Anyone with the link can view".

Thank you for your time.
Regards,
Hassan Huda
GitHub: github.com/HassanCodesIt | Portfolio: hassan-huda-portfolio.vercel.app
```

Before sending: open every link in an incognito window.

---

## 13. Starter prompts for your coding AI

1. *"Act as a senior FastAPI engineer. Scaffold the project structure below, with config via environment variables, SQLite helpers and a static-file mount. Don't add features I haven't listed."* (paste section 4)
2. *"Here is the JSON response from this ArcGIS REST layer: <paste>. Write an ingestion service with `resultOffset` pagination, field normalisation, deduplication and pytest tests."*
3. *"Build the `/api/practices` endpoint with the filters in this table, pagination and CSV export. Return typed Pydantic responses."*
4. *"Write `llm.py` for the Groq OpenAI-compatible API using model `openai/gpt-oss-120b`: retry with backoff on 429, SQLite caching by prompt version plus input hash, JSON-schema output with Pydantic validation and a fallback mode."*
5. *"Write an extraction prompt that returns only data present in the supplied text, each field with a `source_snippet` and a 0–1 confidence. Then write a verifier that rejects values whose snippet isn't in the text."*
6. *"Write `search.py` using the `ddgs` package: one query per call, 2–3 second delay, SQLite cache, a denylist of directory, booking and social domains, and graceful handling of rate-limit and empty results. Then write a prompt that picks the official website from the results or returns none."*
7. *"Build a vanilla JS frontend (no framework) with a filter panel, results table, Leaflet map and a details drawer. Keep it accessible and responsive."*
8. *"Review my code for security issues (key leakage, SSRF in the URL fetcher, unvalidated input) and suggest fixes."* (the fetcher should block private/internal IP ranges)

---

## 14. Definition of done

- [ ] Live or locally runnable app that demonstrably uses Groq gpt-oss-120b
- [ ] Project folder ready for you to push: README, `.env.example`, sample data, no secrets in any file
- [ ] Email sent with all three deliverables and verified links