# EEA Danswer Fork — Customization Map
*Generated: 2026-04-13 | Base: upstream `v3.2.0` → EEA HEAD `v2.5.3-eea.0.0.103` (tag `v3.2.1`)*
*Primary Author: **Zoltan Szabo** (zoltan.szabo@eaudeweb.ro) — 122 EEA-specific commits*
*Second Author: **Matthieu Boret** (matthieu.boret@fr.clara.net) — SharePoint connector*

---

## I. Feature Index

| # | Feature Block | Files (core) | Risk | Sticky? |
|---|---|---|---|---|
| 1 | Langfuse Tracing & LLM Metadata | `eea_utils.py`, `chat_llm.py`, `run_graph.py`, `langfuse_tracing_processor.py` | 🔴 High | ✅ Yes |
| 2 | EEA Rebranding (AI Hub) | `constants.py`, `EEA_Logo.tsx`, `Header.tsx`, `Footer.tsx`, login/signup pages | 🟡 Medium | ✅ Yes |
| 3 | User Disclaimer Modal | `UserDisclaimerModal.tsx`, backend model + API, admin page | 🟡 Medium | ✅ Yes |
| 4 | Custom Pages (Admin) | `web/src/app/admin/eea_config/pages/` | 🟡 Medium | ✅ Yes |
| 5 | Web Scraping & Playwright | `web/connector.py`, `playwright.py`, `eea_utils.py` | 🟡 Medium | ✅ Yes |
| 6 | Connector Stability & Healthcheck | `connectors_state.py`, `monitoring/tasks.py` | 🟡 Medium | ⚠️ Partial |
| 7 | Diacritic Tag Resolver | `backend/onyx/natural_language_processing/` (DiacriticTagResolver) | 🟡 Medium | ✅ Yes |
| 8 | PDF Indexing Improvements | `backend/onyx/connectors/file/` | 🟢 Low | ⚠️ Partial |
| 9 | Citation & Search Fixes | citation backtracking fix, full content to packets | 🟢 Low | ⚠️ Partial |
| 10 | UI UX Improvements | personas tooltips, connector sort, date filter, knowledge set sort | 🟢 Low | ❌ No |
| 11 | Docker / Deployment EEA | `deployment/docker_compose/eea/` | 🟡 Medium | ✅ Yes |
| 12 | Security Patches & Upstream Fixes | CVE patches, libgnutls, SMTP auth guard, connector deletion | 🟢 Low | ❌ No |

---

## II. Functional Specifications

### Feature 1 — Langfuse Tracing & LLM Metadata
**Author**: Zoltan Szabo

**Goal**: Inject comprehensive Langfuse observability into every LLM call with user context, session IDs, and feedback synchronization. This enables monitoring AI usage per user and conversation in the EEA Langfuse instance.

**Logic**:
1. `eea_utils.py` provides `get_langfuse_callback_handler(metadata)` → constructs a `CallbackHandler` with `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST` env vars.
2. Metadata dict includes: `user_id` (stripped of any prefix), `session_id` (from chat session), `trace_name` (first 200 chars of user message), `trace_id`.
3. `chat_llm.py` calls `add_metadata_to_llm()` to inject metadata into every `litellm.completion()` call.
4. `run_graph.py` (Deep Research) passes the Langfuse handler through `GraphConfig` to all agent steps.
5. `langfuse_tracing_processor.py` uses `extra_metadata`/`tags` from the LiteLLM call to set custom span names. Clarification steps are named `Clarification needed for "<original_question>"`.
6. Feedback is synced back to Langfuse via score API (commit `15d51857`).
7. **Batch prevention**: `LANGFUSE_FLUSH_AT=1` env var set to avoid losing traces in batch flush (commit `84ec36f2`).

**Dependencies**: `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST` env vars. `langfuse` Python package. `fast_chat_turn.py` for session ID retrieval.

