# EEA Customizations & Patches Overview

This document records the specific customizations and patches made in the `eea` branch of our fork of the Onyx (formerly Danswer) repository. Keeping track of these changes is essential when migrating our fork to newer upstream Onyx versions.

## Current Merge Target

**Target Upstream Version:** `v2.12.1`

Whenever an EEA-specific customization is created or modified, or an upstream feature requires an EEA patch to work, document it here.

---

### Patch Record Template

To add a new patch, please duplicate the template below.

- **Patch Name/ID:** (e.g., `[EEA-001] Custom SSO Authentication`)
- **Files Modified:** (List of files touched by this patch)
- **Description:** (What does this patch do? Why is it necessary for EEA?)
- **Potential Upstream Conflicts:** (What parts of the original code were overridden that might break during an upgrade?)
- **Migration Strategy:** (How to carry this patch forward or reintegrate it if upstream changes significantly)

---

## Documented Patches

- **Patch Name/ID:** `[EEA-001] Custom Jenkins & Git CI/CD`
- **Files Modified:** `Jenkinsfile`, `deployment/.gitignore`, `backend/Dockerfile`, `backend/Dockerfile.model_server`
- **Description:** Adds Jenkins pipelines, custom Docker build arguments, and tweaks dockerfiles to support EEA's build infrastructure.
- **Potential Upstream Conflicts:** Low to Moderate. Dockerfile changes might conflict if upstream restructures underlying OS or python versions.
- **Migration Strategy:** Maintain Jenkinsfile separately. Re-apply custom dockerfile arguments if `backend/Dockerfile` changes structurally upstream.

---

- **Patch Name/ID:** `[EEA-002] Playwright & Scraping Customizations`
- **Files Modified:** `backend/onyx/utils/playwright.py`, `backend/onyx/utils/sitemap.py`, `backend/chromium-linux.zip.part.*`, `backend/ffmpeg-linux.zip`
- **Description:** Adjusts Playwright behavior (added timeouts, optimistic disconnect handling, exclude elements by selector), allows scraping with expired SSL certificates, and includes offline chromium/ffmpeg binaries to avoid downloading them at runtime.
- **Potential Upstream Conflicts:** Moderate. `sitemap.py` and scraping utilities might receive upstream improvements that conflict.
- **Migration Strategy:** Carry over the offline binaries and the custom timeout/ssl settings into the new crawler utility versions upon merging.

---

- **Patch Name/ID:** `[EEA-003] EEA Config & Admin Pages`
- **Files Modified:** `backend/onyx/server/eea_config/*`, `web/src/app/admin/eea_config/*`, `web/src/app/pages/*`, `web/src/lib/eea/fetchEEASettings.ts`, `backend/onyx/utils/eea_utils.py`
- **Description:** Adds a custom dynamic configuration module to manage specific EEA parameters (like footer links, disclaimer options) directly from the admin panel, as well as the ability to create dynamic pages.
- **Potential Upstream Conflicts:** Low for backend since files are isolated. Moderate for frontend where admin sidebar/routing (`web/src/sections/sidebar/AdminSidebar.tsx`) and `layout.tsx` are modified.
- **Migration Strategy:** The isolated files will migrate cleanly. The integration points in `AdminSidebar.tsx`, API routers, and layout components will need manual conflict resolution.

---

- **Patch Name/ID:** `[EEA-004] Frontend Customizations (Logos, UI, Disclaimer, Chat)`
- **Files Modified:** `web/public/EEA_logo*`, `web/src/components/logo/*`, `web/src/components/EEA_Logo.tsx`, `web/src/app/auth/*`, `web/src/app/layout.tsx`, `web/src/app/chat/components/WelcomeMessage.tsx`, `web/src/components/auth/AuthFlowContainer.tsx`
- **Description:** Replaces Onyx branding with EEA branding. Updates the login/signup pages, header, footer, and chat layout. Adds a custom disclaimer modal when a user logs in.
- **Potential Upstream Conflicts:** High. These are core UI files (Login, Layout, Chatbar) which upstream changes frequently.
- **Migration Strategy:** Carefully re-apply branding and disclaimer modal checks inside the updated upstream layout and login components during the upgrade.

