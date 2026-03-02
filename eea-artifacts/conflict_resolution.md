# AI-Driven Merge Conflict Resolution System (EEA Fork)

## Context & Architecture Overview

Merging with major upstream tags (like **Onyx v2.12.1**) results in extensive conflicts due to deep EEA-specific customizations. To ensure a reliable, repeatable upgrade process, we use a **Self-Correcting Sequential Resolver** architecture implemented in **Python**, designed to run headlessly in an **automated pipeline**.

Instead of a single, fragile interactive AI session, this system uses a dispatched, state-managed pipeline that isolates context per file, forces structured reasoning, and validates output against local linters before automatically integrating the changes.

The entire process is orchestrated by a **Master Workflow Script** that takes the target Upstream tag as a parameter.

---

## Core Mitigations Against "Hallucinations"

To prevent the AI from making poor integration decisions or outputting broken syntax:

1. **`diff3` Conflict Style:** We configure Git to use `diff3` (`git config merge.conflictstyle diff3`). This provides the AI with `<<<<<<< HEAD` (Local), `||||||| merged common ancestors` (Base), and `>>>>>>> MERGE_HEAD` (Upstream) all inline. Seeing the "Base" is critical for the AI to understand _how_ both sides diverged.
2. **Chain-of-Thought JSON Output:** We force the LLM to output a strict JSON schema. It must write an `analysis` (explaining the intent of EEA vs. Upstream) _before_ it generates the `resolved_file_content`. This acts as forced reasoning.
3. **The Compiler Feedback Loop:** We treat the LLM like a developer. After it resolves a file, we run a local syntax/lint check. If it fails, we feed the `stderr` back to the LLM for a retry (up to a configurable max limit).
4. **Sequential Execution:** Parallelism is set to 1. We process one file at a time to ensure stability, trackability, and deterministic pipeline execution.

---

## File-Type Handling & Validation Matrix

Not all conflicted files can be handled identically. The resolver uses the following matrix to determine the validation strategy and whether AI resolution is even applicable:

| File Extension(s)        | Validator                    | Notes                                                                       |
| ------------------------ | ---------------------------- | --------------------------------------------------------------------------- |
| `.py`                    | `ruff check --select=E9`     | Syntax-only check via isolated venv.                                        |
| `.ts`, `.tsx`            | Conflict marker check only\* | Full-project `tsc --noEmit` runs once in Phase 4 (see below).               |
| `.js`, `.jsx`, `.mjs`    | Conflict marker check only   | Same as TS — deferred to Phase 4 build validation.                          |
| `.json`                  | `python -m json.tool`        | Validates JSON syntax. `package.json` has special handling (see below).     |
| `.yaml`, `.yml`          | `yamllint -d relaxed`        | Installed in the isolated Python venv alongside `ruff`.                     |
| `Dockerfile*`            | Conflict marker check only   | No widely reliable Dockerfile linter; marker check is sufficient.           |
| `.md`, `.txt`, `.env`    | Conflict marker check only   | Non-executable; just verify markers are gone.                               |
| Binary files (zip, png…) | **Skip — `requires_human`**  | Auto-detected by `git diff --numstat` (binary = `-\t-`). Never sent to LLM. |

**\*Why `tsc` is not run per-file:** TypeScript requires the full project context (imports, `node_modules`, `tsconfig.json`). Running `tsc` on an isolated file produces meaningless errors. Instead, per-file resolution only checks for leftover conflict markers. A full `tsc --noEmit` is run once in Phase 4 across the entire project.

### Special Files (Resolved Programmatically, Not by AI)

Certain files have implicit semantic structure that an LLM may corrupt. These are handled by deterministic scripts, **not** sent to the AI:

- **`package.json` / `package-lock.json`:** Accept upstream version. Re-apply any EEA-specific dependency additions programmatically by diffing the EEA branch's `package.json` against the merge-base. Then run `npm install` to regenerate the lockfile.
- **`pyproject.toml` / `requirements.txt`:** Same strategy — accept upstream, re-inject EEA-only dependencies.
- **Alembic migration files:** Accept upstream. Verify the migration chain integrity (`down_revision` pointers) programmatically post-merge.

---

## Conflict Type Classification

Git merge conflicts are not always inline `<<<<<<< HEAD` markers. The init phase must classify each unmerged file:

| Conflict Type        | Git Status                  | Resolution Strategy                                                                                  |
| -------------------- | --------------------------- | ---------------------------------------------------------------------------------------------------- |
| **Content conflict** | `both modified`             | Standard AI resolution (Phase 2 loop).                                                               |
| **Delete/modify**    | `deleted by us/them`        | If EEA deleted: accept upstream. If upstream deleted: flag `requires_human` (EEA may still need it). |
| **Added by both**    | `both added`                | AI resolution, but prompt must note there's no common base.                                          |
| **Rename conflict**  | `renamed` with conflicts    | Resolve the content conflict normally; `git add` the correct final path.                             |
| **Binary conflict**  | Binary detected via numstat | Auto-flag as `requires_human`, never send to LLM.                                                    |

