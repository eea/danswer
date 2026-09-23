# Onyx – What's New for Users (v3.2.1 → v4.3.9)

A curated compilation of all user-facing changes, features, performance enhancements, connector improvements, and noticeable bug fixes between **v3.2.1** and **v4.3.9**, presented in reverse chronological order (newest first).

---

## Table of Contents

- [v4.3 Series (v4.3.0 → v4.3.9)](#v43-series-v430--v439)
- [v4.2 Series (v4.2.0 → v4.2.8)](#v42-series-v420--v428)
- [v4.1 Series (v4.1.0 → v4.1.13)](#v41-series-v410--v4113)
- [v4.0 Series — Major Release (v4.0.0 → v4.0.14)](#v40-series--major-release-v400--v4014)
- [v3.3 Series (v3.3.0 → v3.3.14)](#v33-series-v330--v3314)
- [v3.2 Series (v3.2.2 → v3.2.16)](#v32-series-v322--v3216)

---

## v4.3 Series (v4.3.0 → v4.3.9)

### 🌟 Headline Features

- **Direct Document Hierarchy Links** ([#12295](https://github.com/onyx-dot-app/onyx/pull/12295), [`06f586a2d8`](https://github.com/onyx-dot-app/onyx/commit/06f586a2d8af114cc07754de4478e789a931c658)) — You can now copy direct, permalink URLs to document folder hierarchy nodes in navigation trees, making sharing specific sections much easier.
- **Enterprise SIEM Audit Logging** ([#12219](https://github.com/onyx-dot-app/onyx/pull/12219), [`164bab645c`](https://github.com/onyx-dot-app/onyx/commit/164bab645c94783896140a35212e7522e86bca87)) — Admins can export structured audit logs to SIEM systems for enterprise-grade security and compliance monitoring.
- **Mobile Experience Overhaul** ([#12057](https://github.com/onyx-dot-app/onyx/pull/12057), [`44b7a5c6c2`](https://github.com/onyx-dot-app/onyx/commit/44b7a5c6c2e9425121b4fdfdba8c1fdafac13879)) — Major modernization of the React Native mobile app with shared design tokens, polished native typography, tactile buttons, and responsive input layouts.
- **Session-Scoped Tool & Code Approvals** ([#11819](https://github.com/onyx-dot-app/onyx/pull/11819), [`c3ef061021`](https://github.com/onyx-dot-app/onyx/commit/c3ef06102192db3d6df7a4e561c3488966d78379)) — Interactive confirmation workflows now support session-scoped approvals when agents invoke external tools or code sandboxes.
- **Enterprise Database TLS & mTLS** ([#12321](https://github.com/onyx-dot-app/onyx/pull/12321), [`8d3f186cd2`](https://github.com/onyx-dot-app/onyx/commit/8d3f186cd29fb8244ff7422660d582de06e39fc4)) — Full TLS and mutual TLS (client certificate) support for PostgreSQL connections with server certificate verification.

### ⚡ Performance & Speed Improvements

- **Real-Time Document Ingest Metrics** ([#12333](https://github.com/onyx-dot-app/onyx/pull/12333), [`2415cff137`](https://github.com/onyx-dot-app/onyx/commit/2415cff1376af2d046836692bebd6e22326946af)) — Administrators have live visibility into document processing stages, throughput metrics, and residual queue sizes.
- **Background Chat Retention Cleanup** ([#12959](https://github.com/onyx-dot-app/onyx/pull/12959), [`03003a60d4`](https://github.com/onyx-dot-app/onyx/commit/03003a60d409e5de4c0fa03d23734141112302bf)) — Chat message TTL cleanup is now isolated and batched off the primary processing queue, eliminating chat slowdowns during automated maintenance.
- **Hybrid Retrieval Enhancements** ([#9844](https://github.com/onyx-dot-app/onyx/pull/9844), [`02671937fb`](https://github.com/onyx-dot-app/onyx/commit/02671937fbd1852d33f9e12cedc5de77fcfd167a)) — Tuned hybrid search weighting and candidate selection for faster semantic document matching.

### ✨ User Experience & Connector Enhancements

- **Consistent Prompt Placeholders** ([#13142](https://github.com/onyx-dot-app/onyx/pull/13142), [`1da679cefc`](https://github.com/onyx-dot-app/onyx/commit/1da679cefc96165c6b9b64c3bc769584b88f88c2)) — Dynamic prompt placeholders (e.g. user info, date, context) now resolve consistently across all custom agent prompt types.
- **Model Picker Provider Sections** ([#12962](https://github.com/onyx-dot-app/onyx/pull/12962), [`6a36b4835c`](https://github.com/onyx-dot-app/onyx/commit/6a36b4835c4dd4f7f7ede2d60ab39f9d40280c1e)) — AI model dropdowns in chat and admin settings are now organized into clearly labeled provider sections.
- **Windows ARM64 Desktop App** ([#13036](https://github.com/onyx-dot-app/onyx/pull/13036), [`fa2d426f90`](https://github.com/onyx-dot-app/onyx/commit/fa2d426f906a8cdf60b46c65e55471bee08bc593)) — Dedicated desktop client builds for Windows on ARM64 processors (Surface Pro, Snapdragon laptops).
- **Nebius AI Provider Support** ([#12955](https://github.com/onyx-dot-app/onyx/pull/12955), [`eec00d21b0`](https://github.com/onyx-dot-app/onyx/commit/eec00d21b0721d06af51a7290b6a1c3fb7352af0)) — Native provider tile and logo integration for Nebius AI models.
- **Deep Linking for Google Drive** ([#12895](https://github.com/onyx-dot-app/onyx/pull/12895), [`0fa8f23334`](https://github.com/onyx-dot-app/onyx/commit/0fa8f2333451abab8c809b29689e0b9032344efa)) — Smart URL resolver maps ambiguous Google Drive links directly to their indexed documents in search results.

### 🐛 Noticeable Bug Fixes & Patch Highlights

- **SharePoint Group Permissions (v4.3.9, v4.3.7)** ([#13114](https://github.com/onyx-dot-app/onyx/pull/13114), [`038d9d18f1`](https://github.com/onyx-dot-app/onyx/commit/038d9d18f102344ddb15b03705ebeb38e1a90572)) — Fixed a critical permission sync issue where SharePoint security group access was not properly inherited across sub-items.
- **Empty GitHub Repositories (v4.3.8)** ([#13083](https://github.com/onyx-dot-app/onyx/pull/13083), [`606cbdd9e9`](https://github.com/onyx-dot-app/onyx/commit/606cbdd9e93053625c496dbf91a6c1be1d19c1e1)) — Indexing no longer throws exceptions or halts ingestion when encountering empty Git repositories.
- **Slack Bot Agent Permissions (v4.3.7)** ([#12988](https://github.com/onyx-dot-app/onyx/pull/12988), [`06c2a28d01`](https://github.com/onyx-dot-app/onyx/commit/06c2a28d0181cede5a89a328427b092a7a67d4a8)) — The Slack bot now strictly validates whether the asking user has permission to use a specific agent before answering.
- **SCIM Entra ID Member Deletion (v4.3.4, v4.3.5)** ([#12439](https://github.com/onyx-dot-app/onyx/pull/12439), [`cf20127d3f`](https://github.com/onyx-dot-app/onyx/commit/cf20127d3f3738c9511e8c2c0c642386110bd341)) — Fixed Microsoft Entra ID (Azure AD) SCIM sync failing when removing group members, and handled duplicate user creation gracefully with HTTP 409 conflict responses.
- **Code Interpreter Naming Fix (v4.3.x)** ([#13242](https://github.com/onyx-dot-app/onyx/pull/13242), [`1afe6fb4c0`](https://github.com/onyx-dot-app/onyx/commit/1afe6fb4c01ab2b39868264fc44c57dd399cc58c)) — Renamed the internal Code Interpreter function call off OpenAI's reserved `"python"` keyword, resolving unexpected tool execution failures.

---

## v4.2 Series (v4.2.0 → v4.2.8)

### 🌟 Headline Features

- **Dynamic Browser Tab Titles** ([#11832](https://github.com/onyx-dot-app/onyx/pull/11832), [`fcc9044b48`](https://github.com/onyx-dot-app/onyx/commit/fcc9044b485deff62f4e1396c17b2126bd5ff5e9)) — Browser tabs now dynamically display the active chat conversation or search query name instead of a static title.
- **Expanded Autonomous Agent Actions (Craft)** ([#11798](https://github.com/onyx-dot-app/onyx/pull/11798), [`a2b11208b4`](https://github.com/onyx-dot-app/onyx/commit/a2b11208b47394674290062cfdb363bccc00c9ff)) — Agents can perform richer interactive actions directly inside connected apps, including Slack, Google Drive, and Linear.
- **Paginated In-App Notifications** ([#12513](https://github.com/onyx-dot-app/onyx/pull/12513), [`86215ddb6b`](https://github.com/onyx-dot-app/onyx/commit/86215ddb6b9b029f9ec39446ed323ee304639171)) — The notifications center now loads smoothly with pagination, preventing freezes for active users with large notification histories.
- **Opal Design System Upgrade** ([#11823](https://github.com/onyx-dot-app/onyx/pull/11823), [`679193dcc6`](https://github.com/onyx-dot-app/onyx/commit/679193dcc62695456cc419c0fb4b70ab5a9d8e9b)) — Refined UI surfaces featuring modern rounded cards, clean drop shadows, and robust z-index management preventing modal clipping.

### ⚡ Performance & Speed Improvements

- **Fluid Chat Streaming** ([#12566](https://github.com/onyx-dot-app/onyx/pull/12566), [`bf30f2a768`](https://github.com/onyx-dot-app/onyx/commit/bf30f2a768a2c0ae26e22330c9579ee1a6f555c0)) — Optimized client-side token consumption for smoother token-by-token streaming with zero perceived stutter or bursting.
- **Faster Connector Resumes** ([#9812](https://github.com/onyx-dot-app/onyx/pull/9812), [`fa5b90df92`](https://github.com/onyx-dot-app/onyx/commit/fa5b90df927cc0130ede30c4bc58191adeddde0f)) — Resuming paused connectors now starts immediately without re-checking unchanged documents.

### ✨ User Experience & Connector Enhancements

- **Model Configuration Keying** ([#12831](https://github.com/onyx-dot-app/onyx/pull/12831), [`fc162718a6`](https://github.com/onyx-dot-app/onyx/commit/fc162718a6af80b57d8345e87846c6a52c5597da)) — Model selector state is keyed by configuration ID, preventing stale model selections when switching between agents.
- **Public API Documentation Gating** ([#11837](https://github.com/onyx-dot-app/onyx/pull/11837), [`590f972768`](https://github.com/onyx-dot-app/onyx/commit/590f97276831639564d6df24e143cacb7de553c9)) — Administrators can toggle public API documentation and OpenAPI schemas on or off via configuration.
- **SharePoint Role Localization** ([#13175](https://github.com/onyx-dot-app/onyx/pull/13175), [`d985b6a804`](https://github.com/onyx-dot-app/onyx/commit/d985b6a804d98b52a5e93a774f65459b235ec7f6)) — SharePoint connector properly recognizes localized permission role names across non-English Microsoft 365 tenants.

### 🐛 Noticeable Bug Fixes & Patch Highlights

- **Multi-Model Compare Flow (v4.2.6)** ([#12794](https://github.com/onyx-dot-app/onyx/pull/12794), [`da94192d6a`](https://github.com/onyx-dot-app/onyx/commit/da94192d6a45066a3809460a9b29a7b3ddc989dc)) — Submitting follow-up prompts in side-by-side comparison mode now reliably routes prompts to all active comparison models.
- **Tablet & Medium Screen Sidebar (v4.2.0)** ([#9870](https://github.com/onyx-dot-app/onyx/pull/9870), [`9dbe7acac6`](https://github.com/onyx-dot-app/onyx/commit/9dbe7acac6eb920479a9a8b21b3749d7a4c02c93)) — Fixed layout overflow where the sidebar overlapped chat content on medium screen widths and tablets.
- **Rate Limit Modal Polish** ([#9978](https://github.com/onyx-dot-app/onyx/pull/9978), [`67b7d115db`](https://github.com/onyx-dot-app/onyx/commit/67b7d115db599d21d67b9896d990c885848558b8)) — Clean modal footer and button alignment when users reach their token or query quota.
- **Root Document Node Access** ([#12889](https://github.com/onyx-dot-app/onyx/pull/12889), [`20d57ccb0e`](https://github.com/onyx-dot-app/onyx/commit/20d57ccb0e4081aed0acf4f00aaa8594cee685b1)) — Fixed public visibility permissions on root folder hierarchy nodes.

---

## v4.1 Series (v4.1.0 → v4.1.13)

### 🌟 Headline Features

- **Isolated Code & Tool Execution Sandboxes** ([#12443](https://github.com/onyx-dot-app/onyx/pull/12443), [`23f5b94929`](https://github.com/onyx-dot-app/onyx/commit/23f5b949295ff2dfa959841c009b46212e318348)) — Agent code execution and tool runs are isolated within configurable Docker Compose and Kubernetes sandbox backends.
- **Langfuse Observability & Tracing** ([#11247](https://github.com/onyx-dot-app/onyx/pull/11247), [`6f46c470e7`](https://github.com/onyx-dot-app/onyx/commit/6f46c470e7839a7ca3c255b06feb293f7f8210d8)) — Native integration with Langfuse to trace LLM calls, track token costs, and monitor response quality by user and session.
- **Gemini 3 Pro Image Generation** ([#13289](https://github.com/onyx-dot-app/onyx/pull/13289), [`7c93500c91`](https://github.com/onyx-dot-app/onyx/commit/7c93500c91e7800db8140f9a14365cb969e6fc21)) — Added full support for the latest Gemini 3 Pro image generation models directly inside the chat interface.
- **Initial Bulk Indexing Mode** ([#11248](https://github.com/onyx-dot-app/onyx/pull/11248), [`a29b945765`](https://github.com/onyx-dot-app/onyx/commit/a29b94576583e908180c6de861774ffe538bff47)) — Document push webhooks can be deferred during initial data ingest, cutting initial connector sync times significantly.

### ⚡ Performance & Speed Improvements

- **Reduced Document Processing Memory** ([#12059](https://github.com/onyx-dot-app/onyx/pull/12059), [`dc202e295a`](https://github.com/onyx-dot-app/onyx/commit/dc202e295adce69acdbbd71510c1ce04fe3ea9bb)) — Streamlined document chunking pipeline, reducing memory spikes when processing large manuals, spreadsheets, and PDFs.
- **Query Cache Enhancements** ([#10594](https://github.com/onyx-dot-app/onyx/pull/10594), [`43641a9914`](https://github.com/onyx-dot-app/onyx/commit/43641a9914e3415c2c7e8382d682f83c879e2dc3)) — Frequent search queries and recurring agent tool calls are cached with lower round-trip latency.

### ✨ User Experience & Connector Enhancements

- **External Secrets Operator Support** ([#11237](https://github.com/onyx-dot-app/onyx/pull/11237), [`2b5b360011`](https://github.com/onyx-dot-app/onyx/commit/2b5b360011157be6e6d412d51caa48a0c01d6fbd)) — Admins deploying via Helm can pull secrets dynamically from HashiCorp Vault, AWS Secrets Manager, or Azure Key Vault.
- **Slack Federated Deep Links** ([#9940](https://github.com/onyx-dot-app/onyx/pull/9940), [`7ec50280ed`](https://github.com/onyx-dot-app/onyx/commit/7ec50280ed734e0da918b177b00440ede60f09f3)) — Federated search results from Slack include direct links into the original Slack discussion threads.
- **High-Fidelity Tables** ([#12377](https://github.com/onyx-dot-app/onyx/pull/12377), [`0971302e16`](https://github.com/onyx-dot-app/onyx/commit/0971302e169bff26ec84fefdc35fd4534d60a915)) — Markdown tables in chat responses feature refined typography, fixed column proportions, and horizontal scrollbars.

### 🐛 Noticeable Bug Fixes & Patch Highlights

- **Password-Free Encrypted PDFs** ([#9953](https://github.com/onyx-dot-app/onyx/pull/9953), [`c31338e9b7`](https://github.com/onyx-dot-app/onyx/commit/c31338e9b7e7ed2526748136c3855f6f9ab533ca)) — Fixed an issue where PDFs encrypted with empty owner passwords were incorrectly flagged as password-locked.
- **Azure OpenAI Streaming Reliability** ([#11323](https://github.com/onyx-dot-app/onyx/pull/11323), [`a8517d200e`](https://github.com/onyx-dot-app/onyx/commit/a8517d200e560307f5c46e57b3d617805b199917)) — Resolved bursty streaming issues and disconnects when using Azure-hosted OpenAI endpoints.
- **Long Conversation Sluggishness** ([#11557](https://github.com/onyx-dot-app/onyx/pull/11557), [`45224e6ea5`](https://github.com/onyx-dot-app/onyx/commit/45224e6ea538ae6d52a9f3e0fba86523c352bf77)) — Resolved client-side memory buildup during long, multi-turn chat sessions.
- **Jira Bulk Fetch Pagination** ([#10044](https://github.com/onyx-dot-app/onyx/pull/10044), [`5b2ba5caeb`](https://github.com/onyx-dot-app/onyx/commit/5b2ba5caebeaf2ca24cb5af81fc13113544b9dd9)) — Handled timeout errors during large Jira workspace synchronizations.

---

## v4.0 Series — Major Release (v4.0.0 → v4.0.14)

### 🌟 Headline Features

- **OpenSearch Vector Database Engine** ([#9384](https://github.com/onyx-dot-app/onyx/pull/9384), [`86a6a4c134`](https://github.com/onyx-dot-app/onyx/commit/86a6a4c134ed69a285719e3b3f021761f10ddd0d)) — Major architectural migration from Vespa to OpenSearch as the primary document index, delivering significantly faster hybrid search, lighter resource consumption, and simplified operational maintenance.
- **Targeted Document Reindexing** ([#10747](https://github.com/onyx-dot-app/onyx/pull/10747), [`ed7960b7b6`](https://github.com/onyx-dot-app/onyx/commit/ed7960b7b6f5864b1cb3cb2817a3d9c81cf94fe5)) — Admins can re-index specific documents, folders, or sub-trees without triggering an expensive re-crawl of the entire data source.
- **Index Attempt Diagnostics Dashboard** ([#12207](https://github.com/onyx-dot-app/onyx/pull/12207), [`2274d65ac3`](https://github.com/onyx-dot-app/onyx/commit/2274d65ac342875b592608bd4a5fe53e6fff552b)) — A dedicated administration screen providing granular metrics on indexing attempts, successes, failures, and per-document error logs.
- **Chat History Retention Controls** ([#12959](https://github.com/onyx-dot-app/onyx/pull/12959), [`03003a60d4`](https://github.com/onyx-dot-app/onyx/commit/03003a60d409e5de4c0fa03d23734141112302bf)) — Enterprise retention controls allowing organizations to define retention periods or disable chat history persistence entirely.
- **Revamped Notification Panel** ([#10651](https://github.com/onyx-dot-app/onyx/pull/10651), [`66ac4a43bc`](https://github.com/onyx-dot-app/onyx/commit/66ac4a43bc1192437d4cc607aef975ddb805a7c5)) — Complete overhaul of the notifications popover with categorized "New" and "Older" notification sections.

### ⚡ Performance & Speed Improvements

- **Dramatically Faster Search & Ingest** ([#9844](https://github.com/onyx-dot-app/onyx/pull/9844), [`02671937fb`](https://github.com/onyx-dot-app/onyx/commit/02671937fbd1852d33f9e12cedc5de77fcfd167a)) — OpenSearch hybrid search queries run with lower latency and higher concurrent query capacity.
- **Resilient Web Scraping** ([#12461](https://github.com/onyx-dot-app/onyx/pull/12461), [`c902a4609e`](https://github.com/onyx-dot-app/onyx/commit/c902a4609ea4269a83d0d240c7db72087f32e15b)) — Playwright-powered web crawler includes automated exponential backoff and retry handling on slow or flaky sites.

### ✨ User Experience & Connector Enhancements

- **Default Prompt Restoration** ([#10706](https://github.com/onyx-dot-app/onyx/pull/10706), [`2862f786a6`](https://github.com/onyx-dot-app/onyx/commit/2862f786a65fa5f17685f98074f74675c8b23ca3)) — Admins can easily restore system prompts back to curated defaults with a single click.
- **New Connector Ecosystem Branding** ([#10706](https://github.com/onyx-dot-app/onyx/pull/10706), [`2862f786a6`](https://github.com/onyx-dot-app/onyx/commit/2862f786a65fa5f17685f98074f74675c8b23ca3)) — Added logos and streamlined authentication flows for Highspot and Loopio.
- **Tenant Self-Service Upgrades** ([#10732](https://github.com/onyx-dot-app/onyx/pull/10732), [`85078e210d`](https://github.com/onyx-dot-app/onyx/commit/85078e210da42381b70c485f05b923ccb7780edf)) — Multi-tenant instances allow self-serve tier upgrades directly from the billing dashboard.

### 🐛 Noticeable Bug Fixes & Patch Highlights

- **External Group Sync Fencing (v4.0.0)** ([#10691](https://github.com/onyx-dot-app/onyx/pull/10691), [`49a2a134df`](https://github.com/onyx-dot-app/onyx/commit/49a2a134df81989f4b01fd985cfc5be06786dfbd)) — Fixed transition gaps when synchronizing large user group memberships from Azure AD / Okta.
- **Connector Worker Timeouts (v4.0.0)** ([#10693](https://github.com/onyx-dot-app/onyx/pull/10693), [`af596d5dd8`](https://github.com/onyx-dot-app/onyx/commit/af596d5dd8ae2d9b3c032393fa3daa9dbf016ad9)) — Added strict HTTP timeout boundaries preventing worker threads from hanging indefinitely on stalled third-party APIs.
- **Inactive Slack Credentials (v4.0.0)** ([#10697](https://github.com/onyx-dot-app/onyx/pull/10697), [`18867a26b7`](https://github.com/onyx-dot-app/onyx/commit/18867a26b7e459090b624225fd68d5eb5466fd14)) — Expired or revoked Slack bot tokens are recognized immediately and flagged rather than entering infinite retry loops.
- **Multi-Tenant Metrics Isolation** ([#10689](https://github.com/onyx-dot-app/onyx/pull/10689), [`4628dc0b1f`](https://github.com/onyx-dot-app/onyx/commit/4628dc0b1f1a44be007b685c4f25bb56ba49e462)) — Ensured tenant identifiers are strictly isolated across all background task metrics.

---

## v3.3 Series (v3.3.0 → v3.3.14)

### 🌟 Headline Features

- **Searchable Agent Selector in Slack Bot** ([#10036](https://github.com/onyx-dot-app/onyx/pull/10036), [`32d2e7985a`](https://github.com/onyx-dot-app/onyx/commit/32d2e7985a8f7a3c093180cd0ded9cdfccec37d3)) — Users interacting with Onyx inside Slack can search and pick specific custom agents directly within channel or direct message threads.
- **Federated Slack Thread Retrieval** ([#9940](https://github.com/onyx-dot-app/onyx/pull/9940), [`7ec50280ed`](https://github.com/onyx-dot-app/onyx/commit/7ec50280ed734e0da918b177b00440ede60f09f3)) — Live federated search in Slack retrieves complete conversation context and full thread replies.
- **Google Drive Error Resolution Guided Flow** ([#9842](https://github.com/onyx-dot-app/onyx/pull/9842), [`712e6fdf5e`](https://github.com/onyx-dot-app/onyx/commit/712e6fdf5e6c51d160343b488f3279fb6279a4db)) — Self-service resolution workflow guiding users through authentication and shared folder permission issues.
- **Ready-Made Grafana Dashboards** ([#10042](https://github.com/onyx-dot-app/onyx/pull/10042), [`771d2cf101`](https://github.com/onyx-dot-app/onyx/commit/771d2cf1011a09e750782566b9a5eafdb747fb23)) — Bundled Grafana dashboards for OpenSearch metrics, Celery worker capacity, and Redis task queues.
- **New Embedding Provider Integrations** ([#10034](https://github.com/onyx-dot-app/onyx/pull/10034), [`8c7810d688`](https://github.com/onyx-dot-app/onyx/commit/8c7810d688ab4d30d46b09e5c85756c2fa38a992)) — First-class integration and branding for Cohere, Nomic, and Voyage AI embedding models.

### ⚡ Performance & Speed Improvements

- **Expanded Hybrid Subquery Candidates** ([#9844](https://github.com/onyx-dot-app/onyx/pull/9844), [`02671937fb`](https://github.com/onyx-dot-app/onyx/commit/02671937fbd1852d33f9e12cedc5de77fcfd167a)) — Increased default hybrid search candidate pool to 500, improving recall accuracy on ambiguous queries.
- **Database Session Optimization** ([#10881](https://github.com/onyx-dot-app/onyx/pull/10881), [`536f0ef1a7`](https://github.com/onyx-dot-app/onyx/commit/536f0ef1a7a91bd76cf48a7885fdd6fb2eb4b140)) — Reduced open transaction hold times during background synchronization tasks.

### ✨ User Experience & Connector Enhancements

- **Opal UI Polish** ([#12277](https://github.com/onyx-dot-app/onyx/pull/12277), [`8e9a881db4`](https://github.com/onyx-dot-app/onyx/commit/8e9a881db4010fa5501312f500f7fe8ce62bf098)) — Refined divider lines, unified button spacing, and modernized form component layouts across settings pages.
- **Adaptive Thinking for Claude Opus 4.8** ([#11524](https://github.com/onyx-dot-app/onyx/pull/11524), [`1a42b3d439`](https://github.com/onyx-dot-app/onyx/commit/1a42b3d439fa10ea1612fb69fba3c2d02b50839b)) — Automatic omission of conflicting sampling parameters when enabling reasoning mode on Claude Opus models.

### 🐛 Noticeable Bug Fixes & Patch Highlights

- **Query History Column Constraints** ([#10047](https://github.com/onyx-dot-app/onyx/pull/10047), [`0aa1aa7ea0`](https://github.com/onyx-dot-app/onyx/commit/0aa1aa7ea0674364145a57b53da52eecf9067518)) — Fixed table layout stretching when query history contained unusually long question strings.
- **Enterprise Service Account Seat Counting** ([#10053](https://github.com/onyx-dot-app/onyx/pull/10053), [`4dab92ab52`](https://github.com/onyx-dot-app/onyx/commit/4dab92ab52d6f3de11e8dd73a07abd9aded45975)) — Service accounts are excluded from licensed user seat quotas.
- **SCIM Advisory Lock Protection** ([#10048](https://github.com/onyx-dot-app/onyx/pull/10048), [`b1cc0c2bf9`](https://github.com/onyx-dot-app/onyx/commit/b1cc0c2bf9af60199703b5efd642827b51e01635)) — Added database-level locks preventing race conditions and seat count overages during concurrent user onboarding.
- **Clipboard Fallback Handling** ([#10080](https://github.com/onyx-dot-app/onyx/pull/10080), [`bb1c44daff`](https://github.com/onyx-dot-app/onyx/commit/bb1c44daff1e74e390838318b6851cf20d25df16)) — Added fallback copy mechanism when the modern browser Clipboard API is restricted by iframe or browser permissions.

---

## v3.2 Series (v3.2.2 → v3.2.16)

### 🌟 Headline Features & Improvements

- **Accelerated Permission Sync Startup** ([#12457](https://github.com/onyx-dot-app/onyx/pull/12457), [`e38153434b`](https://github.com/onyx-dot-app/onyx/commit/e38153434b4bd6b77774b8da54747b39d2cc05e2)) — Optimized permission initialization, cutting sync startup times dramatically across complex document trees.
- **Configurable Upload & Token Limits** ([#9232](https://github.com/onyx-dot-app/onyx/pull/9232), [`146b5449d2`](https://github.com/onyx-dot-app/onyx/commit/146b5449d22831769f7ca5531b1299e7845f6a7b)) — Administrators can configure maximum file upload sizes and token budget thresholds directly from admin settings.
- **Custom Admin Automation Hook Editor** ([#10009](https://github.com/onyx-dot-app/onyx/pull/10009), [`bfa2f672f9`](https://github.com/onyx-dot-app/onyx/commit/bfa2f672f9528b14c37b4ecf540a01870eb67a33)) — Built-in admin management interface to configure and maintain webhook triggers for system events.
- **Centered Multi-Model Chat Layout** ([#12794](https://github.com/onyx-dot-app/onyx/pull/12794), [`da94192d6a`](https://github.com/onyx-dot-app/onyx/commit/da94192d6a45066a3809460a9b29a7b3ddc989dc)) — Multi-model comparison responses are presented in a focused, centered 720px width view.
- **Richer Notion Metadata Extraction** ([#9891](https://github.com/onyx-dot-app/onyx/pull/9891), [`559bac9f78`](https://github.com/onyx-dot-app/onyx/commit/559bac9f78495a0c16e885dea9c961aeb96855ec)) — The Notion connector parses people properties and inline table content.

### 🐛 Noticeable Bug Fixes & Patch Highlights

- **PowerPoint Slide Chart Indexing** ([#9970](https://github.com/onyx-dot-app/onyx/pull/9970), [`a95e2fd99a`](https://github.com/onyx-dot-app/onyx/commit/a95e2fd99a4c978d9ccf2b24b40149b435a38965)) — Solved crashes when ingesting PowerPoint `.pptx` slides containing embedded charts.
- **Excel Empty Row/Column Robustness** ([#9288](https://github.com/onyx-dot-app/onyx/pull/9288), [`519fb61cc7`](https://github.com/onyx-dot-app/onyx/commit/519fb61cc7aee1e15562367c472a91fa6c45de2a)) — Handled empty rows and columns in spreadsheets without parsing errors.
- **Mobile & Tablet Sidebar Overlap** ([#9870](https://github.com/onyx-dot-app/onyx/pull/9870), [`9dbe7acac6`](https://github.com/onyx-dot-app/onyx/commit/9dbe7acac6eb920479a9a8b21b3749d7a4c02c93)) — Resolved sidebar navigation layering issues on medium screen sizes.
- **Custom LLM Provider Onboarding** ([#10003](https://github.com/onyx-dot-app/onyx/pull/10003), [`ab4d1dce01`](https://github.com/onyx-dot-app/onyx/commit/ab4d1dce01826c70c8235a57b0fa45fec0b8fba3)) — Fixed provider name validation issues and 404 errors during custom LLM endpoint setup.
- **OAuth Masked Secret Protection** ([#10066](https://github.com/onyx-dot-app/onyx/pull/10066), [`6959d851ea`](https://github.com/onyx-dot-app/onyx/commit/6959d851ea83d2743048cd2ba7ddd16b5d8e3d18)) — Re-authenticating external connectors no longer risks overwriting active credentials with masked password placeholders.
- **Citation ReDoS Protection (v3.2.16)** ([#11527](https://github.com/onyx-dot-app/onyx/pull/11527), [`a29c5c0a9d`](https://github.com/onyx-dot-app/onyx/commit/a29c5c0a9d8ef470d69153d74f91333c888fa756)) — Eliminated regex backtracking vulnerabilities in chat citation processors for long documents.
