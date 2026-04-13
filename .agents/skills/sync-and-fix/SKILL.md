---
name: sync-and-fix
description: Merges a target upstream tag, resolves conflicts using the customization_map, and stabilizes the Docker stack.
---

# Sync & Fix Workflow
When this skill is invoked with a `{target_upstream_tag}`:

1. **The Merge**:
   - `git fetch upstream`
   - Attempt `git merge {target_upstream_tag}`.
   - If conflicts occur, refer to `customization_map.md` to determine which version (ours vs. upstream) preserves the "Intent."

2. **The Refactor Check**:
   - For every "Intent" in the map, verify the logic still exists in the code.
   - If files were moved/renamed in the upstream, use the "Re-implementation Guide" from the map to restore the feature.

3. **The Docker Fix-Loop**:
   - Run `docker compose build`.
   - **On Failure**: Feed the build logs back to the agent. Fix the code/dependencies and retry.
   - Run `docker compose up -d`.
   - **On Failure**: Check container logs for runtime errors (Python imports, React build errors). Fix and retry.

4. **Tagging**:
   - Once the stack is healthy and tests pass, create a new fork tag: `{target_upstream_tag}-eea.{new_version}`.

# Technical Guardrails
- Always prioritize the `customization_map.md` specs over raw git conflict markers.
- Never delete a "New File" (flagged in the audit) even if it's not used in the new upstream version.