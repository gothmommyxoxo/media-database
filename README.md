# Media Database

A household media cataloging app: scan a barcode, see if you already own it, and if not, add it
with metadata pulled from free public APIs. Full design in
[specs/media-database-frontend.nlspec.md](specs/media-database-frontend.nlspec.md).

This is a **prototype vertical slice** built test-first per the spec — a real, working path through
auth, the collection, and barcode resolution, rather than all 13 media types and all providers at
once. See "What's built" / "What's not yet built" below.

## Running it

**With Docker (recommended):**

```sh
cp backend/.env.example backend/.env   # fill in provider API keys as you get them; defaults work keyless
docker compose up --build
```

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000

The first account has to be created out-of-band (Section 4 — no public signup) and is always
created as `ADMIN` (13's rationale):

```sh
docker compose exec backend python -m app.seed alice "Alice" "a strong passphrase"
```

Everyone else is created from the admin panel (Section 4.1) once logged in as that account. If
you're upgrading a database that already had users before the role migration landed, every
pre-existing account becomes `MEMBER` by default — promote yourself once:

```sh
docker compose exec backend python -m app.promote_admin alice
```

**Without Docker**, if you don't have MySQL available: the backend also runs against SQLite for
local dev/testing — set `DATABASE_URL=sqlite:///./dev.db` instead of a `mysql+pymysql://...` URL.

```sh
cd backend && python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
DATABASE_URL="sqlite:///./dev.db" .venv/bin/alembic upgrade head
DATABASE_URL="sqlite:///./dev.db" .venv/bin/python -m app.seed alice "Alice" "a strong passphrase"
DATABASE_URL="sqlite:///./dev.db" .venv/bin/uvicorn app.main:app --reload

cd frontend && npm install && npm run dev
```

Camera-based scanning needs a secure context — it works on `localhost`, but if you access the dev
frontend from your phone over plain HTTP on your LAN, the browser will block camera access (this is
the same platform constraint Section 2.2 documents for the real deployment; a real deploy needs the
Caddy/TLS setup in the production Dockerfile target, not the dev one).

## Tests

```sh
cd backend && .venv/bin/pytest tests/ -v   # 102 tests
cd frontend && npm test                     # 40 tests
```

Backend tests run against SQLite, not MySQL — this environment didn't have MySQL/Docker available
while building this, so SQLite stood in for it (see `tests/conftest.py`). Once you have the Docker
stack up, it's worth re-running the integration tests against the real `db` service to catch any
MySQL-specific behavior (particularly around the JSON `attributes` column) that SQLite might paper
over.

## What's built

- Full auth: JWT login/refresh/logout, invite-only household member creation, seed script.
- Collection CRUD: create/list/search/filter/sort/edit/delete, any member can edit any item.
- Barcode resolution end-to-end (`resolve_barcode`, Section 5.3), **all four steps**: general UPC
  lookup, direct-barcode providers, and — new since the first pass — **Step 4's title-search
  fallback** (`app/barcode/category_routing.py`), which routes a general provider's raw
  category string (e.g. "Movies & TV > Blu-ray") toward the category-plausible title-search
  providers when nothing else classified the item. Plus caching, per-provider fault tolerance,
  historical-candidate accumulation across media types, and already-owned detection.
- **All 13 media types now have at least one metadata provider wired up**, 11 providers total:
  - Direct barcode: UPCitemdb (general, Appendix A.1), MusicBrainz + Discogs (CD/VINYL/CASSETTE,
    with the format-mapping logic from 6.2.1), Google Books (MANGA/BOOK/GRAPHIC_NOVEL by ISBN),
    ScanDex (VIDEO_GAME), PriceCharting (VIDEO_GAME, optional/paid, only registered when
    `PRICECHARTING_API_KEY` is set — never instantiated otherwise, per 13's rationale).
  - Title-search fallback (Step 4): TMDb + OMDb (BLU_RAY/DVD/VHS/VCD), IGDB + RAWG (VIDEO_GAME),
    Comic Vine (COMIC_BOOK, and the GRAPHIC_NOVEL ISBN-miss fallback per Appendix A.3), AniList +
    Jikan (MANGA fallback only, not BOOK — 13's rationale).
  - LASERDISC intentionally has no dedicated provider (confirmed no API exists, Appendix A.6) —
    it only ever gets the general UPC lookup's best-effort hit, per spec.
  - IGDB's Twitch OAuth token is cached in-instance and refreshed on expiry rather than fetched
    per request.
- A dedup bug found while wiring Step 4 in: two *unclassified* candidates (`media_type: None`)
  sharing a title — e.g. the UPCitemdb raw stub and a genuine TMDb result for the same movie —
  were being silently collapsed into one, because the original dedup rule treated `None == None`
  as a real match. Fixed in `app/barcode/dedup.py`: the title+media_type dedup rule now only
  applies once media_type is actually known, with a regression test.
- Frontend: login, collection browse/search/filter, item detail, manual add/edit, camera scan
  (zxing) with a manual-barcode fallback, and the resolution screen showing every candidate plus
  owned-match warnings.
- **Admin panel** (Section 4.1/7.4, added after the initial vertical slice): `ADMIN`/`MEMBER` role
  on `User`, with account creation moved from "any member" to admin-only as a direct consequence.
  - **User management**: list/create/edit (rename, promote/demote)/reset-password/delete, all
    admin-gated (403 for members, and the routes don't even render for a non-admin — 9.1).
  - **Last-admin protection**: deleting or demoting the household's only remaining admin is
    rejected with 409, verified live (promote a second admin, then the original delete succeeds).
  - **Deleting a user nulls `MediaItem.added_by`** on their items rather than deleting the items —
    the collection belongs to the household, not whoever happened to scan something first.
  - **Admin record editor** (7.4): a superset edit endpoint exposing fields the member-facing form
    never does (`media_type`, `source`, `external_ids`, `added_by`) — still routed through the same
    Pydantic validation as every other write (changing `media_type` re-validates `attributes`
    against the new type's Appendix B schema), not a raw SQL console (deliberately out of scope,
    Section 12 — see 13's rationale for why).
  - **Barcode cache viewer/purge**: list/inspect/delete `BarcodeCache` entries to unstick a bad
    cached resolution; purging never touches any `MediaItem`.
- Docker Compose + Dockerfiles (dev and production targets) for local running.

This was verified with live, unmocked calls during development, not just against fixtures:
MusicBrainz/UPCitemdb (see the resolution result for UPC `724384960650`, where MusicBrainz's own
data tags that release `Digital Media` rather than `CD`, and the app correctly left it
unclassified — `media_type: null` — per 6.2.1's unmapped-format handling, rather than guessing),
plus AniList, Jikan, and Discogs while wiring up the newer providers (Jikan's live 504 during
testing was a good incidental proof that a real provider outage degrades to "contributed nothing,"
not a crash).

## What's not yet built

Tracked here rather than silently glossed over:

- **ScanDex's exact response schema is an educated guess, not verified against live docs.**
  Research confirmed the endpoint, Bearer-token auth, and that it's a genuine purpose-built
  game-barcode API, but not its field-level JSON shape (no test API key was available to check
  live). If its real shape differs, `app/barcode/providers/scandex.py`'s parsing will raise, which
  degrades to "ScanDex contributed nothing" (6.4) rather than crashing — but it should be verified
  against ScanDex's actual docs before relying on it. Flagged in the file itself.
- **UPC-E → UPC-A expansion** (Section 5.1.1) is not implemented; only the zero-padded-EAN-13 case
  is. UPC-E barcodes pass through unnormalized. Flagged in `app/barcode/normalization.py`.
- **TMDb's attribution requirement** (Appendix A.2 — the "This product uses the TMDB API..."
  notice) is defined as a constant (`TMDB_ATTRIBUTION_NOTICE` in `tmdb.py`) but not yet rendered
  anywhere in the frontend.
- **Per-category attribute editing in the manual entry form** — the backend validates attributes
  per `MediaType` (Appendix B) and the barcode-scan flow can populate them, but the manual-entry
  form doesn't yet expose category-specific fields (e.g. `director`, `issue_number`).
- **Real MySQL integration testing, CI, and the production Caddy/TLS deployment** are defined
  (docker-compose, Dockerfiles) but unexercised — this environment had no Docker/MySQL to run them
  against.