This classification is stored in `state.json` per file and determines which resolution path is taken.

---

## State Management (`.eea_merge/`)

The system stores its progress in a `.eea_merge/` directory at the project root. This allows the process to be paused, resumed, or debugged if the automated pipeline fails.

```text
.eea_merge/
├── .tools/               # Isolated tooling (Python venv, local node_modules)
├── state.json            # Master state (file paths, conflict types, status, retry counts, patch IDs)
├── prompts/              # Saved prompts sent to the LLM (for debugging/auditing)
├── resolutions/          # Resolved file content (held here until Phase 3 applies them)
├── logs/                 # Linter/Compiler outputs and error logs
└── backups/              # Pre-resolution copies of conflicted files (for rollback)
```

**Important:** Resolved file content is initially written to `.eea_merge/resolutions/`, **not** directly to the working tree. Files are only written back to the tree and staged in Phase 3, after all resolutions are complete. This allows safe rollback at any point during Phase 2.

---

## The Pipeline Phases

### Phase -1: Environment Bootstrap

To ensure the system is immune to Git conflicts in `package.json` or `pyproject.toml`, and to guarantee 100% reproducibility across different machines, the orchestrator first sets up an isolated environment:

1. **Python (`ruff`, `yamllint`):** Creates a virtual environment in `.eea_merge/.tools/python_env` and installs pinned versions of `ruff` and `yamllint`.
2. **Node (for Phase 4 build):** No isolated install needed — Phase 4 uses the project's own `node_modules` after dependency resolution.
3. **Verify `gemini` CLI:** Confirms the `gemini` command is available on `$PATH` and can authenticate. Exits with a clear error if not.

### Phase 0: The Master Orchestrator (`eea_merge_master.py <tag>`)

The entry point for the pipeline. All scripts live in `eea-artifacts/scripts/`. It takes the target Onyx upstream tag as a CLI parameter (e.g., `python eea-artifacts/scripts/eea_merge_master.py v2.12.1`) and coordinates the execution of all subsequent phases.

**CLI Parameters:**

- `target_tag`: (Required) The Onyx version to merge into the `eea` branch.
- `--smart-model`: (Optional) The LLM model used for complex AI resolution (default: `gemini-3.1-pro-preview`).
- `--dumb-model`: (Optional) The LLM model used for context mapping (default: `gemini-3-flash-preview`).

**Pre-flight checks (abort immediately if any fail):**

1. **Clean working tree:** Runs `git status --porcelain` and aborts if there are any uncommitted changes or untracked files. The user must start from a clean state.
2. **Source branch:** Confirms the current branch is `eea` (the correct base for all upgrades). Prints a warning and prompts for confirmation if not.
3. **Tag exists:** Confirms the target tag (e.g., `v2.12.1`) is known to Git locally. Fetches from `onyx` remote if not found.
4. **`gemini` available:** Confirms the `gemini` command is on `$PATH` and exits with a clear error if not.

### Phase 1: Setup & Context Mapping (`eea_merge_init.py`)

1. **Branch Creation:** Creates and checks out a new upgrade branch named `eea-merge-<tag>-<YYYYMMDD>` (e.g., `eea-merge-v2.12.1-20260302`) from the current `eea` branch. Using a datestamped name ensures previous attempts are preserved and the script is safe to re-run from scratch.
2. **Git Prep:** Sets `merge.conflictstyle diff3` and initiates the target merge (`git merge <tag> --no-commit --no-ff`), leaving the tree in a conflicted state.
3. **Manifest Generation:** Identifies all `Unmerged` files via `git diff --name-only --diff-filter=U` and classifies each by conflict type (see Conflict Type Classification above).
4. **Binary Detection:** Runs `git diff --numstat` to identify binary files (lines show as `-\t-`). These are immediately marked `requires_human` and excluded from AI processing.
5. **Special File Detection:** Identifies `package.json`, `pyproject.toml`, lockfiles, and Alembic migrations. These are marked `programmatic_resolution` and handled by deterministic scripts, not the AI.
6. **The Mapping Pass:** Makes a single LLM call (using a fast model) providing the list of _AI-resolvable_ conflicted files and the `eea-artifacts/patches-overview.md`. The LLM returns a JSON map linking each file to its relevant EEA Patch ID(s) or `null`.
   - For `null`-mapped files (no documented patch), the resolution prompt will instruct the AI: _"No EEA patch documentation exists for this file. Prefer upstream changes. Preserve any lines clearly marked with `// EEA` or `# EEA` comments."_