**Sticky Logic** ⚠️: The `LANGFUSE_FLUSH_AT=1` setting and the `trace_name`/`trace_id` construction logic MUST remain identical. Any upstream change to how `metadata` is passed to `litellm.completion()` is a "Logic Violation" — re-apply from commits `bdc09551`, `8d3f8e1a`, `84ec36f2`.

**Key Commits**: `84ec36f2`, `8d3f8e1a`, `43f53ec1`, `0f5e4443`, `bdc09551`, `15d51857`

---

### Feature 2 — EEA Rebranding (AI Hub)
**Author**: Zoltan Szabo

**Goal**: Replace all Onyx/Danswer/GPT Lab branding with EEA-specific "AI Hub" identity including custom logo, footer links, and color scheme.

**Logic**:
1. `constants.py`: `APPLICATION_NAME = "EEA AI Hub"` (was "GPT Lab", then "AI Hub").
2. `EEA_Logo.tsx`: Custom SVG component for `EEA_logo_compact_EN.svg`.
3. `Header.tsx`: Replaces title with EEA Logo component.
4. `Footer.tsx`: EEA privacy policy and architecture page links.
5. Login & Signup pages: EEA logo, custom disclaimer text, no 3rd-party resource loading.
6. Auth pages: `fixed logo on auth pages` (commit `76b5cc27`) — logo patched on NextAuth pages.
7. History sidebar: typo fix on branding label (commit `4e4c1840`).

**Dependencies**: `EEA_logo_compact_EN.svg` static asset. `constants.py` APPLICATION_NAME.

**Key Commits**: `bcdaf71c`, `7ba9c9fe`, `4b42a026`, `6ba660c3`, `76b5cc27`, `a9d2b7aa`

---

### Feature 3 — User Disclaimer Modal
**Author**: Zoltan Szabo

**Goal**: Display a legal/usage disclaimer modal to users upon first login. Admins can configure the disclaimer text from the admin panel.

**Logic**:
1. Backend: New DB model `EEADisclaimer` (or similar) with `text` field. API endpoint at `/api/eea/disclaimer` (GET/POST).
2. `eea_utils.py`: `get_eea_custom_settings()` fetches all EEA-specific config including the disclaimer.
3. Frontend: `UserDisclaimerModal.tsx` checks `localStorage` for a "disclaimerAcknowledged" flag. If not set, shows the modal on login.
4. Admin page: `web/src/app/admin/eea_config/disclaimer/page.tsx` — text editor for the disclaimer.
5. Disclaimer shown as a modal overlay (not a blocking page) with an "I Agree" button.

**Dependencies**: Backend model requires DB migration. `eea_utils.py` custom settings fetcher. LocalStorage flag.

**Key Commits**: `f49349d3`, `d19b3cc8`, `65fbca40`, `2824a873`, `49c4b53c`, `921689a1`, `eb460341`

---

### Feature 4 — Custom Admin Pages (EEA Config)
**Author**: Zoltan Szabo

**Goal**: Allow EEA admins to create custom CMS-style pages (e.g., "What's New", privacy statement) that appear as navigable pages in the user dropdown and admin UI.

**Logic**:
1. `web/src/app/admin/eea_config/pages/` — Next.js admin section with CRUD for pages.
2. Pages have: `title` (used as URL slug), `content` (markdown), `is_public` flag. Public pages are accessible without admin role.
3. `hooks.tsx` — React hooks for fetching/mutating pages via API.
4. `lib.tsx` — shared helpers for the page admin section.
5. User popover `added customizable pages to user popover` (commit `87536313`) — pages appear as links in the profile dropdown.
6. Privacy statement page added (commit `62a49359`) — non-EE-restricted.
7. Backend: Pages stored in DB, served via `/api/eea/pages` endpoint.

**Dependencies**: Backend model + API, `eea_utils.py` settings fetch, user popover component.

**Key Commits**: `836e3c3d`, `3dd2c77b`, `875363133`, `c26ce64b7`, `62a49359`, `dfd19cfe`

