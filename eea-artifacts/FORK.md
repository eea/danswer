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

1. **Read `eea-artifacts/patches-overview.md`** first to get a high-level view of existing customizations.
2. **Consult Patch Artifacts:** For detailed architectural intent and files modified by specific patches, read the corresponding `eea-artifacts/patches/EEA-XXX.md` file.
3. **Prioritize Upstream Compatibility**: Avoid massive structural refactors of upstream Onyx files. Instead, use hooks, subclassing, overriding, or isolated components wherever the language/framework permits.
4. **Document Your Patches**: If you introduce a new deviation from the upstream codebase:
   - Create a new `EEA-XXX.md` file in `eea-artifacts/patches/` detailing the files modified, your intent, and how to migrate the changes during upstream updates.
   - Update `eea-artifacts/patches-overview.md` with a bullet point linking to your new patch file.
   - Keep comments in the code (e.g., `// EEA CUSTOMIZATION: ...`) to link back to the patch ID where appropriate.
5. **Keep it Clean**: Write clear, standard, and highly readable code. Do not introduce messy dependencies that conflict with Onyx's primary `package.json` or `requirements.txt` / `pyproject.toml` unless strictly necessary for EEA.
6. **Git Commands**: To avoid issues with visual diff tools or interactive pagers in the terminal, always prefix git commands with `env GIT_PAGER=cat` (e.g., `env GIT_PAGER=cat git diff`). This ensures that the output is printed directly to the terminal without hanging or requiring user interaction.

By following this strategy, we can leverage the powerful features developed by the Onyx community while securely and reliably serving EEA's specific organizational and user needs.