---

- **Patch Name/ID:** `[EEA-005] Custom Background Tasks & Celery Tweaks`
- **Files Modified:** `backend/onyx/background/celery/tasks/eea/*`, `backend/onyx/background/celery/tasks/beat_schedule.py`, `backend/onyx/background/celery/apps/primary.py`, `backend/onyx/background/celery/apps/light.py`
- **Description:** Adds EEA-specific scheduled tasks and celery worker configurations. Modifies the beat schedule to include these custom tasks.
- **Potential Upstream Conflicts:** Moderate. Upstream registry `beat_schedule.py` might have new tasks added.
- **Migration Strategy:** Keep `eea/tasks.py` isolated. Re-inject the schedule into `beat_schedule.py` and worker configs manually upon merge.

---

- **Patch Name/ID:** `[EEA-006] Helm Chart Customizations for EEA Infrastructure`
- **Files Modified:** `deployment/helm/charts/onyx/templates/postgresql-*`, `deployment/helm/charts/onyx/templates/redis-*`, `deployment/helm/charts/onyx/templates/vespa-*`, `deployment/docker_compose/eea/*`, `deployment/helm/charts/onyx/templates/network-policies.yaml`, `deployment/helm/charts/onyx/templates/nginx-ingress.yaml`, `deployment/helm/charts/onyx/templates/nginx-simple.yaml`
- **Description:** Adds backup cronjobs, PVCs, custom network policies, and a different ingress setup for EEA's Kubernetes environment. Disables/moves upstream ingress templates.
- **Potential Upstream Conflicts:** High. Upstream Helm chart version bumps and template restructuring.
- **Migration Strategy:** Retain the EEA-specific YAML templates. If upstream made changes to statefulsets/deployments, ensure our backup cronjobs and PVCs still attach correctly.

---

- **Patch Name/ID:** `[EEA-007] Connector Healthchecks & Workarounds`
- **Files Modified:** `backend/onyx/server/manage/connectors_state.py`, `backend/onyx/connectors/*`, `backend/onyx/background/indexing/job_client.py`
- **Description:** Adds connector healthcheck endpoints, tweaks failure handling (wait for 2 consecutive failures before pausing), and provides workarounds for connector deletion and un-reachable indexing models.
- **Potential Upstream Conflicts:** Moderate. Upstream is actively improving connectors and indexing logic.
- **Migration Strategy:** Carefully review upstream connector management during the merge. Some workarounds may no longer be needed if upstream fixed the underlying bug.

---

- **Patch Name/ID:** `[EEA-008] LLM & Auth Minor Tweaks`
- **Files Modified:** `backend/onyx/auth/email_utils.py`, `backend/onyx/llm/chat_llm.py`, `backend/onyx/llm/utils.py`
- **Description:** Minor tweaks for SMTP authentication (don't auth if credentials are missing), handling Meta-Llama `MAX_TOKENS` special cases, and fallback encoding.
- **Potential Upstream Conflicts:** Low.
- **Migration Strategy:** Re-apply the specific conditional lines to the updated upstream files.

---

- **Patch Name/ID:** `[EEA-009] Upstream Backports & Hotfixes`
- **Files Modified:** Various backend files (e.g., `alembic` revisions, Confluence `handleRequest` fix).
- **Description:** Commits cherry-picked from newer Onyx versions before doing a full upgrade to fix urgent bugs.
- **Potential Upstream Conflicts:** Low. Git should handle exact cherry-picks cleanly.
- **Migration Strategy:** Upon merging `v2.12.1`, git will likely auto-resolve these. If conflicts arise, accept the upstream `v2.12.1` version of the file since it contains the official fix.