---

### Feature 5 — Web Scraping & Playwright Enhancements
**Author**: Zoltan Szabo

**Goal**: Improve web connector reliability with selector-based element removal, sitemap `lastmod` filtering, SSL error tolerance, and Playwright stability fixes.

**Logic**:
1. `eea_utils.py`: `remove_by_selector(html, selectors)` — removes HTML elements matching CSS selectors before indexing (avoids indexing nav/footer noise).
2. `eea_utils.py`: `get_document_updated_at_batch(urls, sitemaps)` — checks `lastmod` from sitemap XML to skip re-indexing unchanged pages.
3. `web/connector.py`: `get_ssl=False` option for connectors where SSL cert is expired (commit `529f3e5e`).
4. `web/connector.py`: Auto-discover sitemap via common paths if not configured (`acdead91`). Fallback to `ultimate_sitemap_parser` library if primary sitemap yields no URLs.
5. `playwright.py`: Added configurable timeouts (`added timeout for playwright`, commit `fa04e343`). Fixed process stopping by checking `process.returncode` before calling `process.terminate()` — avoids `playwright-python` issue #2238, commit `199a9944`.
6. `headless chrome flags`: Small fix on headless chrome flags (commit `small fix on headless chrome flags`).
7. Docker: `added tini in the image` (commit `79c4c6b0`) — tini as PID 1 to properly handle zombie playwright processes.

**Dependencies**: `ultimate_sitemap_parser` Python package. `playwright` Python package. `tini` in Dockerfile.

**Sticky Logic** ⚠️: The playwright process-stopping logic (checking `returncode` before `terminate()`) MUST remain. Upstream may update `playwright.py` and remove this guard.

**Key Commits**: `199a9944`, `fa04e343`, `529f3e5e`, `acdead91`, `ab5e4cd2`

---

### Feature 6 — Connector Stability & Healthcheck
**Author**: Zoltan Szabo

**Goal**: Prevent connectors from being auto-paused on single failures, add a healthcheck that only fails after 2 consecutive failures, and fix memory watchdog process identification.

**Logic**:
1. `connectors_state.py`: Fixed tuple mapping for `cc_pair_to_document_cnt` to handle optional `search_settings` returned from DB. Prevents tuple-unpack crashes.
2. `monitoring/tasks.py` (Celery watchdog): Map `onyx.background.celery.versioned_apps.beat` → `"beat"` to fix process duplication in memory monitoring.
3. Connector healthcheck logic (`35581db8`, `a52ea18c`): Only mark connector as failed if there are **2 consecutive** failed indexing attempts, not just 1.
4. `f8696402`: Updated healthcheck to track consecutive failure count.
5. `0a31435f`: Additional fix for connectors healthcheck edge case.
6. `Don't pause the failed connectors` (commit `0a4e3635`): Removed auto-pause behavior on connector failure.

**Dependencies**: DB schema for consecutive failure tracking. Celery beat configuration.

**Key Commits**: `4636caca` (upstream ref), `35581db8`, `a52ea18ca`, `f8696402`, `0a4e3635`, `0a31435f`

---

### Feature 7 — Diacritic Tag Resolver
**Author**: Zoltan Szabo

**Goal**: Guardrail to restore diacritics in Romanian/other language tags that get stripped during text normalization, ensuring accurate document tagging and search.

**Logic**:
1. `DiacriticTagResolver` class in `backend/onyx/natural_language_processing/` — built as a registry from document tags at index time.
2. On query: normalizes input (strips diacritics), looks up canonical tag with diacritics restored.
3. Configurable latency tracking via YAML config (toggled via `DIACRITIC_RESOLVER_LOGGING` env var).
4. Class-based implementation (not functional) for streaming support and superior normalization. Registry is built excluding input noise tokens.
5. Fallback: if resolver can't restore, returns original tag unchanged.

