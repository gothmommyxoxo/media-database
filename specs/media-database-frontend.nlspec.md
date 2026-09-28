# Media Database: Web Frontend and Barcode Catalog Service

This spec defines a web application that lets a household catalog a personal collection of manga,
books, comic books, graphic novels, video games, Blu-rays, DVDs, VHS tapes, VCDs, laserdiscs, CDs,
vinyl records, and cassette tapes in a MySQL database, so that members can scan an item's barcode with a phone
camera while shopping and immediately see whether it is already owned. It is for a coding agent
implementing the system end-to-end: frontend, backend API, database schema, and integrations with
free third-party metadata APIs.

## Table of Contents

1. [Overview and Goals](#1-overview-and-goals)
2. [Architecture](#2-architecture)
3. [Data Model](#3-data-model)
4. [Authentication and Access Control](#4-authentication-and-access-control)
5. [Barcode Scanning and Resolution (Critical)](#5-barcode-scanning-and-resolution-critical)
6. [External Metadata Providers](#6-external-metadata-providers)
7. [Collection Management](#7-collection-management)
8. [REST API Surface](#8-rest-api-surface)
9. [Frontend Application](#9-frontend-application)
10. [Testing Strategy (Critical)](#10-testing-strategy-critical)
11. [Deployment and Operations](#11-deployment-and-operations)
12. [Out of Scope](#12-out-of-scope)
13. [Design Decision Rationale](#13-design-decision-rationale)
14. [Definition of Done](#14-definition-of-done)
15. [Appendix A: External API Catalog](#appendix-a-external-api-catalog)
16. [Appendix B: Category Attribute Field Reference](#appendix-b-category-attribute-field-reference)

---

## 1. Overview and Goals

### 1.1 What This Is

A household media cataloging application. Members log in, browse and search what they own, and
add new items either by typing details in or by scanning a barcode with a phone camera. The system
resolves a scanned barcode against free public metadata APIs, and — because the same UPC/EAN has
sometimes been reused across unrelated releases — presents every plausible match so the member can
pick the right one, rather than silently guessing.

### 1.2 Problem Statement

Today the collection exists only in the members' memory. When standing in a store or browsing
online, there is no reliable way to check whether a manga volume, Blu-ray, or CD is already owned,
which leads to accidental duplicate purchases. Manually maintaining a spreadsheet does not scale to
thirteen different media categories with different identifying attributes, and does not work from a
phone in a store aisle. This spec defines a web application, backed by a MySQL database, that scans
a barcode, looks up what it identifies across category-appropriate free APIs, and tells the member
immediately whether they already own it.

### 1.3 Design Principles

**Scan-first, but never scan-only.** Barcode scanning is the primary entry path for adding items,
but every field it can populate must also be enterable and editable by hand. Laserdiscs in
particular have no barcode-lookup API at all (see Section 6), so manual entry is a first-class
path, not a degraded one.

**Show every candidate, never guess silently.** A barcode is not a stable, unique identifier for a
specific release — reissues, regional variants, and unrelated products have collided on the same
UPC/EAN in the wild. When a scan resolves to more than one plausible item, the system always shows
the member every candidate it found and lets them choose, rather than picking the "best" match
automatically.

**Cache external lookups aggressively.** The free tier of nearly every metadata API used here is
rate-limited (see Appendix A), and the single most common scan is a repeat scan of something
already owned. Barcode resolution results are cached server-side and reused, both to stay under
rate limits and to accumulate the candidate history a reused barcode needs (see Section 5.3).

**Tests before implementation.** Every feature in this spec is built test-first: a failing test
that encodes the requirement is written before the code that satisfies it. This applies with
particular force to barcode resolution (Section 5), which depends on unreliable third-party
services and must be verifiable without burning real API quota (see Section 10).

### 1.4 Layering and Scope

This spec defines: the data model for the collection and its household accounts, the barcode
capture and resolution pipeline, the routing logic to external metadata providers, the REST API
surface, the frontend views, the testing approach, and the deployment topology.

This spec does NOT define: the internal implementation details of third-party APIs it depends on
(only their externally observable contract, see Appendix A), or a native mobile app (the frontend
is a browser-based Progressive Web App — see Section 9.2).

---

## 2. Architecture

### 2.1 System Layers

```
+-------------------------------------------------------------+
|  Browser (phone or desktop)                                 |
|  React + TypeScript PWA                                     |
|    - Camera capture + barcode decode (client-side)          |
|    - Browse / search / add / edit UI                        |
+-------------------------------------|-------------------------+
                                       | HTTPS (JSON REST)
+-------------------------------------v-------------------------+
|  Backend API                                                  |
|  FastAPI (Python)                                              |
|    - Auth (household accounts, JWT)                            |
|    - Collection CRUD                                           |
|    - Barcode resolution orchestration + caching                |
|    - Outbound proxy to external metadata providers             |
+-----------------|--------------------------------|------------+
                   |                                | HTTPS
        +----------v----------+           +---------v-----------+
        |  MySQL 8             |           |  External metadata  |
        |  collection, users,  |           |  providers           |
        |  barcode cache        |           |  (Appendix A)        |
        +-----------------------+           +----------------------+
```

**Behavior:**
- The browser never calls external metadata providers directly; all outbound provider requests are
  proxied through the backend so provider API keys are never exposed to the client and so
  server-side caching (Section 6.3) applies uniformly.
- The browser never connects to MySQL directly; all persistence goes through the backend API.

### 2.2 Deployment Topology

The application is cloud-hosted and reachable over the public internet (members may check the
collection while shopping, not only at home). It runs as three containers behind a reverse proxy
that terminates TLS: `frontend` (static build), `backend` (FastAPI), `db` (MySQL). See Section 11
for the full deployment definition.

**HTTPS is a hard requirement, not a preference (Critical).** Browsers only grant camera access
(`getUserMedia`) on a secure context (`https://` or `localhost`). Because this app is accessed over
the open internet rather than only `localhost`, barcode scanning will not function at all without
valid TLS in every environment members actually use.

### 2.3 Technology Stack

| Layer | Choice | Rationale |
|---|---|---|
| Backend framework | FastAPI (Python 3.12) | Native async for proxying external APIs, Pydantic models double as validation and OpenAPI schema, first-class `TestClient` for TDD |
| ORM / migrations | SQLAlchemy 2.0 + Alembic | Typed models over MySQL, versioned schema migrations |
| Backend HTTP client | `httpx` (async) | Used for all outbound provider calls; swappable for a fake transport in tests |
| Backend test tools | `pytest`, `pytest-asyncio`, `respx` | `respx` mocks `httpx` calls against recorded provider fixtures (Section 10.3) |
| Auth | JWT access + refresh tokens, `passlib`/bcrypt for password hashing | Stateless session validation, standard password storage |
| Database | MySQL 8.0 | Required by the user; JSON column type (used in Section 3.2) is mature as of 8.0 |
| Frontend framework | React 18 + TypeScript, built with Vite | PWA plugin ecosystem, fast dev/test loop |
| Frontend data layer | TanStack Query | Caching/retry for REST calls, minimizes duplicate network requests from the UI |
| Barcode decoding | `@zxing/browser` (client-side, in-browser) | Pure JS/WASM, no native app required, decodes UPC-A/UPC-E/EAN-13/EAN-8/Code128 from a live camera stream |
| Frontend test tools | `vitest`, `React Testing Library`, `Playwright` | Unit/component tests and end-to-end browser tests (Section 10.2) |
| Reverse proxy / TLS | Caddy | Automatic HTTPS via Let's Encrypt, satisfies Section 2.2's hard requirement with minimal config |

---

## 3. Data Model

### 3.1 MediaType

```
ENUM MediaType:
    MANGA        -- Manga volumes
    BOOK         -- Standalone books (novels, non-fiction, etc.)
    COMIC_BOOK   -- Single-issue comic books / floppies
    GRAPHIC_NOVEL -- Bound, ISBN-carrying collected editions (trades, omnibuses, OGNs)
    VIDEO_GAME   -- Console or PC games
    BLU_RAY      -- Film/TV releases on Blu-ray
    DVD          -- Film/TV releases on DVD
    VHS          -- Film/TV releases on VHS tape
    VCD          -- Film/TV releases on Video CD
    LASERDISC    -- Film/TV releases on Laserdisc
    CD           -- Music releases on compact disc
    VINYL        -- Music releases on vinyl record
    CASSETTE     -- Music releases on cassette tape
```

**Anime is not a separate `MediaType`.** Anime is a genre, not a physical format: an anime title is
catalogued under whichever of `BLU_RAY`, `DVD`, `VHS`, `VCD`, or `LASERDISC` it was actually
released on, exactly like any other film/TV release, and resolves through the same provider path
(Section 6.2). There is no anime-specific routing or attribute schema.

| MediaType | Barcode-lookup coverage | Primary metadata providers |
|---|---|---|
| `MANGA` | ISBN-based, good | Google Books (Appendix A.3) |
| `BOOK` | ISBN-based, good | Google Books (Appendix A.3) |
| `COMIC_BOOK` | Partial — many issues carry a UPC, but no provider searches by it directly | General UPC lookup, then Comic Vine title/issue search (Appendix A.7) |
| `GRAPHIC_NOVEL` | ISBN-based, good — collected editions are sold like books, unlike single issues | Google Books (Appendix A.3), Comic Vine title/volume search as fallback (Appendix A.7) |
| `VIDEO_GAME` | Partial, direct — ScanDex covers a meaningful slice directly, general UPC lookup catches more; both feed IGDB/RAWG for canonical metadata | ScanDex, general UPC providers -> IGDB, RAWG (Appendix A.4) |
| `BLU_RAY` / `DVD` | Indirect (general UPC lookup, then title search) | TMDb, OMDb (Appendix A.2) |
| `VHS` | Indirect; most commercial VHS releases were retail-barcoded, coverage close to DVD | TMDb, OMDb (Appendix A.2) |
| `VCD` | Indirect and less reliable — many VCDs were regional/import releases with inconsistent barcoding | TMDb, OMDb (Appendix A.2) |
| `LASERDISC` | Sparse and incidental — no dedicated laserdisc API exists, but general UPC lookup has real, crowdsourced hits for discs (mostly US, post-UPC-adoption) that happen to be in its database | General UPC providers only, best-effort (Appendix A.1, A.6); manual entry remains the primary path (Section 5.5) |
| `CD` | Good, direct barcode search | MusicBrainz, Discogs (Appendix A.5) |
| `VINYL` | Good, direct barcode search | MusicBrainz, Discogs (Appendix A.5) |
| `CASSETTE` | Good for retail-era tapes, direct barcode search; poor for pre-UPC vintage tapes | MusicBrainz, Discogs (Appendix A.5) |

### 3.2 MediaItem

```
RECORD MediaItem:
    id               : Integer                     -- primary key
    media_type       : MediaType
    title            : String
    subtitle         : String | None                -- e.g. series/volume qualifier
    barcode          : String | None                -- UPC/EAN/ISBN as scanned; None for manual entries with no code
    format           : String | None                -- e.g. "Steelbook", "Picture Disc", "Special Edition"
    condition        : String | None                -- free text, e.g. "Sealed", "Used - Good"
    notes            : String | None
    cover_image_url  : String | None
    attributes       : Map<String, Any>              -- category-specific fields, see Appendix B
    external_ids     : Map<String, String>            -- provider name -> provider's item id
    source           : ItemSource                    -- SCANNED | MANUAL, see 3.2.1
    added_by         : Integer | None                 -- User.id; None if that account was later deleted (4.1)
    created_at       : DateTime
    updated_at       : DateTime
```

**Attribute storage.** `attributes` is stored as a MySQL `JSON` column rather than category-specific
tables (see Section 13 for rationale). The backend validates its shape per `media_type` against the
Pydantic schemas defined in Appendix B before persisting; the database itself does not enforce the
per-category shape.

**Barcode uniqueness is deliberately not enforced.** Two distinct owned items (e.g. two different
manga volumes affected by a barcode collision, see Section 5.3) may legitimately share the same
`barcode` value. Uniqueness is not a database constraint on this column.

#### 3.2.1 ItemSource

```
ENUM ItemSource:
    SCANNED   -- created from a resolved barcode candidate
    MANUAL    -- created by hand, with or without a barcode
```

### 3.3 User

```
ENUM Role:
    ADMIN    -- Section 4.1: manages accounts, edits any record's full field set (7.4)
    MEMBER   -- Standard access: full collection CRUD (Section 7); cannot manage users or edit
             -- records outside the normal item form's field set

RECORD User:
    id             : Integer
    username       : String                -- unique, used for login
    display_name   : String
    password_hash  : String
    role           : Role = MEMBER
    created_at     : DateTime
```

**Household accounts.** Every household member who uses the app has their own account so that
`MediaItem.added_by` reflects who actually catalogued an item (see Section 4). Every account, admin
or member, has full read/write access to the shared collection (Section 7) — `Role` only gates user
management and the admin record editor (Section 4.1, 7.4), not ordinary browsing/cataloguing.

### 3.4 BarcodeCandidate and BarcodeCache

```
RECORD BarcodeCandidate:
    source_provider   : String              -- e.g. "musicbrainz", "google_books", "tmdb"
    media_type        : MediaType | None    -- provider's best guess; None if ambiguous
    title             : String
    subtitle          : String | None
    external_id       : String | None       -- provider's own identifier for this item
    external_url      : String | None       -- link to the provider's page for this item, if any
    cover_image_url    : String | None
    raw_attributes     : Map<String, Any>    -- provider-native fields, mapped toward Appendix B shape where possible
```

```
RECORD BarcodeCache:
    barcode          : String                     -- primary key
    candidates       : List<BarcodeCandidate>
    last_refreshed_at: DateTime
    refresh_count    : Integer = 0                 -- number of times resolution has been re-run for this barcode
```

**Behavior:** `BarcodeCache` is the accumulated, deduplicated set of every candidate ever resolved
for a given barcode across all members and all time — including across different media types. This
is the mechanism that satisfies the requirement that a reused barcode shows all known options, not
just the most recent resolution (see Section 5.3).

---

## 4. Authentication and Access Control

The application requires a login; there is no anonymous access. Sessions use JWT access tokens
(short-lived, 15 minutes) plus refresh tokens (long-lived, 30 days, stored as an `HttpOnly` cookie).

**Account creation is invite-only, not self-service.** There is no public registration page. The
first account is created by a one-time seed script at deploy time (Section 11) and is always
`ADMIN` (whoever can run a script on the server already has full trust — see Section 13). From then
on, only an `ADMIN` can create, edit, or delete accounts (Section 4.1) — this is a change from an
earlier draft of this spec, where any member could create accounts; seeing "manage other people's
accounts" and "manage the shared collection" as the same trust level stopped holding once an admin
tier existed at all.

```
INTERFACE AuthService:
    FUNCTION login(username, password) -> TokenPair | AuthError
    FUNCTION refresh(refresh_token) -> TokenPair | AuthError
    FUNCTION logout(refresh_token)
    FUNCTION get_current_user(access_token) -> User

    -- Capability metadata
    access_token_ttl_minutes  : Integer = 15
    refresh_token_ttl_days    : Integer = 30
```

| Error | Example | Recovery |
|---|---|---|
| Invalid credentials | Wrong password on login | Return 401, generic "invalid username or password" message (do not reveal which field was wrong) |
| Expired access token | Request made after 15 minutes | Frontend transparently calls `refresh`; if refresh also fails, redirect to login |
| Expired/revoked refresh token | Refresh token past 30 days or after `logout` | Return 401, frontend redirects to login |
| Non-admin calls an admin-only endpoint | A `MEMBER` calls `create_user` (4.1) | Return 403, frontend hides admin entry points from non-admins entirely (9.1) so this is a defense-in-depth check, not the primary UX |

### 4.1 Admin Role and User Management

Every mutating user-management action requires the caller to be `ADMIN`; `get_current_user` (above)
is how the frontend learns its own role to decide whether to show admin UI at all (9.1).

```
INTERFACE AdminUserService:
    FUNCTION list_users(admin) -> List<User>
    FUNCTION create_user(admin, username, display_name, password, role) -> User
    FUNCTION update_user(admin, user_id, display_name, username, role) -> User
    FUNCTION reset_password(admin, user_id, new_password)
    FUNCTION delete_user(admin, user_id)
```

**Deleting a user does not delete their items.** A household's collection is shared, not personally
owned (Section 7.2), so `delete_user` sets `MediaItem.added_by = None` on every item that account
added, then deletes the account — it does not cascade-delete items (see Section 13 for rationale).

**An admin cannot delete or demote their own account** if it is the only remaining `ADMIN` — the
household must always have at least one admin capable of managing accounts. This is the only
business-rule validation `delete_user`/`update_user` perform beyond the error table below.

| Error | Example | Recovery |
|---|---|---|
| Duplicate username | `create_user`/`update_user` with an existing username | Return 409, surface inline field error in the UI |
| Last-admin protection | Deleting or demoting the only `ADMIN` account | Return 409 with a message explaining why; no partial effect |
| Self-lockout attempt not otherwise covered | Any other admin action that would leave zero admins | Return 409, same as above |

---

## 5. Barcode Scanning and Resolution (Critical)

This is the core feature: turning a decoded barcode into a set of candidate items the member can
confidently choose from, while flagging anything already owned.

### 5.1 Client-Side Capture

The frontend requests camera access and decodes frames locally using `@zxing/browser` against a
live `<video>` stream — the raw barcode string is what reaches the backend, no image data is
uploaded. Supported symbologies: UPC-A, UPC-E, EAN-13 (which subsumes ISBN-13), EAN-8, Code128.

```
FUNCTION on_barcode_decoded(raw_value, symbology):
    normalized = normalize_barcode(raw_value, symbology)
    -- Step 1: normalize UPC-E to UPC-A / strip whitespace, per Section 5.1.1
    navigate_to_resolution_screen(normalized)
```

#### 5.1.1 Barcode Normalization

UPC-E codes are expanded to their UPC-A equivalent, and any codes that are EAN-13 with a leading
`0` are treated as equivalent to the UPC-A form without the leading zero, so that the same physical
product is not cached under two different string keys. ISBN-13 values (EAN-13 with prefix `978` or
`979`) are passed through unchanged, since Google Books expects the ISBN-13 form directly.

### 5.2 Provider Interface

```
INTERFACE MetadataProvider:
    FUNCTION supports_barcode_lookup() -> Boolean
    FUNCTION lookup_by_barcode(barcode) -> List<BarcodeCandidate>   -- only if supports_barcode_lookup()
    FUNCTION search_by_title(title, media_type) -> List<BarcodeCandidate>

    -- Capability metadata
    provider_name       : String
    covers_media_types  : List<MediaType>
    requires_api_key     : Boolean
    rate_limit_per_second: Float | None
```

Each provider in Appendix A implements this interface. Providers that cannot look up by barcode
(most of them — see Appendix A) implement `supports_barcode_lookup() -> False` and only
`search_by_title`; the resolution algorithm (5.3) skips straight to title search for those.

**Side-effect constraint:** provider implementations must not write to `BarcodeCache` themselves —
only the orchestrating resolution function (5.3) writes to the cache, so caching policy stays in
one place.

### 5.3 Resolution Algorithm

```
FUNCTION resolve_barcode(barcode, requesting_user) -> ResolutionResult:
    normalized = normalize_barcode(barcode)

    -- Step 1: serve from cache if fresh
    cached = BarcodeCache.get(normalized)
    IF cached is not None AND cached.last_refreshed_at > NOW() - CACHE_TTL:
        candidates = cached.candidates
    ELSE:
        candidates = fetch_fresh_candidates(normalized)
        BarcodeCache.upsert(normalized, merge(cached.candidates IF cached ELSE [], candidates))

    -- Step 2: cross-check against the household's existing collection
    owned_matches = MediaItem.find_all(barcode == normalized)

    -- Step 3: nothing found anywhere -- direct the member to manual entry
    IF candidates is empty AND owned_matches is empty:
        RETURN ResolutionResult(candidates=[], owned_matches=[], requires_manual_entry=True)

    RETURN ResolutionResult(candidates=candidates, owned_matches=owned_matches, requires_manual_entry=False)


FUNCTION fetch_fresh_candidates(barcode) -> List<BarcodeCandidate>:
    results = []

    -- Step 1: general UPC/EAN lookup providers first, to get a raw product title/category guess
    FOR EACH provider IN GENERAL_BARCODE_PROVIDERS:      -- Appendix A.1
        TRY:
            results.append_all(provider.lookup_by_barcode(barcode))
        CATCH ProviderError:
            CONTINUE                                     -- Section 6.4: a single provider failure never blocks resolution

    -- Step 2: providers that support direct barcode search run in parallel regardless of Step 1's result
    FOR EACH provider IN MetadataProvider.all() WHERE provider.supports_barcode_lookup():
        TRY:
            candidates_from_provider = provider.lookup_by_barcode(barcode)
            IF provider.provider_name IN ["musicbrainz", "discogs"]:
                candidates_from_provider = map_music_format(candidates_from_provider)   -- Section 6.2.1
            results.append_all(candidates_from_provider)
        CATCH ProviderError:
            CONTINUE

    -- Step 3: if the barcode is an ISBN-13 (prefix 978/979), always query Google Books directly
    IF is_isbn13(barcode):
        TRY:
            results.append_all(GoogleBooksProvider.lookup_by_barcode(barcode))
        CATCH ProviderError:
            PASS

    -- Step 4: if Step 1 produced a raw title but no category-specific provider matched it directly,
    --         use that raw title to run a best-effort title search across providers whose
    --         covers_media_types looks plausible given the raw category hint
    IF results has no candidates with media_type set AND a raw title was found in Step 1:
        FOR EACH provider IN plausible_providers_for(raw_category_hint):
            TRY:
                results.append_all(provider.search_by_title(raw_title, media_type=None))
            CATCH ProviderError:
                CONTINUE

    RETURN deduplicate(results)                          -- Section 5.3.1
```

**Behavior:**
- Every provider call is independently fault-tolerant: one provider timing out or returning an
  error never prevents the others from contributing candidates (Section 6.4).
- The function always returns whatever the union of successful providers found, plus any items the
  household already owns under that exact barcode — both facts are shown to the member together.
- A barcode that has previously resolved to candidates across *different* media types (e.g. a UPC
  reused between a DVD release and an unrelated board game) keeps every historical candidate in
  `BarcodeCache`, so the member always sees the full set, not just this scan's fresh results.

#### 5.3.1 Deduplication

```
FUNCTION deduplicate(candidates) -> List<BarcodeCandidate>:
    -- Two candidates are the same item if they share a provider AND external_id,
    -- or if they share a normalized title AND media_type across different providers.
    ...
```

| Config key | Type | Default | Description |
|---|---|---|---|
| `CACHE_TTL` | Duration | `30 days` | How long a cached `BarcodeCache` entry is served without re-querying providers |
| `PROVIDER_TIMEOUT_MS` | Integer | `4000` | Per-provider request timeout before it's treated as a failure (Section 6.4) |

### 5.4 Duplicate / Already-Owned Detection

When `ResolutionResult.owned_matches` is non-empty, the frontend shows those items first and most
prominently, labeled "You already own this," before the full candidate list. This is a warning, not
a block: a member may deliberately own two copies (e.g. a backup, or a gift), so adding a new item
is always still allowed after the warning is shown.

### 5.5 Manual Fallback

When `requires_manual_entry` is `True` (nothing found anywhere — the common case for laserdiscs,
though not universal; see Appendix A.6), the frontend routes the member to a manual entry form
pre-filled only with the scanned barcode, with every other field editable free text. If a general
UPC provider did return a raw title for a laserdisc barcode (Appendix A.6), `requires_manual_entry`
is `False` and that candidate is shown with `media_type = None` — the member confirms it's a
`LASERDISC` and fills in the rest by hand, since no provider can populate laserdisc-specific
attributes (Appendix B). Manual entry is also reachable directly from the collection view without
scanning at all, for items with no barcode (e.g. imports, doujinshi, homebrew, or pre-barcode-era
cassettes).

---

## 6. External Metadata Providers

### 6.1 Provider Catalog

The full catalog of providers, endpoints, auth requirements, and rate limits is normative in
**Appendix A**. This section defines how providers are selected and combined at runtime.

### 6.2 Media-Type-to-Provider Routing

| MediaType | Providers queried (in order used by 5.3) | Supports direct barcode lookup |
|---|---|---|
| `CD`, `VINYL`, `CASSETTE` | MusicBrainz, Discogs | Yes (both) |
| `MANGA` | Google Books (by ISBN), AniList/Jikan (title fallback) | Yes (Google Books, ISBN only) |
| `BOOK` | Google Books (by ISBN) | Yes (ISBN only) |
| `COMIC_BOOK` | General UPC providers -> Comic Vine (title/issue search) | No (indirect only) |
| `GRAPHIC_NOVEL` | Google Books (by ISBN); Comic Vine (title/volume search) if ISBN lookup fails | Yes (Google Books, ISBN only) |
| `BLU_RAY`, `DVD`, `VHS`, `VCD` | General UPC providers -> TMDb/OMDb (title search) | No (indirect only) |
| `VIDEO_GAME` | ScanDex (direct barcode); General UPC providers -> IGDB/RAWG (title search); PriceCharting (direct barcode) only if configured | Partial — yes via ScanDex, and via PriceCharting if configured (Appendix A.4) |
| `LASERDISC` | General UPC providers only (no title-search refinement provider exists) | Partial — hit rate is low and unpredictable; see Appendix A.6 |

#### 6.2.1 Music Format Mapping

MusicBrainz and Discogs each catalog one release per physical format, exposing that format as a
string field (MusicBrainz `release.media[].format`, Discogs `format` in search results). Because
`CD`, `VINYL`, and `CASSETTE` are three separate `MediaType` values (Section 3.1), every music
`BarcodeCandidate`'s `media_type` is derived from that field, not left to the provider's own
category guess:

| Provider format value | MediaType |
|---|---|
| `CD` | `CD` |
| `Vinyl` | `VINYL` |
| `Cassette` | `CASSETTE` |
| Anything else (e.g. `Digital Media`, `SACD`, `DVD-Audio`) | `None` — candidate is still surfaced, with `media_type = None` for the member to classify manually when selecting it |

### 6.3 Caching and Rate-Limit Policy

**Every provider call the backend makes is cached in `BarcodeCache` keyed by the normalized
barcode**, per Section 5.3, `CACHE_TTL = 30 days` by default. This is required, not optional
optimization: MusicBrainz enforces roughly 1 request/second per client and will temporarily ban an
IP that exceeds it; UPCitemdb's free tier is capped at 100 requests/day. Repeated scans of the same
item (the dominant real-world usage pattern — checking for duplicates) must not re-issue provider
requests within the cache window.

Requests to MusicBrainz additionally self-throttle to one in flight at a time with the required
custom `User-Agent` header, per its published policy (Appendix A.5).

### 6.4 Error Handling

| Error Type | Example | Recovery |
|---|---|---|
| Provider timeout | A provider takes longer than `PROVIDER_TIMEOUT_MS` | Treated as no result from that provider; other providers still run; logged, not surfaced to the member |
| Provider rate-limited (HTTP 429) | UPCitemdb daily cap exceeded | Back off that provider for the remainder of the day (tracked server-side); other providers still run |
| Provider auth failure | Expired/misconfigured API key | Logged as an operational alert; provider treated as unavailable until fixed; other providers still run |
| All providers fail or return nothing | Barcode unknown everywhere (expected for laserdiscs) | `requires_manual_entry = True` (Section 5.5); this is normal operation, not a system error |

---

## 7. Collection Management

### 7.1 Browse, Search, Filter, Sort

The collection view supports: full-text search over `title`/`subtitle`/`notes`, filtering by one or
more `media_type` values, filtering by `added_by`, and sorting by title, `created_at`, or
`updated_at`. Search and filters are combinable (e.g. "manga containing 'berserk', sorted by
title", or "everything on `VINYL`, sorted by newest added").

### 7.2 Create/Edit/Delete

Any household member can create, edit, or delete any item, regardless of who originally added it
(there is no per-item ownership restriction — see Section 3.3). Deletion requires an inline
confirmation step in the UI; there is no soft-delete/trash (see Section 12).

### 7.3 Duplicate Warning UX

Outside of the scan flow, typing a title/barcode into the manual-add form triggers the same
`resolve_barcode`-driven owned-match check whenever a barcode is present, so the "you already own
this" warning (Section 5.4) applies consistently regardless of entry path.

### 7.4 Admin Record Editor

`ADMIN` accounts (4.1) get a second, more permissive edit surface on top of 7.2's normal one — the
same validated backend, exposing more fields, not a separate unvalidated path (13's rationale on
why this isn't a raw SQL console).

```
INTERFACE AdminRecordService:
    FUNCTION update_item_admin(admin, item_id, full_payload) -> MediaItem
    FUNCTION list_barcode_cache(admin, page) -> Page<BarcodeCache>
    FUNCTION get_barcode_cache(admin, barcode) -> BarcodeCache
    FUNCTION delete_barcode_cache(admin, barcode)
```

**`update_item_admin` accepts every `MediaItem` field** (3.2), including ones the normal member
edit form (7.2) never exposes: `media_type`, `source`, `external_ids`, `added_by`. Changing
`media_type` re-validates `attributes` against the new type's Appendix B schema exactly as item
creation does (3.2) — an admin can fix a miscategorized item, but not leave it with an
attribute shape that doesn't match its (new) category.

**`delete_barcode_cache` exists to unstick a bad cache entry** — e.g. a provider returned garbage
that got cached for `CACHE_TTL` (6.3). Deleting the entry doesn't touch any `MediaItem`; the next
scan of that barcode simply re-resolves from scratch (5.3).

---

## 8. REST API Surface

```
INTERFACE CollectionAPI:
    FUNCTION list_items(filters, sort, page) -> Page<MediaItem>
    FUNCTION get_item(id) -> MediaItem
    FUNCTION create_item(payload) -> MediaItem
    FUNCTION update_item(id, payload) -> MediaItem
    FUNCTION delete_item(id)

INTERFACE BarcodeAPI:
    FUNCTION resolve(barcode) -> ResolutionResult          -- Section 5.3
    FUNCTION create_from_candidate(candidate, media_type, overrides) -> MediaItem
```

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/auth/login` | None | Exchange username/password for a token pair |
| POST | `/api/auth/refresh` | Refresh cookie | Exchange a valid refresh token for a new access token |
| POST | `/api/auth/logout` | Access token | Revoke the current refresh token |
| GET | `/api/auth/me` | Access token | Current user's profile, including `role` (4) |
| GET | `/api/items` | Access token | List/search/filter/sort items (7.1) |
| POST | `/api/items` | Access token | Create an item manually (5.5, 7.2) |
| GET | `/api/items/{id}` | Access token | Fetch one item |
| PATCH | `/api/items/{id}` | Access token | Edit an item (7.2's field set) |
| DELETE | `/api/items/{id}` | Access token | Delete an item |
| GET | `/api/barcode/{barcode}/resolve` | Access token | Run resolution (5.3), returns candidates + owned matches |
| POST | `/api/barcode/items` | Access token | Create an item from a chosen `BarcodeCandidate` (5.3) |
| GET | `/api/admin/users` | Admin | List all household accounts (4.1) |
| POST | `/api/admin/users` | Admin | Create a household account, with `role` (4.1) |
| PATCH | `/api/admin/users/{id}` | Admin | Edit username/display_name/role |
| POST | `/api/admin/users/{id}/reset-password` | Admin | Set a new password for the account |
| DELETE | `/api/admin/users/{id}` | Admin | Delete the account (4.1's added_by handling) |
| PATCH | `/api/admin/items/{id}` | Admin | Edit an item with 7.4's full field set |
| GET | `/api/admin/barcode-cache` | Admin | List cached barcode resolutions (7.4) |
| GET | `/api/admin/barcode-cache/{barcode}` | Admin | Fetch one cache entry |
| DELETE | `/api/admin/barcode-cache/{barcode}` | Admin | Purge a cache entry (7.4) |

---

## 9. Frontend Application

### 9.1 Views

| View | Purpose |
|---|---|
| Login | Username/password form |
| Collection browse | Search/filter/sort grid of owned items (7.1) |
| Item detail | Full attribute view (Appendix B fields), edit/delete entry points |
| Scan | Opens the camera, decodes a barcode, navigates to Resolution |
| Resolution | Shows owned matches (5.4) and every `BarcodeCandidate` (5.3) for the member to choose from, or "Add manually" |
| Manual entry / edit form | Category-aware form driven by Appendix B's per-`MediaType` fields |
| Admin: Users *(admin only)* | List/create/edit/delete household accounts, reset passwords (4.1) |
| Admin: Item editor *(admin only)* | 7.4's full-field item edit, reachable from Item detail for admins |
| Admin: Barcode cache *(admin only)* | List/inspect/purge cached resolutions (7.4) |

**Admin views are hidden, not merely blocked, from non-admins.** The frontend reads `role` from
`GET /api/auth/me` (8) once at login and never renders admin nav entries, routes, or buttons for a
`MEMBER` — the backend's 403s (4.1) are a defense-in-depth backstop, not the primary access control.

### 9.2 PWA and Camera Requirements (Critical)

The frontend is built as an installable Progressive Web App (manifest + service worker via
`vite-plugin-pwa`) so it can be added to a phone's home screen and launched full-screen for
scanning, without requiring a native app store submission. Per Section 2.2, camera access requires
a valid HTTPS context in every deployed environment — there is no environment where this app is
expected to run over plain HTTP other than local development (`localhost` is exempt by browser
policy).

---

## 10. Testing Strategy (Critical)

### 10.1 TDD Workflow

For every feature in this spec, a failing test is written first, against the requirement as stated
in the relevant section, before the implementing code is written. A pull request that adds
production code without a preceding or accompanying test for that code is incomplete.

### 10.2 Test Pyramid

| Level | Tooling | Scope |
|---|---|---|
| Backend unit | `pytest` | Pure logic: barcode normalization (5.1.1), deduplication (5.3.1), music format mapping (6.2.1), attribute validation against Appendix B schemas, auth token handling |
| Backend integration | `pytest` + `TestClient` + a real MySQL test database | Full request/response cycles through the REST API (Section 8) against actual SQL, including migrations |
| Provider contract tests | `pytest` + `respx` against recorded fixtures | `MetadataProvider` implementations, see 10.3 |
| Frontend unit/component | `vitest` + `React Testing Library` | Individual components (Resolution candidate list, manual entry form validation, etc.) |
| End-to-end | `Playwright` | Full user flows: login -> scan (mocked camera/decoder) -> resolve (mocked backend) -> select candidate -> item appears in collection |

### 10.3 External Provider Test Doubles

Live calls to the free APIs in Appendix A are never made from the automated test suite — they are
rate-limited, sometimes flaky, and would make tests non-deterministic. Instead:

1. A one-time script records a real response from each provider (success, empty-result, and
   rate-limited cases) into a fixture file under `backend/tests/fixtures/providers/`.
2. `respx` mocks `httpx` to return these fixtures for the corresponding provider URL patterns in
   all automated tests.
3. Fixtures are refreshed manually when a provider's response shape changes, never automatically
   as part of CI.

**Required fixture cases per provider (minimum):** a successful single-match response, a
successful multiple-match response (to exercise the multi-candidate UI), an empty/no-match
response, and a rate-limited (429) response (to exercise 6.4's recovery path). MusicBrainz and
Discogs fixtures additionally include one release of each of `CD`, `Vinyl`, and `Cassette` format,
plus one unmapped format (e.g. `Digital Media`), to exercise 6.2.1.

### 10.4 Coverage Targets

| Area | Target |
|---|---|
| Backend overall line coverage | 85% |
| `resolve_barcode`, `deduplicate`, `map_music_format` (5.3, 5.3.1, 6.2.1) | 100% branch coverage, including every row of the error table in 6.4 |
| Frontend components overall | 80% |

---

## 11. Deployment and Operations

### 11.1 Containers

Three services under Docker Compose: `frontend` (static Vite build served by Caddy), `backend`
(FastAPI via `uvicorn`), `db` (MySQL 8.0 with a persistent named volume). Caddy also acts as the
reverse proxy in front of `backend`, terminating TLS for both services from one entrypoint.

### 11.2 Secrets and Configuration

| Key | Type | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | String | *(none — required)* | MySQL connection string |
| `JWT_SECRET` | String | *(none — required)* | Signing secret for access/refresh tokens |
| `GOOGLE_BOOKS_API_KEY` | String | `""` (keyless mode) | Optional; keyless Google Books works but at a lower, less reliable limit (Appendix A.3) |
| `TMDB_API_KEY` | String | *(none — required for BLU_RAY/DVD/VHS/VCD lookup)* | Appendix A.2 |
| `OMDB_API_KEY` | String | *(none — required for BLU_RAY/DVD/VHS/VCD lookup)* | Appendix A.2 |
| `SCANDEX_API_KEY` | String | *(none — required for direct VIDEO_GAME barcode lookup)* | Appendix A.4; free tier is time-limited, monitor for deprecation |
| `IGDB_CLIENT_ID` / `IGDB_CLIENT_SECRET` | String | *(none — required for VIDEO_GAME lookup)* | Twitch developer credentials, Appendix A.4 |
| `RAWG_API_KEY` | String | *(none — required for VIDEO_GAME lookup)* | Appendix A.4 |
| `PRICECHARTING_API_KEY` | String | `""` (provider disabled) | Optional, paid; Appendix A.4. Provider is not instantiated at all when unset |
| `DISCOGS_TOKEN` | String | `""` (falls back to unauthenticated, lower rate limit) | Appendix A.5 |
| `COMICVINE_API_KEY` | String | *(none — required for COMIC_BOOK lookup)* | Appendix A.7 |
| `UPCITEMDB_MODE` | String | `"trial"` | Trial (keyless, IP-based) vs paid, Appendix A.1 |
| `BARCODESPIDER_API_KEY` | String | *(none — optional)* | Appendix A.1 |
| `CACHE_TTL_DAYS` | Integer | `30` | See Section 5.3's `CACHE_TTL` |

All secrets are supplied via environment variables at deploy time and are never committed to the
repository; a `.env.example` file documents every key above with no real values.

### 11.3 HTTPS and Reverse Proxy

Caddy obtains and renews a Let's Encrypt certificate automatically for the deployment's domain
name, satisfying the hard HTTPS requirement from Section 2.2.

### 11.4 Backups

The `db` container's volume is backed up on a daily schedule via a scheduled `mysqldump` to
off-container storage. This is the only durable copy of the collection data and must be verified
restorable, not merely taken.

---

## 12. Out of Scope

**Native mobile app.** A dedicated iOS/Android app store submission, as opposed to the
browser-based PWA (Section 9.2). The PWA covers camera-based scanning without app store
distribution overhead. Extension point: the same barcode-decoding and REST API could be wrapped in
a native shell (e.g. Capacitor) later if PWA camera performance proves insufficient on some device.

**Per-item ownership locks.** Every account, `ADMIN` or `MEMBER`, can still edit or delete every
item (Section 7.2) — the `Role` distinction added in Section 4.1 governs user management and the
admin record editor (7.4), not who may touch a given collection item. A per-item lock (e.g. "only
the adder or an admin may delete this") is a further narrowing this spec does not make. Extension
point: `MediaItem.added_by` (3.2) plus `Role` (3.3) already carry enough information to add such a
check to `delete_item`/`update_item` later without a schema change.

**A raw SQL / arbitrary-query admin console.** The admin record editor (7.4) exposes every field on
`MediaItem` and `BarcodeCache` but only through the same validated backend every other write goes
through — there is no query box that executes arbitrary SQL. This was a deliberate choice, not an
oversight (see Section 13): a stray query with no undo is a standing risk this spec chooses not to
accept for a household app. Extension point: none intended — if a specific gap in the record editor
is found, the fix is to expose the missing field/table through `AdminRecordService` (7.4), not to
add a query console.

**Fine-grained admin permissions.** `Role` (3.3) is binary — `ADMIN` or `MEMBER` — there is no
"can manage users but not edit records" or per-table permission grid. Extension point: `Role` could
become a permission bitmask or a join table later if the household's needs get more granular than
that; nothing here precludes it.

**Loan/borrow tracking.** Tracking that an item has been lent out to someone outside the household.
Extension point: add a `status`/`loaned_to` field to `MediaItem` later; the current schema does not
preclude it.

**Recommendation / "what to buy next."** Suggesting new purchases based on the existing collection.
This is a distinct feature built on top of, not required by, a working catalog. Extension point:
the external metadata already fetched (Appendix A) could feed a recommendation feature later.

**Offline-first full collection caching.** The PWA (Section 9.2) is installable but does not cache
the entire collection for offline browsing. Extension point: a cache-first service worker strategy
could be added without changing the API surface.

**Barcode/label printing for unlabeled items.** Generating a printable barcode for items that never
had one (e.g. some laserdiscs or vintage cassettes). Extension point: could reuse `MediaItem.id` as
an internal code and add a label-rendering view later.

**Multi-household / multi-tenant support.** This spec assumes one shared collection for one
household. Extension point: add a `household_id` partition key to `MediaItem` and `User` later if
the system needs to serve more than one household.

---

## 13. Design Decision Rationale

**Why FastAPI + React instead of a single full-stack framework (e.g. Next.js)?** Barcode resolution
(Section 5) is server-side business logic that must be independently unit-testable (Section 10)
without a UI framework in the loop; a Python backend also gives straightforward MySQL access via
SQLAlchemy and `pytest`-based TDD, while React with Vite gives a fast PWA build. Splitting the
concerns keeps the resolution logic testable in isolation from rendering concerns.

**Why a JSON `attributes` column instead of one table per media type?** Twelve categories with
divergent and likely-to-evolve attribute sets (Appendix B) would require a constant stream of
schema migrations and complex cross-category UNION queries if modeled as separate tables. A single
`MediaItem` table with a validated JSON column (Section 3.2) keeps browsing/search/filter (7.1)
simple across all categories, at the cost of the database itself not enforcing per-category shape —
that validation instead lives in the Pydantic schemas the backend applies before writing.

**Why cache barcode resolution server-side instead of querying providers on every scan?** Several
providers used here have strict free-tier rate limits — MusicBrainz roughly 1 request/second,
UPCitemdb 100 requests/day (Appendix A) — and the single most common real-world scan is a repeat
scan of something already owned, done specifically to check for a duplicate. Caching (Section 6.3)
turns that dominant case into a near-zero-cost lookup and is also the mechanism that accumulates a
reused barcode's full candidate history over time (Section 5.3), which a stateless per-scan query
could never do.

**Why not block adding an item that matches no provider (e.g. most laserdiscs)?** No dedicated,
curated laserdisc API exists (confirmed twice during spec research, Appendix A.6) — general UPC
lookup incidentally covers some US laserdiscs, but sparsely and unpredictably. Treating "no match
found" as a routine, first-class path to manual entry (Section 5.5) rather than a degraded fallback
keeps the app usable for the categories with poor or no API coverage, not just the ones with good
coverage.

**Why fold anime into `BLU_RAY`/`DVD`/`VHS`/`VCD`/`LASERDISC` instead of giving it its own
`MediaType`?** Anime is a genre, not a physical format — the format categories already needed for
any other film/TV release apply to it identically, and it resolves through exactly the same
provider path (Section 6.2). A separate `ANIME` type would duplicate that routing with no
behavioral difference; the earlier draft of this spec had one and it was removed for that reason.

**Why split music into `CD`/`VINYL`/`CASSETTE` instead of one `MUSIC` type with a format
attribute?** The household wants to filter the collection by physical format directly (7.1), which
a top-level `MediaType` supports natively without every view and filter branching on an attribute
value. The tradeoff is that MusicBrainz and Discogs each return one `format` string per release
that must be mapped onto the three types (Section 6.2.1) rather than trusted as a `MediaType`
as-is.

**Why is `GRAPHIC_NOVEL` its own `MediaType` instead of folding into `BOOK` or `COMIC_BOOK`?**
Bibliographically, a graphic novel is a bound collected edition sold with an ISBN like a book — not
a single issue sold with a UPC — so it resolves through the same reliable ISBN path as `BOOK` and
`MANGA` rather than `COMIC_BOOK`'s indirect, less reliable one (Section 6.2). But its attribute
shape (writer, artist, collected issues) is comics-specific, not book-specific, and Comic Vine's
`volume` resource is a better fallback match for it than a generic book search. A dedicated type
keeps both the reliable resolution path and the comics-appropriate attributes without compromising
either `BOOK` or `COMIC_BOOK`.

**Why include ScanDex for `VIDEO_GAME` despite its free tier being explicitly time-limited?**
Video games are a priority category for this household, and no other free API does direct
barcode-to-game lookup — the alternative (PriceCharting) is paid-only, and everything else is
title-search-only (Appendix A.4). ScanDex is worth the risk specifically because the system does
not depend on it: it is one more fault-tolerant provider in an already fault-tolerant pipeline
(Section 6.4), so its disappearance degrades `VIDEO_GAME` resolution back to the indirect general-
UPC-lookup path rather than breaking anything.

**Why is PriceCharting optional and off by default instead of a required provider given its strong
retro-game UPC coverage?** Every other provider in this spec has a genuine free tier; requiring a
paid subscription for a core lookup path would contradict Section 1.3's free-API design principle
for every other category. Gating it behind an unset-by-default API key keeps it available as a
deliberate upgrade a household can opt into, without making the base system depend on a paid
service.

**Why route `VHS` and `VCD` through the same providers as `DVD`/`Blu-ray` instead of a
dedicated provider?** No metadata provider indexes releases by physical format — TMDb and OMDb
catalog the underlying film or show, not the disc or tape it was pressed onto, so the same title
search that resolves a DVD resolves the identical film on VHS or VCD. A format-specific provider
does not exist for either format and is not needed.

**Why household accounts instead of one shared login?** The requirement was to catalog a shared
collection, not to gate collection access between members — every account can browse and edit every
item regardless of role (Section 3.3, Section 12). Individual accounts are the minimal mechanism
that lets `MediaItem` record who added or last edited an entry, and are also what makes an `ADMIN`
tier possible at all (4.1) without inventing a second identity system.

**Why is registration invite-only rather than self-service?** A public sign-up page is unnecessary
attack surface for an application meant to be used by one specific household. Restricting account
creation to admins (Section 4.1) keeps the account list closed without adding an approval workflow.

**Why introduce an `ADMIN`/`MEMBER` split at all, when an earlier draft of this spec deliberately
kept access flat?** The flat model was correct until "manage other people's accounts" and "make
direct edits to any record's raw fields" became actual requirements — those two capabilities are
qualitatively different from cataloguing a shared collection, and giving every member both by
default would mean any account compromise (or honest mistake) can rewrite anyone's login or any
item's ownership history. A role is the minimal mechanism that lets a subset of trusted accounts
have that power without giving it to every account by default. Section 12 is explicit that this
does *not* extend to per-item ownership locks — the flat model's actual goal, "nobody needs
permission to catalogue," is preserved.

**Why is the admin record editor (7.4) a superset of validated fields instead of a raw SQL
console?** A query box is the most flexible possible admin tool and also the most dangerous one
this app could ship: no undo, no schema awareness, and a single typo can corrupt the only copy of
the collection (11.4's backup is daily, not real-time). Routing every admin edit through the same
Pydantic validation normal writes use (3.2) means an admin can fix `media_type`, `added_by`, or a
stale `external_ids` entry, but cannot leave a record in a shape the application itself couldn't
have produced. The tradeoff is that a genuinely novel corruption case might need a code change
(a new field exposed on `AdminRecordService`) rather than an ad hoc query — an acceptable and
rare cost for a household app, not a production database with a dedicated operator.

**Why does deleting a user null out `added_by` instead of deleting their items, or blocking
deletion until their items are reassigned?** The collection belongs to the household, not to
whichever member happened to scan an item first (7.2) — losing attribution when someone leaves is
a reasonable cost, losing their catalogued items is not. Blocking deletion until every item is
manually reassigned would make removing an account disproportionately tedious for what is, in
practice, a rare action.

**Why does the first (seed-script) account default to `ADMIN` instead of `MEMBER`?** Whoever can
run a script against the production database already has more access than the admin role grants
inside the app (11.1) — denying them the `ADMIN` role would just mean their first action is
promoting themselves, adding a step without adding safety.

**Why does barcode resolution treat every provider call as independently fault-tolerant (Section
6.4) instead of failing the whole scan on one provider's error?** The providers in Appendix A are
free-tier third-party services outside this application's control, individually prone to timeouts
and rate limits. A member scanning a CD should still see MusicBrainz's results even if TMDb is
down; requiring every provider to succeed would make the feature only as reliable as its least
reliable dependency.

---

## 14. Definition of Done

### 14.1 Overview and Goals

- [ ] Opening paragraph states what the app is and who uses it
- [ ] Problem statement follows status-quo -> pain -> solution
- [ ] Design principles are named, checkable constraints

### 14.2 Architecture

- [ ] Frontend never calls external metadata providers directly; all such calls are proxied through the backend
- [ ] Frontend never connects to MySQL directly
- [ ] The deployed environment serves the app over valid HTTPS in every environment other than local `localhost` development
- [ ] The three containers (frontend, backend, db) run via a single Docker Compose definition

### 14.3 Data Model

- [ ] `MediaItem` persists all fields in 3.2, including a validated JSON `attributes` column
- [ ] `MediaItem.barcode` has no uniqueness constraint at the database level
- [ ] `User` accounts exist with hashed passwords (never plaintext, never reversible encryption)
- [ ] `BarcodeCache` persists and accumulates candidates across repeated resolutions of the same barcode, including across different media types
- [ ] There is no `ANIME` value anywhere in the `MediaType` enum or database
- [ ] `User.role` exists and defaults to `MEMBER`; `MediaItem.added_by` is nullable at the database level

### 14.4 Authentication and Access Control

- [ ] Login issues a short-lived access token and a longer-lived refresh token
- [ ] There is no public self-registration endpoint
- [ ] Only an `ADMIN` can create, edit, or delete household accounts (4.1); a `MEMBER` calling any admin user-management endpoint gets 403
- [ ] The seed script's first account is created with `role = ADMIN` (13's rationale)
- [ ] `GET /api/auth/me` returns the caller's `role`
- [ ] Expired access tokens are transparently refreshed by the frontend; expired refresh tokens redirect to login
- [ ] Every error case in Section 4 and 4.1's tables returns the specified status and behavior
- [ ] Deleting a user sets `added_by = None` on every item they added, rather than deleting those items or failing
- [ ] Deleting or demoting the last remaining `ADMIN` is rejected with 409, with no partial effect

### 14.5 Barcode Scanning and Resolution

- [ ] Camera capture decodes UPC-A, UPC-E, EAN-13, EAN-8, and Code128 client-side
- [ ] UPC-E and zero-padded EAN-13 values normalize to the same cache key as their UPC-A equivalent (5.1.1)
- [ ] `resolve_barcode` serves from `BarcodeCache` within `CACHE_TTL` before querying any provider
- [ ] `resolve_barcode` always returns both `owned_matches` and `candidates` together
- [ ] A barcode resolving to zero candidates and zero owned matches sets `requires_manual_entry = True`
- [ ] An ISBN-13 barcode (prefix 978/979) always triggers a direct Google Books lookup (5.3 Step 3)
- [ ] A single provider throwing `ProviderError` never prevents other providers from contributing candidates
- [ ] `deduplicate` collapses same-provider/same-external_id and same-title/same-media_type candidates from different providers
- [ ] A barcode previously resolved under a different media type retains those historical candidates on a later resolution
- [ ] A `LASERDISC` barcode that a general UPC provider recognizes returns `requires_manual_entry = False` with a `media_type = None` candidate, not a forced manual-entry path (5.5)

### 14.6 External Metadata Providers

- [ ] Every `MetadataProvider` implementation in Appendix A conforms to the `MetadataProvider` interface (6.1)
- [ ] Routing in Section 6.2 is followed exactly per `MediaType`
- [ ] MusicBrainz requests are throttled to the documented rate and include a custom `User-Agent`
- [ ] `map_music_format` (6.2.1) correctly maps `CD`/`Vinyl`/`Cassette` provider format strings to `MediaType`, and sets `media_type = None` for any unmapped format
- [ ] The PriceCharting provider is never instantiated (and never called) when `PRICECHARTING_API_KEY` is unset (Appendix A.4)
- [ ] `VIDEO_GAME` resolution still functions via the indirect general-UPC-lookup -> IGDB/RAWG path when ScanDex is unreachable or removed, with no code change required (verified with a test that disables the ScanDex fixture)
- [ ] Every error row in Section 6.4's table has an implemented, tested recovery path

### 14.7 Collection Management

- [ ] List endpoint supports combined full-text search, `media_type` filter, `added_by` filter, and sort by title/`created_at`/`updated_at`
- [ ] Any authenticated account, admin or member, can create, edit, and delete any item via 7.2's field set
- [ ] Deletion requires explicit UI confirmation
- [ ] Manual entry with a barcode present triggers the same owned-match check as the scan flow (7.3)
- [ ] `PATCH /api/admin/items/{id}` accepts every `MediaItem` field, including `media_type`, `source`, `external_ids`, and `added_by`; a `MEMBER` calling it gets 403
- [ ] Changing `media_type` via the admin editor re-validates `attributes` against the new type's Appendix B schema
- [ ] `GET/DELETE /api/admin/barcode-cache*` let an admin inspect and purge cache entries; purging one does not modify any `MediaItem`

### 14.8 REST API Surface

- [ ] Every endpoint in Section 8's table is implemented with the specified method, path, and auth requirement
- [ ] `POST /api/barcode/items` persists a `MediaItem` with `source = SCANNED` and the chosen candidate's `external_id` recorded in `external_ids`

### 14.9 Frontend Application

- [ ] Every view in Section 9.1 is implemented
- [ ] The app is installable as a PWA (manifest + service worker present)
- [ ] Camera scanning is verified working over HTTPS on an actual phone browser, not only in desktop dev tools emulation
- [ ] Admin nav entries, routes, and buttons are absent (not just disabled) for a logged-in `MEMBER`, verified by a test that asserts on their absence, not just on a blocked action

### 14.10 Testing Strategy

- [ ] No production code is merged without a preceding or accompanying test
- [ ] No automated test makes a live network call to any provider in Appendix A
- [ ] Fixture files exist for every provider covering: single match, multiple matches, no match, and rate-limited response
- [ ] MusicBrainz/Discogs fixtures cover `CD`, `Vinyl`, `Cassette`, and one unmapped format (10.3)
- [ ] Coverage targets in 10.4 are met, with `resolve_barcode`/`deduplicate`/`map_music_format` at 100% branch coverage
- [ ] A Playwright end-to-end test covers: login -> scan -> resolve -> select candidate -> item visible in collection

### 14.11 Deployment and Operations

- [ ] All secrets in 11.2's table are supplied via environment variables, with a `.env.example` documenting every key and no real values committed
- [ ] Caddy obtains and auto-renews a valid TLS certificate for the deployed domain
- [ ] A daily `mysqldump` backup runs and has been verified restorable at least once

### 14.12 Integration Smoke Test

```
FUNCTION test_scan_to_catalog_end_to_end():
    -- Setup: two household members, provider fixtures loaded (10.3)
    alice = seed_admin("alice", password="...")               -- 13's rationale: first account is ADMIN
    bob = alice.create_user("bob", password="...", role=MEMBER)  -- 4.1: only an admin can create accounts

    -- Scan a barcode whose MusicBrainz fixture returns exactly one CD candidate
    login(alice)
    result = resolve_barcode(known_cd_barcode)
    ASSERT result.owned_matches == []
    ASSERT length(result.candidates) == 1
    ASSERT result.candidates[0].media_type == CD
    item = create_from_candidate(result.candidates[0], media_type=CD)
    ASSERT item.source == SCANNED
    ASSERT item.added_by == alice.id

    -- Second member scans the same barcode -- must now see it as already owned
    login(bob)
    result2 = resolve_barcode(known_cd_barcode)
    ASSERT length(result2.owned_matches) == 1
    ASSERT result2.owned_matches[0].id == item.id

    -- Scan a barcode whose fixtures return candidates under two different media types
    result3 = resolve_barcode(reused_barcode_fixture)
    ASSERT length(result3.candidates) >= 2
    ASSERT count(DISTINCT c.media_type FOR c IN result3.candidates) >= 2

    -- Scan a barcode with no fixture data at all (simulates a laserdisc)
    result4 = resolve_barcode(unknown_barcode)
    ASSERT result4.requires_manual_entry == True
    manual_item = create_item(media_type=LASERDISC, title="...", barcode=unknown_barcode, source=MANUAL)
    ASSERT manual_item.id is not None
```

---

## Appendix A: External API Catalog

Referenced from Section 6. Every provider below is free to use at the tier described; several
still require a free-signup API key. All entries were verified via each provider's own
documentation during spec research; treat rate limits as subject to change and re-verify before
relying on them in production.

### A.1 General UPC/EAN Lookup

| Provider | Base URL | Auth | Free tier limit | Barcode lookup |
|---|---|---|---|---|
| UPCitemdb | `api.upcitemdb.com/prod/trial/lookup` | None (IP-based trial key) | 100 combined lookup+search/day, 6/min burst | Yes, direct |
| Barcode Spider | `barcodespider.com` API | Free signup | 100 UPC lookups/day | Yes, direct |
| Barcode Lookup | `barcodelookup.com` API | Free signup | 100 req/min cap; persistent monthly free quota unconfirmed — verify before relying on it | Yes, direct |

### A.2 Movies and Video Releases (Blu-ray / DVD / VHS / VCD)

| Provider | Base URL | Auth | Free tier limit | Barcode lookup |
|---|---|---|---|---|
| TMDb | `api.themoviedb.org/3` | Free signup key | ~50 req/sec, 20 connections/IP | No — title/IMDb-ID search only |
| OMDb | `omdbapi.com` | Free key via email request | 1,000 req/day | No — title/IMDb-ID search only |

Neither provider indexes by physical format — both catalog the underlying film or TV title, so the
same lookup serves `BLU_RAY`, `DVD`, `VHS`, and `VCD` releases of that title identically, anime
included (Section 3.1's note on anime).

**TMDb attribution requirement:** any use of TMDb data must display "This product uses the TMDB API
but is not endorsed or certified by TMDB," per its API Terms of Use.

### A.3 Manga and Books

| Provider | Base URL | Auth | Free tier limit | Barcode lookup |
|---|---|---|---|---|
| Google Books | `www.googleapis.com/books/v1` | Keyless works but is unreliable; free API key recommended | ~1,000 req/day, ~1 req/sec/user | Yes — `isbn:XXXXXXXXXX` query |
| AniList | `graphql.anilist.co` (GraphQL) | None for public queries | 90 req/min + burst limiter | No — title search only; used as a `MANGA` fallback for non-ISBN entries |
| Jikan (unofficial MyAnimeList) | `api.jikan.moe/v4` | None | ~60 req/min; caching strongly recommended | No — title search only; used as a `MANGA` fallback for non-ISBN entries |

Google Books covers standalone `BOOK` and `GRAPHIC_NOVEL` items identically to `MANGA` — all three
are looked up by ISBN (EAN-13 prefix 978/979) via the same provider and the same `is_isbn13` branch
of Section 5.3's resolution algorithm. There is no separate provider or code path for `BOOK`.
`GRAPHIC_NOVEL` additionally falls back to a Comic Vine title/volume search (Appendix A.7) when its
ISBN goes unmatched — collected editions are exactly the kind of "volume" Comic Vine indexes.
AniList and Jikan are retained only as a title-search fallback for manga volumes that carry no
usable ISBN; neither is used for `BOOK` or `GRAPHIC_NOVEL`.

### A.4 Video Games

| Provider | Base URL | Auth | Free tier limit | Barcode lookup |
|---|---|---|---|---|
| ScanDex | `scandex.gamery.app/api/v2/lookup` | Free signup, Bearer token | "Free during launch period" — no permanent free tier guaranteed; ~100k barcodes / ~20k games (PlayStation/Xbox/Nintendo) | Yes — `?value={UPC/EAN}`, purpose-built for physical game barcodes |
| IGDB | `api.igdb.com/v4` | Free Twitch developer Client-ID + OAuth token | 4 req/sec, 8 concurrent max | No — title/platform search only |
| RAWG | `api.rawg.io` | Free signup key | 20,000 req/month (~1,000/hr) | No — title search only |
| PriceCharting *(optional, paid)* | `pricecharting.com/api` | Paid subscription only — no free API tier, even though the website itself is free to browse | N/A (paid) | Yes — `?upc=`, strong retro + modern console coverage per community reports |

**ScanDex is the primary direct-barcode source for `VIDEO_GAME`, with a known risk.** It is the
only free, purpose-built game-barcode API found during spec research, but its free access is
explicitly time-boxed ("launch period," not a permanent tier) and its catalog is modest relative to
IGDB/RAWG's. The system must degrade gracefully if it goes paid or offline — Section 6.4's
provider-fault-tolerance already makes this a no-code-change scenario: `VIDEO_GAME` resolution
simply falls back to the general UPC lookup -> IGDB/RAWG indirect path (6.2) with no special casing.

**PriceCharting is deliberately optional and disabled by default.** Every other provider in this
appendix has a genuine free tier; PriceCharting's API requires a paid subscription regardless of
usage volume. It is included only because its UPC coverage of retro cartridges is reported as
strong, and a household with heavy retro-game cataloging may choose to pay for it. The backend only
instantiates this provider when `PRICECHARTING_API_KEY` (Section 11.2) is set; an empty key means
it is never called, not merely rate-limited.

Investigated and ruled out for `VIDEO_GAME` barcode lookup: **TheGamesDB** (no UPC/EAN field in its
schema at all), **GiantBomb** (has product-code fields on release records but no search-by-UPC
endpoint — the release must already be known), **MobyGames** (no confirmed UPC-lookup endpoint,
and API access requires a paid MobyPro key regardless), and **Backloggery** (a personal
backlog-tracking site, not a game database — no official API exists at all per its own unofficial
wrapper projects' documentation, no barcode concept, and no canonical catalog to query; all data is
free-text and scoped to one user's manually-typed collection).

### A.5 Music (CD / Vinyl / Cassette)

| Provider | Base URL | Auth | Free tier limit | Barcode lookup |
|---|---|---|---|---|
| MusicBrainz | `musicbrainz.org/ws/2` | None; requires a custom `User-Agent` header identifying the app | ~1 req/sec hard limit; exceeding risks a temporary IP ban | Yes — `barcode:` field on release search |
| Cover Art Archive | `coverartarchive.org` | None | Same policy as MusicBrainz | Companion image lookup only, keyed by MusicBrainz release ID |
| Discogs | `api.discogs.com` | Free signup (token or key+secret); requires a unique `User-Agent` | 60 req/min authenticated, 25/min unauthenticated | Yes — `barcode` search parameter |

Both providers serve `CD`, `VINYL`, and `CASSETTE` releases from the same barcode-search endpoint;
Section 6.2.1 defines how each candidate's returned format string is mapped onto the correct
`MediaType`.

### A.6 Laserdiscs

No dedicated, curated API exists for laserdisc metadata — this was independently re-verified twice
during spec research. LDDb.com is the only substantial curated catalog; it exposes no developer
program, export, or feed, and blocks automated requests site-wide at the network level (its
homepage, help page, and even `robots.txt` all return HTTP 403), not merely at one endpoint. No
mirror, scrape, or data dump of LDDb was found anywhere (GitHub, Wikidata, or otherwise).

**General UPC providers (Appendix A.1) do have real, if sparse, laserdisc coverage**, since many US
laserdiscs — particularly 1990s mainstream releases — were sold with genuine retail UPC barcodes.
Individual laserdisc entries (e.g. *Toy Story*, *Star Trek*, Criterion's *Brazil*) were confirmed
present in UPCitemdb and Barcode Spider during research. Because Step 1 of `fetch_fresh_candidates`
(Section 5.3) already queries these providers for every barcode regardless of media type, a
laserdisc scan sometimes yields a raw title with no further attempt needed — this is incidental
crowdsourced coverage, not a laserdisc-aware feature, and misses import/Japan-market releases and
anything predating widespread UPC adoption.

**Providers considered and ruled out specifically for laserdiscs:**

| Provider | Finding |
|---|---|
| Discogs (Appendix A.5) | Has a `Laserdisc` format (~7,100 releases) with a working free API, but its laserdisc entries skew almost entirely to music laserdiscs (concert videos), not film catalog releases — wrong content domain for this use case |
| TMDb / OMDb (Appendix A.2) | Confirmed via TMDb's own community forum: a barcode/UPC field has been explicitly requested and explicitly declined; neither API has any physical-format concept |
| Internet Archive `laserdiscs` collection | Has a real, working, open metadata API, but it is a ~500-item digitization/preservation collection with no UPC field — not a barcode-searchable purchase catalog |

Manual entry (Section 5.5) remains the primary, guaranteed path for every laserdisc; general UPC
lookup is a best-effort supplement layered on top of it, not a replacement for it.

### A.7 Comic Books

| Provider | Base URL | Auth | Free tier limit | Barcode lookup |
|---|---|---|---|---|
| Comic Vine | `comicvine.gamespot.com/api` | Free signup key | ~200 req/resource/hour, ~1 req/sec | No — search is by series/issue name and issue number, not by UPC |

Many single comic issues carry a UPC barcode on the cover, but Comic Vine's API exposes no
barcode-search endpoint, and many older back issues and small-press comics were never barcoded at
all. Resolution therefore follows the same indirect path as `VIDEO_GAME`/`BLU_RAY`/`DVD`/`VHS`/`VCD`
(Section 5.3, Step 4): a general UPC provider's raw title, if any, seeds a Comic Vine title/issue
search. A comic with no barcode, or one Comic Vine cannot match by title, falls through to manual
entry (Section 5.5) exactly like a laserdisc.

Comic Vine also serves as the secondary provider for `GRAPHIC_NOVEL` (Appendix A.3): its `volume`
resource models exactly the kind of collected edition a graphic novel is, so when a `GRAPHIC_NOVEL`
barcode's ISBN goes unmatched in Google Books, its raw title is searched against Comic Vine's
volume/issue index rather than falling straight through to manual entry.

---

## Appendix B: Category Attribute Field Reference

Referenced from Section 3.2. Each `MediaType`'s `attributes` JSON shape, validated by the backend
before persistence. All fields are optional (`| None`) since manual entry and partial provider data
must both be accepted — see 13's rationale for the JSON-column approach.

```
RECORD MangaAttributes:
    series_title : String | None
    volume        : Integer | None
    isbn          : String | None
    publisher     : String | None
    author        : String | None

RECORD BookAttributes:
    author        : String | None
    isbn          : String | None
    publisher     : String | None
    series_title  : String | None    -- for multi-book series; None for standalone titles
    edition       : String | None

RECORD ComicBookAttributes:
    series_title  : String | None
    issue_number  : String | None    -- string, not integer: annuals/specials use non-numeric labels
    publisher     : String | None
    writer        : String | None
    artist        : String | None
    variant_cover : String | None    -- e.g. cover artist/description, if a variant

RECORD GraphicNovelAttributes:
    series_title    : String | None
    volume          : Integer | None
    isbn            : String | None
    publisher       : String | None
    writer          : String | None
    artist          : String | None
    collects_issues : String | None    -- free text, e.g. "Issues #1-6"

RECORD VideoGameAttributes:
    platform    : String | None      -- e.g. "Nintendo Switch", "PS5"
    region      : String | None
    developer   : String | None
    publisher   : String | None
    genre       : String | None

RECORD VideoReleaseAttributes:        -- shared by BLU_RAY, DVD, VHS, VCD, LASERDISC
    director        : String | None
    runtime_minutes : Integer | None
    region_code     : String | None
    special_edition : String | None
    is_anime        : Boolean | None  -- optional genre flag; does not affect routing (3.1)

RECORD MusicAttributes:               -- shared by CD, VINYL, CASSETTE
    artist        : String | None
    label         : String | None
    release_year  : Integer | None
    track_count   : Integer | None
```