7. **State Initialization:** Creates `.eea_merge/state.json` setting all files to their initial status (`pending`, `requires_human`, or `programmatic_resolution`).
8. **Summary Output:** Prints a conflict summary: total files, breakdown by type and resolution strategy, estimated LLM calls needed.

### Phase 2: The Self-Correcting Resolution Loop (`eea_merge_resolve.py`)

Runs sequentially over every `pending` file in `state.json`:

1. **Backup:** Copies the conflicted file to `.eea_merge/backups/` before any processing.
2. **Prompt Construction:**
   - Reads the conflicted file (`diff3` markers included).
   - Fetches the specific patch documentation mapped in Phase 1.
   - For `null`-mapped files, includes the fallback instruction (prefer upstream, preserve EEA-marked comments).
   - For `both added` conflicts, notes to the AI that there is no common base ancestor.
   - Appends strict instructions to preserve EEA logic while adopting Upstream architecture.
3. **LLM Execution:** Calls `gemini -m "gemini-2.5-pro"` via `subprocess`, piping the prompt through `stdin` and capturing `stdout`. JSON output is enforced.
   - _Expected Output:_ `{"analysis": {"eea_intent": "...", "upstream_intent": "...", "strategy": "..."}, "resolved_file_content": "..."}`
4. **Storage & Verification:**
   - Extracts the code from the JSON and writes it to `.eea_merge/resolutions/<filepath>` (not the working tree yet).
   - Checks for leftover conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`).
   - Runs the appropriate validator from the File-Type Handling Matrix above.
5. **Feedback Loop:**
   - **Pass:** Marks as `resolved_and_verified` in `state.json`.
   - **Fail:** Appends the validation error to the prompt and retries. Retry budget:
     - `.py` files: **3 retries** (ruff is precise, errors are actionable).
     - `.ts`/`.tsx` files: **2 retries** (only checking markers, less likely to fail).
     - All others: **2 retries**.
   - If retries exhausted: marks as `failed_requires_human`.
6. **Programmatic Resolutions:** After all AI files are processed, runs deterministic scripts for `programmatic_resolution` files (package.json, pyproject.toml, etc.).

### Phase 3: Integration & Staging

Resolved files are applied to the working tree and staged for commit. **No `git add` happens until this phase.**

1. For every file marked `resolved_and_verified` or `programmatic_resolution`, copy from `.eea_merge/resolutions/` to the working tree and run `git add <file>`.
2. For files marked `requires_human`, leave them as-is (conflicted) in the working tree. Log them prominently.
3. **Integrity check:** Run `git diff --check` to verify no conflict markers remain in any staged file.

### Phase 4: Post-Merge Validation (Full-Project Build)

**This phase validates the merge at the project level**, catching semantic integration errors that per-file checks cannot detect (e.g., a changed function signature upstream breaking an EEA caller in a different, auto-merged file).

1. **Backend:** Run `ruff check backend/` for a comprehensive Python lint pass.
2. **Frontend:** Run `cd web && npm install && npx tsc --noEmit` for a full TypeScript type-check.
3. **Alembic:** Verify migration chain integrity (no broken `down_revision` pointers) with a script that walks the chain.
4. **Results:**
   - **All pass:** Proceed to Phase 5.
   - **Any failure:** Log the errors. These might indicate auto-merged files that are semantically broken. The failures are appended to the human review list.

### Phase 5: Commit or Abort

1. **If no `failed_requires_human` files and Phase 4 passed:**
   - Run `git commit -m "Merge upstream tag <tag> (Automated AI Resolution)"`.
   - Exit 0 (success).
2. **If any files need human intervention or Phase 4 failed:**
   - Do **NOT** commit.
   - Print a detailed report: which files failed, why, and the error logs.
   - Exit with a non-zero status code.
   - The `.eea_merge/` state remains on disk for manual intervention, debugging, or `git merge --abort` if desired.

---

## Rollback Strategy

At any point before Phase 5's commit:

- **Full abort:** `git merge --abort` returns the repo to a clean pre-merge state. The `.eea_merge/` directory can optionally be kept for forensics.
- **Partial restart:** Delete specific entries from `state.json` (reset status to `pending`) and re-run Phase 2. The backup copies in `.eea_merge/backups/` ensure originals are never lost.
- **Manual override:** A human can edit any file in `.eea_merge/resolutions/` before Phase 3 applies it to the working tree.

---

## Technical Tooling

- **Language:** Python 3.x
- **AI Interface:** `gemini` CLI (called via `subprocess` with `stdin`/`stdout` pipelines). Model selection via `-m` flag.
- **Models:**
  - **Heavy (resolution):** `gemini-3.1-pro-preview` — for conflict resolution requiring complex reasoning.
  - **Fast (mapping):** `gemini-3-flash-preview` — for the Phase 1 mapping pass and simpler tasks.
- **Validators:** `ruff`, `yamllint` (isolated venv), `python -m json.tool` (stdlib), `tsc` (project-level only in Phase 4).