**Dependencies**: Indexing pipeline (registry must be built at index time). YAML config for logging toggle.

**Sticky Logic** ⚠️: The class-based architecture with streaming must not be simplified to a functional approach. The registry exclusion logic is proprietary EEA logic.

**Key Commits**: Commits in `ef1bdbea` conversation era (see conversation history).

---

### Feature 8 — PDF Indexing Improvements
**Author**: Zoltan Szabo

**Goal**: Fix PDF title extraction and improve handling of special characters in filenames during indexing.

**Logic**:
1. `fix the names of indexed pdf files` (commit `81f1893b`): Extract actual PDF title from metadata instead of filename.
2. `updated pdf indexing` (commit `14679af5`): Handle edge cases in PDF text extraction.
3. `remove special characters in filenames` (commit referenced in log): Sanitize filenames before indexing.
4. `allow indexing of text files` (commit `79d4a2a2`): Extend file connector to accept `.txt` files.
5. `fallback if we can't figure out the encoding from the model name` (commit `91a31c63`): LLM encoding detection fallback for Llama-3.1 and similar models.

**Key Commits**: `81f1893b`, `14679af5`, `79d4a2a2`, `91a31c63`

---

### Feature 9 — Citation & Search Algorithm Fixes
**Author**: Zoltan Szabo + upstream-merged

**Goal**: Prevent catastrophic backtracking in the citation regex and add full document content to search tool packets.

**Logic**:
1. `feat(citation): avoid catastrophic backtracking` (commit `96a33e3b`): Fix in citation regex to avoid polynomial time matching on malformed citations.
2. `feat(search_tool): Add full content to search tool packets` (commit `6ad00f66`): Include full document content (not just excerpts) in search tool response packets for better LLM context.
3. `Replace special brackets used for citations` (commit `325a63ec`): Replace `【】` with standard brackets to avoid encoding issues.

**Key Commits**: `96a33e3b`, `6ad00f66`, `325a63ec`

---

### Feature 10 — UI/UX Improvements
**Author**: Zoltan Szabo

**Goal**: Various improvements to the admin and user-facing UI for better EEA usability.

**Logic**:
1. Personas tooltips (commit `83e33d7e`) — hover tooltips on persona cards.
2. Alphabetically sort knowledge sets (commit `23688f51`).
3. New date filter options in search (commit `ad369a6d`).
4. Show actual default model for personas (commit `206c9c42`).
5. Fixed sort on connectors admin page (commit `995cc5a1`).
6. Connector multi-select improvements.
7. `add fallback value to timeout` (commit `e74cb042`) — avoid undefined timeout crashes.
8. `custom fix for chatting with 'my documents'` (commit `fb35ada6`).
9. `added option to reindex a user file (only for admin users)` (commit `1ec55734`).
10. `quickfix for changing password` (commit `b303e042`).

**Key Commits**: `83e33d7e`, `23688f51`, `ad369a6d`, `995cc5a1`, `e74cb042`, `fb35ada6`

---

### Feature 11 — Docker / Deployment (EEA-Specific)
**Author**: Zoltan Szabo

**Goal**: Maintain a complete, self-contained Docker Compose configuration for EEA-specific deployment with resource limits, network policies, and EEA environment defaults.

**Logic**:
1. `deployment/docker_compose/eea/docker-compose.yml` — EEA-specific compose file with service configs, volume mounts, network policies.
2. `.env.example` — EEA-specific env var template with Langfuse, SMTP, and custom settings pre-filled.
3. `docker-compose.override.yml` — Resource limit overrides (`set the resource limits from an env`).
4. Backend `Dockerfile`: Updated for `tini` as PID 1, custom Python deps including EEA-specific packages.
5. Nginx configuration: Custom volume mounts for EEA static assets (commit `9150a8c1`).
6. Vespa backup image: Updated backup job configs (commit `60d0911c`).
7. Helm chart updates: EEA deployment configs in `deployment/helm/` (commit `3c968b2f`).
8. `update network policies` (commit `1c4f9128`) — Kubernetes NetworkPolicy for EEA deployment.
9. Jenkins CI: `updated jenkinsfile` — EEA-specific CI pipeline.

