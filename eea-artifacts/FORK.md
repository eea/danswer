# EEA Fork Maintenance Context & Strategy

## Introduction

This repository is the EEA (European Environment Agency) fork of the **Onyx** (formerly Danswer) project. It contains a complex architecture with both backend and frontend services.

Because we have a significant number of customizations tailored to EEA's needs, maintaining this fork requires a careful, methodical approach to ensure we can periodically bring in updates from the main Onyx repository without losing or breaking our customizations.

**For AI Assistants:** Treat this file as the primary seed context when working in this repository. Ensure that any code changes, architectural decisions, and bug fixes consider the long-term maintainability of our fork against upstream Onyx changes.

---

## Branching Strategy

- **`eea` Branch**: This is our **main branch of development**. All EEA-specific features, customizations, and bug fixes reside here. When deploying or testing our environment, the `eea` branch is the source of truth.
- **Upstream Branches / Tags**: We track the main Onyx repository releases (e.g., `v2.12.1`).

---

## Update & Patch Strategy

To ensure seamless integration of upstream Onyx releases, we adhere to the following workflow:

1. **Targeting a Release**: We periodically identify a stable Onyx release (e.g., `v2.12.1`) as our target to merge into our fork.
2. **Patch Documentation**: Every customization or deviation from upstream Onyx **must** be documented in `eea-artifacts/patches-overview.md`. This allows us to track exactly what we changed, why we changed it, and where the changes live.
3. **Isolating Customizations**: When writing new features or modifying existing Onyx code:
   - Try to isolate EEA features by placing them in separate, newly created files or modules whenever possible.
   - If modifying an existing upstream file is unavoidable, clearly delineate the change with concise comments (e.g., `// EEA CUSTOMIZATION: ...`) so it is trivial to identify during a merge conflict.
4. **Merge Process**:
   - Fetch the upstream Onyx tags/releases.
   - Merge the targeted release tag into a temporary upgrade branch based on `eea`.
   - Resolve conflicts by referring to `eea-artifacts/patches-overview.md` to ensure our customizations are preserved.
   - Review and test before completing the merge back into the `eea` branch.

---

## Guidelines for AI Assistants working in this repo

When you (the AI assistant) are tasked with creating a feature, modifying code, or resolving conflicts in this repository, you must:

1. **Read `eea-artifacts/patches-overview.md`** first to understand existing customizations.
2. **Prioritize Upstream Compatibility**: Avoid massive structural refactors of upstream Onyx files. Instead, use hooks, subclassing, overriding, or isolated components wherever the language/framework permits.
3. **Document Your Patches**: If you introduce a new deviation from the upstream codebase, update `eea-artifacts/patches-overview.md` with:
   - The file(s) modified.
   - The nature of the change.
   - The reasoning behind it.
   - Any potential upstream conflicts it might cause.
4. **Keep it Clean**: Write clear, standard, and highly readable code. Do not introduce messy dependencies that conflict with Onyx's primary `package.json` or `requirements.txt` / `pyproject.toml` unless strictly necessary for EEA.
5. **Git Commands**: Always run git commands with the `--no-pager` option (e.g., `git --no-pager diff`, `git --no-pager log`). The environment is configured with a visual diff tool that may cause issues or hang when run without this option in the associated agentic terminal.

By following this strategy, we can leverage the powerful features developed by the Onyx community while securely and reliably serving EEA's specific organizational and user needs.
