# EEA Merge Automation Scripts

This directory contains the Python scripts and prompt templates used for the **Self-Correcting Sequential Resolver** architecture. These scripts automate the process of merging an upstream Onyx release tag into the EEA fork while preserving customizations.

## Prerequisites

- **Python 3.x**: Required for all scripts.
- **Git**: Configured to access both the local EEA fork and the upstream Onyx repository.
- **`gemini` CLI**: Authenticated and available on `$PATH` for AI-driven conflict resolution.
- **Dependencies**: The master script will automatically set up an isolated virtual environment in `.eea_merge/.tools/python_env` with necessary tools (`ruff`, `yamllint`).

---

## The Workflow

The entire process is orchestrated by a **Master Workflow Script** but can be run phase-by-phase for debugging or manual intervention.

### 1. The Master Stage (Recommended)

Running the master script is the standard way to initiate and complete an upgrade. It performs pre-flight checks, sets up the environment, and executes all subsequent phases sequentially.

```bash
python eea-artifacts/scripts/eea_merge_master.py <target_tag>
```

**Parameters:**
- `target_tag`: (Required) The Onyx version to merge (e.g., `v2.12.1`).
- `--smart-model`: (Optional) The LLM for complex resolution (default: `gemini-3.1-pro-preview`).
- `--dumb-model`: (Optional) The LLM for mapping (default: `gemini-3-flash-preview`).
- `--no-branch-switch`: (Optional) Use the current branch instead of creating a new one (e.g., for testing or manual branch management).

---

### 2. Individual Stages (For Debugging/Resume)

If the master script fails, you can resume from specific scripts or re-run them after manual adjustments to `.eea_merge/state.json`.

#### Phase 1: Init (`eea_merge_init.py`)
Creates a datestamped upgrade branch (unless `--no-branch-switch` is used), initiates the `git merge <tag>`, identifies conflicted files, and maps them to documented EEA patches.
```bash
python eea-artifacts/scripts/eea_merge_init.py <target_tag> [--no-branch-switch]
```

#### Phase 2: Resolve (`eea_merge_resolve.py`)
The core resolution loop. It iterates over every conflicted file:
1. **AI Resolution**: Files with documented patches or standard code are sent to the LLM.
2. **Programmatic Resolution**: Special files like `package.json`, `pyproject.toml`, and Alembic migrations are handled by deterministic logic.
3. **Self-Correction**: Resolutions are validated against linters (`ruff`, `yamllint`). If syntax is broken, the script feeds errors back to the AI for a retry.
```bash
python eea-artifacts/scripts/eea_merge_resolve.py --smart-model gemini-3.1-pro-preview
```

#### Phase 3-5: Integrate & Validate (`eea_merge_integrate.py`)
1. **Integration**: Copies verified resolutions from `.eea_merge/resolutions/` to the working tree and stages them (`git add`).
2. **Validation**: Runs a full project build (Backend `ruff`, Frontend `npm install` & `tsc --noEmit`, Alembic chain check).
3. **Commit**: If all checks pass and no files require human intervention, it creates the final merge commit.
```bash
python eea-artifacts/scripts/eea_merge_integrate.py <target_tag>
```

---

## File Manifest

| File | Description |
| :--- | :--- |
| `eea_merge_master.py` | The main orchestrator (Entry Point). |
| `eea_merge_init.py` | Phase 1: Environment setup, branching, and mapping. |
| `eea_merge_resolve.py` | Phase 2: AI-driven and programmatic resolution loop. |
| `eea_merge_integrate.py` | Phase 3-5: Integration, validation, and final commit. |
| `eea_merge_utils.py` | Shared utilities for Git commands, state, and LLM calls. |
| `prompts/` | Directory containing `.txt` templates for LLM instructions. |

---

## State & Troubleshooting

The system maintains its progress in a `.eea_merge/` directory at the project root:
- `state.json`: Master tracking file for all conflicted files.
- `backups/`: Original conflicted files (pre-resolution).
- `resolutions/`: AI-generated content before it is applied to the repo.
- `logs/`: Detailed validation and AI-analysis logs for debugging.
- `prompts/`: Audit trail of the exact prompts sent to the LLM.

If a file fails AI resolution, its status in `state.json` will be marked as `failed_requires_human`. You can manually resolve the file in the working tree or edit the resolution in `.eea_merge/resolutions/` and set its status to `resolved_and_verified` before re-running the integration script.
