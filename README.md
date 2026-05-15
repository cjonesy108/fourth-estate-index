# Fourth Estate Index

In 1968, 27 million people watched Walter Cronkite every night to get it straight. He was the most trusted man in America.

That feels like an old-timey notion now. But journalists have more scale than ever — their voices reach further, their influence runs deeper, and the information ecosystem they shape has never mattered more.

What better moment to build transparency into the system?

---

## What This Is

The Fourth Estate Index scores individual journalists against the [SPJ Code of Ethics](https://www.spj.org/ethicscode.asp) — the profession's own published standard. Not a bias tracker. Not a political scorecard. A professional conduct measurement, the same way doctors are measured against medical ethics and lawyers against bar standards.

Every score links to the primary source text that produced it. Every weight is published. Every prompt is open. The methodology is fully transparent before any score appears.

Built and maintained by one person — a former journalist who started this because the question wouldn't leave him alone: *if the SPJ Code is the profession's standard, why isn't anyone measuring against it systematically?*

---

## The Standard

The [SPJ Code of Ethics](https://www.spj.org/ethicscode.asp) has four pillars. The scoring maps directly to them.

| Pillar | Weight | What We Measure |
|---|---|---|
| Seek Truth and Report It | 30% | Headline accuracy, attribution patterns, hedging language |
| Minimize Harm | 20% | Language patterns, sentiment differential across subjects |
| Act Independently | 30% | Financial conflicts (FEC), source diversity, social media advocacy |
| Be Accountable and Transparent | 20% | Corrections frequency, velocity, and severity |

No score is published until minimum data thresholds are met. Dimensions below threshold are marked *insufficient data* — not zero. A zero means the journalist failed the dimension. Insufficient data means we can't say yet.

---

## Current Coverage

**Publication:** The Guardian (free API — [see why](#why-the-guardian-first))

**MVP Cohort:**
| Journalist | Beat | Articles Analyzed |
|---|---|---|
| Marina Hyde | Columnist | 162 |
| Hugo Lowell | Congress / Investigations | 431 |
| Joan E Greve | US Politics | 368 |
| Ed Pilkington | US Correspondent | 283 |
| Lauren Gambino | US Politics / California | 229 |

Scoring is ongoing. Profiles show partial scores honestly while remaining dimensions are built out.

---

## Why The Guardian First

The Guardian provides a free, full-text API through their [Open Platform](https://open-platform.theguardian.com/) program. That makes it the right starting point for a solo project with no institutional budget. This constraint is stated openly because transparency about our own limitations is the same transparency we're asking of journalists.

Additional publications are next. The methodology doesn't change — only the coverage expands.

---

## How It Works

```
Guardian API → article ingestion → Claude analysis → pillar scores → public profile
```

1. **Ingest** — Full article text pulled via Guardian Open Platform API
2. **Analyze** — Claude (claude-sonnet-4-6) evaluates each dimension against a published rubric
3. **Validate** — Every citation is verified verbatim against the stored corpus. No hallucinated sources.
4. **Score** — Weighted pillar scores calculated from dimension results
5. **Publish** — Profile page shows scores, citations, FEC records, corrections log

Every pipeline run is tagged with model version and prompt version. Historical scores are preserved when methodology changes.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+, FastAPI |
| Database | PostgreSQL 15 |
| AI Analysis | Anthropic Claude (claude-sonnet-4-6) |
| Content API | Guardian Open Platform |
| Frontend | Next.js 14, Tailwind CSS |

---

## Running Locally

**Prerequisites:** Python 3.9+, PostgreSQL 15, Node.js 18+

```bash
# Clone
git clone https://github.com/cjonesy108/fourth-estate-index.git
cd fourth-estate-index

# Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Environment variables
cp .env.example .env
# Add your keys to .env:
#   GUARDIAN_API_KEY  — free at https://open-platform.theguardian.com/access/
#   ANTHROPIC_API_KEY — https://console.anthropic.com
#   DATABASE_URL      — postgresql+asyncpg://user@localhost:5432/fourth_estate

# Database
createdb fourth_estate
psql fourth_estate < backend/database/schema.sql

# Backend
PYTHONPATH=. uvicorn backend.api.main:app --reload

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

---

## Methodology

The full scoring rubric is published at [`methodology/rubric.json`](methodology/rubric.json).

The analysis prompts are in [`backend/analysis/`](backend/analysis/). Every prompt used to produce a score is in the codebase — open, readable, disputable.

**Scoring pipeline:**
- `backend/ingestion/` — data collection modules
- `backend/analysis/` — Claude-powered analysis modules
- `backend/scoring/` — pillar and composite score calculation
- `scripts/run_cohort.py` — pipeline orchestration

---

## Appeals & Context

Any journalist scored by this system can submit context or dispute a specific dimension. Context submissions are published unedited alongside the profile. Appeals citing data errors are investigated — if a confirmed error is found, the pipeline re-runs. Scores are not changed by context alone, only by confirmed data errors.

*Appeal submission coming soon.*

---

## Roadmap

- [x] Guardian ingestion pipeline
- [x] Headline fidelity analysis (Pillar 1)
- [x] Attribution patterns analysis (Pillar 1)
- [ ] Corrections ingestion (Pillar 4)
- [ ] FEC financial disclosure ingestion (Pillar 3)
- [ ] Sentiment differential analysis (Pillar 2)
- [ ] Source diversity analysis (Pillar 3)
- [ ] Additional publications
- [ ] Video/podcast transcription pipeline (Whisper)
- [ ] Public appeal submission form

---

## License

Data sources are attributed throughout. Article content is accessed under Guardian Open Platform terms. FEC data is public record. Scoring methodology and code are MIT licensed.

---

*The Fourth Estate Index is an independent project. It is not affiliated with the SPJ or any publication it covers.*
