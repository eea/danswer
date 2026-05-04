# EEA Features Test Plan

## Issues to Address
The EEA fork contains numerous custom features (Langfuse tracing, Playwright stability, custom UI pages, rebranding, and NLP improvements) that are currently lacking dedicated test coverage. To prevent regressions during upstream merges, we need a robust test suite covering these specific customizations.

## Important Notes
- **Onyx Test Typologies**: We will strictly follow the Onyx testing structure:
  - `unit`: Pure Python logic, mocked dependencies.
  - `external_dependency_unit`: Tests against real DB/Redis/Vespa, but without running the full backend server.
  - `integration`: Full backend API tests via HTTP.
  - `e2e` (Playwright): Full-stack tests including the Next.js frontend.
- **Langfuse Keys**: Tracing tests will require mocking the Langfuse client or ensuring test API keys are provided so we don't pollute the production Langfuse dashboard with test traces.

## Implementation strategy
We will systematically add test files mirroring the existing project structure, targeting the 4 active functional areas of the EEA customizations.

## Tests

### 1. Langfuse Tracing & LLM Metadata
**Type**: Unit & Integration
- **Unit**: 
  - Test `eea_utils.get_eea_user_id` to ensure it strips `DANSWER_API_KEY_PREFIX` correctly and appends the persona name.
- **Integration**:
  - Test that calling `eea_start_turn` initializes the thread-local storage correctly with the `ChatMessage` metadata.
  - Test that `eea_set_turn_output` correctly retrieves the thread-local data, includes the `assistant_message.id` in metadata, constructs the composite session ID, and submits the trace using the Onyx tracing framework.

### 2. Web Scraping & Playwright Enhancements
**Type**: Unit & External Dependency Unit
- **Unit**: 
  - Test `eea_utils.remove_by_selector` by passing sample HTML with headers/footers and asserting they are stripped.
  - Test Playwright process guards (e.g. mocking a process where `returncode` is None).
- **External Dependency Unit**:
  - Mock an external web server serving a basic `sitemap.xml` and verify `get_document_updated_at_batch` successfully extracts the `lastmod` dates.

### 3. Connector Stability & Healthchecks
**Type**: Integration
- **Integration**:
  - Manually insert a connector and trigger an indexing job that intentionally raises an exception.
  - Check the DB state: confirm `consecutive_failure_count` increments but the connector is NOT paused.
  - Trigger a second failure and confirm the connector status shifts to `FAILED`.

### 4. EEA UI Customizations (Rebranding, Disclaimer, Custom Pages)
**Type**: Playwright (E2E)
- **E2E**:
  - **Rebranding**: Navigate to the login page and assert the presence of the `EEA AI Hub` branding and custom SVG logo.
  - **Disclaimer**: Run a test with an empty local storage state. Assert the User Disclaimer Modal blocks interaction. Click "I Agree", refresh the page, and assert the modal does not reappear.
  - **Custom Pages**: Log in as admin, navigate to `/admin/eea_config/pages`, create a test page. Switch to a standard user, open the User Dropdown, and verify the newly created custom page is visible and navigable.
