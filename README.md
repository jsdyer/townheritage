# Town Heritage

An **unlisted Europeana review prototype**: explore how a familiar place appears in cultural collections across Europe. It is prepared to demonstrate real personal-key use before applying for a Europeana project key.

**Do not add this prototype to the CoolCode homepage, catalogue, public sitemap or routine watchdog refresh list.** It is not a production service. The standard CoolCode aggregate page-open counter is enabled, and the ID is registered separately for owner statistics without a public listing. The HTML declares `noindex,nofollow,noarchive`; this discourages indexing but is not access control. Anyone with its review link can view its published data.

## What it does

- Seven configurable place searches: Halifax, Nova Scotia, Vancouver, Langley BC, Canada, Edinburgh and Amsterdam.
- Real images and source metadata from the Europeana Search API, filtered to openly reusable IMAGE records with previews.
- Search within the capture; filter by institution, rights and recorded decade; sort by title or date.
- Open each item to inspect its source, creator, dates, recorded place fields, licence and exact collection query.
- Save a personal collection locally, share a filtered view, and export source citations. Saved records retain the capture date and metadata even if a later capture no longer includes them.
- Explicit sample coverage, empty-result handling, and missing/ambiguous geographic information. Institution/provider country is never presented as an object's location.

## Enable and run the review build

1. Create `jsdyer/townheritage` from `jsdyer/coolcode-tool-template` and publish this source to its `main` branch.
2. Set **Settings → Pages → Source: GitHub Actions**.
3. Add **Settings → Secrets and variables → Actions → New repository secret**:
   - Name: `EUROPEANA_API_KEY`
   - Value: your Europeana personal API key.
4. Open **Actions → Town Heritage · Check and review → Run workflow**, select `main`, and run. Optionally enter one extra keyword query.
5. The first push already attempts a real capture when no saved snapshot exists; manual runs refresh it. The workflow tests, builds and publishes the review site. Use the Pages URL shown by the successful deployment when contacting Europeana.

The key stays in the workflow environment and is sent only to `api.europeana.eu` using the preferred `X-Api-Key` header. It is never embedded in URLs, HTML, JavaScript, downloaded JSON or logs. Sanitized records are committed for reproducibility; raw API responses are never saved (Europeana can echo a key in its response). An explicit output scan rejects the capture if credential material is found. Unexpected redirects are rejected without forwarding credentials.

The first `main` push collects and publishes if no saved capture exists (seven real calls with the default configuration). That sanitized capture is committed back to `main` using the repository workflow token. Subsequent pushes reuse it and publish source changes without spending API quota. **A manual `workflow_dispatch` on `main` makes a new capture.** Pull requests only check and build; they never receive the key or publish. There is no cron, inactivity guard, automatic daily harvesting or Cloudflare proxy. A failed collection prevents deployment and leaves the last successful site available.

## Expand or customize

Edit `config/collections.json`. Every collection needs a unique lowercase `id`, a display `title`, a Europeana `query`, and an honest coverage `note`. Add any valid keyword query, not just the starter towns. The workflow's optional `extra_query` appends a collection for one capture without changing the source configuration.

At most 12 collections and 100 returned rows per collection are supported. Defaults use seven sequential calls, 60 rows each and at least two seconds between calls. These are conservative application limits, **not a claim about Europeana's personal-key quota**. Current Europeana documentation says personal limits have changed and requests must follow fair-use rules; HTTP 429 stops the capture. No automatic retry storm is used.

All API calls request `qf=TYPE:IMAGE`, `reusability=open`, `thumbnail=true`, and `profile=rich`. The collector also requires explicit recognized CC0, Public Domain Mark, CC BY or CC BY-SA URIs and excludes records with mixed or unknown rights. Individual media files can carry different rights: verify the specific image at its source before reuse. At least one validated record must be collected overall; individual empty shelves are allowed. Rights filters and counts come from the actual capture. Metadata is not invented to fill empty dates, images, creators or locations. Collection totals are API match counts, not the number of objects represented by the bounded sample. Identical Europeana IDs are deduplicated across collections.

The prototype searches a **sample**, not the entire live Europeana catalogue. To add a new town, collect it through configuration or the manual workflow. A production version can use a cached, rate-limited server endpoint after a project key is granted. There is no browser key-entry field.

## Local development

Python 3.12+ and Node 24+; no production dependencies.

```bash
node --test tests/*.test.mjs
python3 -m unittest discover -s tests -v
python3 scripts/build.py
python3 -m http.server 8000 --directory dist
```

Without a real capture, the development build shows an honest “Awaiting its first Europeana capture” state. Test fixtures are not published. To collect locally, place the key in your shell environment privately (do not commit it), then run `python3 scripts/collect.py` and `python3 scripts/build.py --require-data`.

Browser checks use the test-only packages in `tests/browser-requirements.txt`; run `python3 tests/browser_smoke.py` after installing Chromium with Playwright. Tests inject synthetic records only into an isolated temporary copy of the build.

## Sources, rights and privacy

- [Europeana Search API documentation](https://europeana.atlassian.net/wiki/spaces/EF/pages/2385739812)
- [API access and personal/project keys](https://europeana.atlassian.net/wiki/spaces/EF/pages/2462351393)
- [Fair-use policy](https://europeana.atlassian.net/wiki/spaces/EF/pages/2704146433)
- [Europeana terms](https://www.europeana.eu/en/rights/terms-of-use)

Each item links to Europeana, the supplying institution where available, and the image's rights statement. Open reuse can still require attribution or share-alike licensing. CC0 metadata does not make every associated image CC0. An `edmPreview` is a preview; the app does not claim it is a high-resolution original.

This independent application is not endorsed by Europeana. Europeana and source institutions retain their branding and attribution. Saved collections use the namespaced `coolcode:townheritage:saved:v1` local-storage key. Images load from their published source hosts; the shared CoolCode counter records aggregate page opens using only this tool ID. Search text, URL query strings and saved collections are not sent. It respects Do Not Track and Global Privacy Control; there is no remote collection database.

## Project-key application notes

Use the completed Pages review link and describe the following only after the workflow has succeeded:

> Town Heritage is a non-commercial cultural discovery prototype that helps visitors explore place-related photographs, prints and objects in European heritage collections. We have tested the Search API with a personal key through a small, manual collection workflow. The prototype demonstrates source attribution, explicit item-level rights, transparent sample coverage, local saved collections and source citations. We plan to add cached visitor searches after project-key approval. The personal key is held server-side in GitHub Actions, never delivered to visitors. The prototype is unlisted and marked noindex during review.

The capture's timestamp, request count, collection queries and source counts appear in the downloadable site data at `data/europeana.json`; they provide reproducible evidence of the tested implementation without revealing the key.

## Release boundary

This repository is intentionally separate from production CoolCode integration. Before a production launch: obtain the project key, review current usage limits, add the agreed caching/rate limits, perform the normal repository/catalogue/Worker/watchdog/sitemap lifecycle (retaining existing visit history), and then remove the prototype noindex restriction. No production registration should occur merely because a review Pages deployment succeeds.

## Credential regression checks

Tests simulate Europeana echoing a fake key in a successful response and in error JSON. The full collect/build path is checked: the fake key must be absent from every published file and captured log. `X-Api-Key` is the only credential transport; raw responses are never retained.