**Sticky Logic** ⚠️: The `LANGFUSE_FLUSH_AT=1` in `.env.example` must be preserved. The `tini` entrypoint in Dockerfile is required for playwright process management.

**Key Commits**: `95f44e1a`, `a48c5275`, `b89157b4`, `9150a8c1`, `60d0911c`, `79c4c6b0`

---

### Feature 12 — Security Patches & Upstream Fixes
**Author**: Zoltan Szabo

**Goal**: Apply security patches not yet in upstream (CVE fixes, dependency upgrades, SMTP auth guard).

**Logic**:
1. `don't try to authenticate in case SMTP_USER & SMTP_PASS are not set` (commit `dccd9888`): Guards SMTP auth call to prevent crash when credentials not configured.
2. CVE-2025-55182 fixes (commits `05e9a42c`, `ef922c13`, `02d84bd2`): Three-pass patch for a specific CVE.
3. `updated to libgnutls30=3.7.9-2+deb12u3` (commit `b658f5c5`): Pin security-patched version.
4. `applied security patches` (commit `cf277efc`): Batch security patch application.
5. `pessimistic disconnect handling` (commit `babac3da`): DB connection pessimistic disconnect config to handle stale connections.
6. `workaround for not reachable indexing_model_server using tenacity` (commit `dc3ddeb9`): Retry logic for model server unreachability.

**Key Commits**: `dccd9888`, `05e9a42c`, `ef922c13`, `02d84bd2`, `b658f5c5`, `babac3dad`

---

### Feature 13 — SharePoint Connector Enhancement
**Author**: Matthieu Boret (matthieu.boret@fr.clara.net)

**Goal**: Update SharePoint connector behavior for EEA-specific SharePoint environments.

**Logic**: `Update sharepoint connector behavior` (commit `715e1f37`) — specific change to how the SharePoint connector authenticates or processes documents for the EEA SharePoint instance.

**Key Commits**: `715e1f37`

---

## III. Sticky Logic Registry

> Code segments that **MUST remain identical** regardless of upstream changes.

