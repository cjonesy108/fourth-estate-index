# Fourth Estate Index — browser extension

Shows two numbers on a news article:

1. **This article** — published only after that URL is ingested and an article snapshot exists. Pending is not a zero.
2. **Journalist** — corpus composite for the byline when that person is in the directory (example: Jaclyn Diaz on NPR).

## Load unpacked (Chrome / Edge)

1. Merge or check out `feature/browser-extension`.
2. Open `chrome://extensions` → Developer mode → Load unpacked → select this `extension/` folder.
3. Open https://www.npr.org/2026/08/31/nx-s1-5947259/sheriffs-lawsuits-state-ice-cooperation-bans
4. A cream FEI chip appears lower-right. Click it.

The chip talks to `https://fourth-estate-index.vercel.app/ext/lookup`. After this branch is on Vercel, Jaclyn Diaz resolves as a listed NPR reporter. Her composite stays pending until an NPR corpus is scored.

## API

`GET /ext/lookup?url=&title=&authors=&host=`

Directory match always works on Vercel. Postgres article/journalist scores overlay when `NEXT_PUBLIC_API_URL` points at the FastAPI box.

On that box after merge:

```bash
psql "$DATABASE_URL" -f backend/database/migrations/003_article_lookup.sql
```

## What this does not do

- It does not log into paywalls or send article body to a model from the page.
- It does not invent an article grade from one headline.
- Pillars 3 and 4 are journalist-level (FEC, corrections). They do not appear as an article snapshot.
