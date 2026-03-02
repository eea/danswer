# AI-Driven Merge Conflict Resolution System (EEA Fork)

## Context & Architecture Overview

Merging with major upstream tags (like **Onyx v2.12.1**) results in extensive conflicts due to deep EEA-specific customizations. To ensure a reliable, repeatable upgrade process, we use a **Self-Correcting Sequential Resolver** architecture implemented in **Python**, designed to run headlessly in an **automated pipeline**.

Instead of a single, fragile interactive AI session, this system uses a dispatched, state-managed pipeline that isolates context per file, forces structured reasoning, and validates output against local linters before automatically integrating the changes.

The entire process is orchestrated by a **Master Workflow Script** that takes the target Upstream tag as a parameter.

---

## Core Mitigations Against "Hallucinations"

To prevent the AI from making poor integration decisions or outputting broken syntax:

1. **`diff3` Conflict Style:** We configure Git to use `diff3` (`git config merge.conflictstyle diff3`). This provides the AI with `<<<<<<< HEAD` (Local), `||||||| merged common ancestors` (Base), and `>>>>>>> MERGE_HEAD` (Upstream) all inline. Seeing the "Base" is critical for the AI to understand *how* both sides diverged.
2. **Chain-of-Thought JSON Output:** We force the LLM to output a strict JSON schema. It must write an `analysis` (explaining the intent of EEA vs. Upstream) *before* it generates the `resolved_file_content`. This acts as forced reasoning.
3. **The Compiler Feedback Loop:** We treat the LLM like a developer. After it resolves a file, we run a local syntax/lint check (e.g., `ruff`, `tsc`). If it fails, we feed the `stderr` back to the LLM for a retry (up to a max limit).
4. **Sequential Execution:** Parallelism is set to 1. We process one file at a time to ensure stability, trackability, and deterministic pipeline execution.

---

## State Management (`.eea_merge/`)

The system stores its progress in a `.eea_merge/` directory at the project root. This allows the process to be paused, resumed, or debugged if the automated pipeline fails.

```text
.eea_merge/
├── state.json            # Master state (File paths, status, retry counts, patch IDs)
├── prompts/              # Saved prompts sent to the LLM (for debugging)
├── resolutions/          # Raw JSON responses from the LLM
└── logs/                 # Linter/Compiler outputs and error logs
```

---

## The 4-Phase Pipeline

### Phase 0: The Master Orchestrator (`eea_merge_master.py <tag>`)

The entry point for the pipeline. It takes the target Onyx upstream tag as a CLI parameter (e.g., `python eea_merge_master.py v2.12.1`) and coordinates the execution of the subsequent phases.

### Phase 1: Setup & Context Mapping (`eea_merge_init.py`)

1. **Git Prep:** Sets `merge.conflictstyle diff3` and attempts the target merge (`git merge <tag>`), leaving the tree in a conflicted state.
2. **Manifest Generation:** Identifies all `Unmerged` files.
3. **The Mapping Pass:** Makes a single LLM call providing the list of conflicted files and the `eea-artifacts/patches-overview.md`. The LLM returns a JSON map linking each file to its relevant EEA Patch ID (or `null` if undocumented).
4. **State Initialization:** Creates `.eea_merge/state.json` setting all files to `status: pending`.

### Phase 2: The Self-Correcting Loop (`eea_merge_resolve.py`)

Runs sequentially over every `pending` file in `state.json`:

1. **Prompt Construction:** 
   * Reads the conflicted file (`diff3` markers included).
   * Fetches the specific patch documentation mapped in Phase 1.
   * Appends strict instructions to preserve EEA logic while adopting Upstream architecture.
2. **LLM Execution:** Calls the most capable reasoning model available via the Gemini CLI in non-interactive mode, enforcing JSON output.
   * *Expected Output:* `{"analysis": {"eea_intent": "...", "upstream_intent": "...", "strategy": "..."}, "resolved_file_content": "..."}`
3. **Application & Verification:**
   * Extracts the code from the JSON and overwrites the conflicted file.
   * Checks for leftover conflict markers (`<<<<<<<`).
   * Runs the appropriate syntax/lint check based on file extension (e.g., `.py` -> `ruff`, `.tsx` -> `tsc`).
4. **Feedback Loop:**
   * **Pass:** Marks as `resolved_and_verified` in `state.json`.
   * **Fail:** Appends the linter error to the prompt and retries (Max Retries: 2). If it fails repeatedly, marks as `failed_requires_human`.

### Phase 3: Automated Integration & Commits

Because this runs in an automated pipeline, successful resolutions are committed automatically:
1. For every file marked `resolved_and_verified`, the script runs `git add <file>`.
2. Once all files in `state.json` are processed:
   * **If Success:** If no files are marked `failed_requires_human`, the script runs `git commit -m "Merge upstream tag <tag> (Automated AI Resolution)"` and completes successfully.
   * **If Failure:** If any files failed validation limits, the script aborts the commit, logs a fatal error listing the failed files, and exits with a non-zero status code to fail the CI/CD pipeline. The state remains on disk for manual intervention.

---

## Technical Tooling

* **Language:** Python 3.x
* **AI Interface:** `gemini-cli` (called via `subprocess` with `stdin`/`stdout` pipelines and JSON schema flags).
* **Models:** Heavy reasoning models (e.g., `gemini-3.1-pro-preview`) for maximum reliability on complex logic integrations, and fast models (e.g., `gemini-3-flash-preview`) for simpler mapping tasks.