| ID | Location | Invariant | Reason |
|---|---|---|---|
| SL-01 | `eea_utils.py`: `get_langfuse_callback_handler()` | Full function body | Core Langfuse integration entrypoint |
| SL-02 | `chat_llm.py`: metadata injection call | `metadata` parameter in `litellm.completion()` | Any upstream change removing this is a Logic Violation |
| SL-03 | `run_graph.py`: GraphConfig Langfuse handler | LangfuseCallbackHandler in agent graph | Deep Research tracing depends on this |
| SL-04 | `langfuse_tracing_processor.py`: Clarification Step naming | `"Clarification needed for "<original_question>""` | Langfuse dashboard naming convention |
| SL-05 | `docker-compose.yml` / `.env.example` | `LANGFUSE_FLUSH_AT=1` | Prevents trace loss on process exit |
| SL-06 | `playwright.py`: process stop guard | `if process.returncode is None: process.terminate()` | Prevents playwright zombie processes (GH #2238) |
| SL-07 | `Dockerfile`: tini entrypoint | `ENTRYPOINT ["/usr/bin/tini", "--"]` | Required for playwright subprocess reaping |
| SL-08 | `DiacriticTagResolver`: registry build | Class-based, streaming-compatible | EEA proprietary normalization logic |
| SL-09 | Healthcheck logic: consecutive failure threshold | 2 consecutive failures before marking unhealthy | Prevents connector auto-pause on transient errors |

---

## IV. Re-implementation Guide

> Step-by-step instructions to recreate each feature block if the original files are missing or heavily refactored in a new upstream.

---

### RG-01: Langfuse Tracing (CRITICAL — re-implement first)

**Prompt for re-implementation**:

> "Create `backend/onyx/utils/eea_utils.py` with a `get_langfuse_callback_handler(metadata: dict) -> CallbackHandler` function. It must import `from langfuse.callback import CallbackHandler` and build the handler using `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST` from `os.environ`. The `metadata` dict must include keys: `user_id` (strip the `__user__` prefix if present), `session_id`, `trace_name` (first 200 chars of user message), `trace_id` (UUID).
>
> Next, in `backend/onyx/llm/chat_llm.py`, find the `litellm.completion()` call and add a `metadata=` argument populated by `get_langfuse_callback_handler()`.
>
> In `backend/onyx/agents/agent_search/run_graph.py`, add the Langfuse handler to the `GraphConfig`. Ensure it propagates through all agent steps including clarification.
>
> In `backend/onyx/tracing/langfuse_tracing_processor.py`, add logic so that if `'Clarification'` is in the trace metadata, the span name is set to `Clarification needed for "<original_question>"`.
>
> Set `LANGFUSE_FLUSH_AT=1` in the EEA `.env` file to prevent batch loss."

**Verification**: Check Langfuse dashboard shows user_id, session_id on every trace. Deep Research sub-spans must appear as children of the parent trace.

---

### RG-02: EEA Rebranding

**Prompt for re-implementation**:

> "In `backend/onyx/configs/constants.py`, set `APPLICATION_NAME = 'EEA AI Hub'`. Create `web/src/components/EEA_Logo.tsx` as an SVG component loading `/EEA_logo_compact_EN.svg`. Update `Header.tsx` to use `<EEALogo />` instead of the default Onyx logo. In `Footer.tsx`, replace footer links with EEA privacy policy (`https://www.eea.europa.eu/en/legal/eea-data-policy`) and architecture page links. In all auth pages (login, signup), replace the logo and ensure no external scripts (fonts, analytics) are loaded by adding `next.config.js` CSP headers."

---

### RG-03: User Disclaimer Modal

**Prompt for re-implementation**:

> "Create a DB model `EEAConfig` with a `disclaimer_text: str` field and a migration. Add GET/POST endpoints at `/api/eea/disclaimer`. Create `web/src/app/admin/eea_config/disclaimer/page.tsx` with a text editor that POSTs to this endpoint. Create `web/src/components/UserDisclaimerModal.tsx` — a modal that reads `localStorage.getItem('eea_disclaimer_acknowledged')`. If null, fetch the disclaimer text from the API and display it with an 'I Acknowledge' button that sets the localStorage key. Mount this modal in `_app.tsx` or the root layout wrapping all authenticated pages."

---

### RG-04: Custom Admin Pages

**Prompt for re-implementation**:

> "Create a DB model `EEAPage` with `title: str` (used as URL slug), `content: str` (markdown), `is_restricted: bool`. Add CRUD endpoints at `/api/eea/pages`. Create `web/src/app/admin/eea_config/pages/` with Next.js pages for listing, creating, editing, and viewing pages. In `web/src/components/layout/UserDropdown.tsx` (or equivalent user popover), fetch and render EEA pages as dropdown links. Pages with `is_restricted=False` should be accessible without admin role."

---

### RG-05: Playwright & Web Connector Stability

**Prompt for re-implementation**:

> "In `backend/onyx/utils/playwright.py`, wrap all `process.terminate()` calls in a guard: `if process.returncode is None: process.terminate()`. Add a configurable timeout (default 30s) for page load. In `backend/onyx/connectors/web/connector.py`, add `ignore_ssl_errors=True` option and implement sitemap auto-discovery: try `/sitemap.xml`, `/sitemap_index.xml`, and robots.txt. If the primary sitemap parser returns 0 URLs, fall back to `ultimate_sitemap_parser`. Implement `remove_by_selector(html, selectors)` in `eea_utils.py` and call it before passing HTML to the indexer. In the backend `Dockerfile`, add `tini` as the entrypoint: `RUN apt-get install -y tini` and `ENTRYPOINT ['/usr/bin/tini', '--']`."

---

### RG-06: Connector Healthcheck

**Prompt for re-implementation**:

> "In the connector state tracker, add a `consecutive_failure_count: int` field (DB-backed or in-memory with Redis). On each indexing failure, increment it. Only mark a connector as unhealthy if `consecutive_failure_count >= 2`. On success, reset to 0. Remove any auto-pause logic that suspends connectors after a single failure. Update `backend/onyx/server/manage/connectors_state.py` to handle the optional `search_settings` tuple safely using `if settings else default_value`."

---

### RG-07: Diacritic Tag Resolver

**Prompt for re-implementation**:

> "Create `backend/onyx/natural_language_processing/diacritic_resolver.py` with a `DiacriticTagResolver` class. Constructor accepts a list of canonical tags (with diacritics). It builds a registry by normalizing each canonical tag (via `unicodedata.normalize('NFD', tag).encode('ascii', 'ignore').decode()` to strip diacritics). The `resolve(query_tag)` method normalizes the input, looks up the canonical tag, and returns it. If not found, return the original. Add configurable latency logging via `DIACRITIC_RESOLVER_LOGGING` env var. The class must be stateful (registry built once) and thread-safe (use a frozen dict or lock)."

---

## V. Gap Analysis: Smart-Sync Protection Rules

| Feature | Covered by smart-sync.md? | Gap / Action Needed |
|---|---|---|
| Langfuse metadata injection | ✅ Yes — Section "Feature-Specific Rules: Langfuse & LiteLLM" covers call sites | Partially: `run_graph.py` Deep Research path explicitly mentioned. Clarification step naming in `langfuse_tracing_processor.py` is covered in "Onyx Tracing Processor" section. |
| EEA Rebranding | ❌ Not mentioned | **GAP**: Add guard: "If `constants.py` `APPLICATION_NAME` is changed to 'Onyx' by upstream, revert to 'EEA AI Hub'." |
| Disclaimer Modal | ❌ Not mentioned | **GAP**: Add guard for `web/src/app/admin/eea_config/` directory — protect from deletion. |
| Custom Pages | ❌ Not mentioned | **GAP**: Add protection rule for `eea_config/pages/` route tree. |
| Playwright stability | ❌ Not mentioned | **GAP**: Add rule: "After any upstream change to `playwright.py`, verify the `returncode` guard and timeout are present." |
| Connector Healthcheck | ❌ Not mentioned | **GAP**: Add rule: "Consecutive failure threshold must remain 2. Do not merge upstream changes that add auto-pause behavior." |
| Diacritic Resolver | ❌ Not mentioned | **GAP**: Add rule for `DiacriticTagResolver` — protect from upstream refactor that restructures `natural_language_processing/`. |
| LANGFUSE_FLUSH_AT=1 | Partially (env var mentioned) | **GAP**: Add explicit check: after sync, verify `.env.example` contains `LANGFUSE_FLUSH_AT=1`. |
| tini Dockerfile entrypoint | ❌ Not mentioned | **GAP**: Add Dockerfile guard: "Verify ENTRYPOINT uses tini after upstream Dockerfile changes." |

**Recommended addition to `smart-sync.md`**:
```
## EEA Identity Guards
After any upstream sync:
1. Verify `constants.py` APPLICATION_NAME = 'EEA AI Hub'
2. Verify `web/src/app/admin/eea_config/` directory exists and is unchanged
3. Verify `deployment/docker_compose/eea/` is not overwritten
4. Verify backend Dockerfile ENTRYPOINT uses tini
5. Verify `.env.example` contains LANGFUSE_FLUSH_AT=1
6. Verify playwright.py contains the returncode guard
7. Verify connector healthcheck threshold is 2 consecutive failures
```
