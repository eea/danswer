---
name: smart-sync
description: Automates git merging from upstream, preserving custom fork logic and resolving refactors.
---

# Smart Sync Skill

## Context
We maintain a fork with specific customizations. Upstream merges often conflict due to simple refactors or logic changes.

## Instructions
When the user asks to "sync with upstream" or "run smart-sync":
1. **Analyze Delta**: Identify our unique customizations vs. the upstream source.
2. **Execute Merge**: Run `git fetch upstream` and `git merge upstream/main`.
3. **Resolve Conflicts**:
    - **Simple conflicts**: Auto-resolve if it's just formatting or trivial logic.
    - **Refactors**: If code moved to another file, find the new location and re-apply our changes there.
    - **Logic Changes**: If upstream changed the core logic, attempt to wrap our customization around the new logic.
4. **Safety Rail**: If a conflict changes the fundamental architectural intent, STOP and ask the user for a "Logic Review."
5. **Verify**: After merging, run `npm test` (or your specific test command) to ensure the build isn't broken.

## Advanced Conflict Resolution
When a file is moved or a component is refactored:
1. **Trace Symbol Movement**: If a component (e.g., `MyButton`) is missing in the original file, use `grep` or the IDE's symbol search to find its new location in the `upstream` tag.
2. **Import Re-mapping**: After moving our custom code to a new upstream file, automatically run a "Lint & Fix" pass to update relative import paths.
3. **Ghost Conflict Detection**: Even if Git says "No Conflict," check if an upstream file we depend on was renamed. If so, update our local references to match.
4. **TSX Specifics**: For React/Next.js files, prioritize keeping our "Props" definitions even if the component body was refactored by upstream.

## Constraints
- Do not delete our custom features.
- Always use 'Planning Mode' for conflicts involving more than 3 files.

## Post-Merge Validation
Before declaring "Done":
- Scan all modified `.tsx` and `.ts` files for `import` errors (Red squiggles).
- Verify that every custom feature identified in the "Mapping" phase still exists in the codebase.
- If a symbol is "Undefined," attempt to find its new location before asking the user.

## Automated Build & Self-Healing Loop
After the merge is complete, execute the following verification loop:

1. **Target Directory**: `cd deployment/docker_compose/eea`
2. **Action**: Run `docker compose build --no-cache`
3. **On Success**: Notify the user: "Build Successful. Sync Complete."
4. **On Failure**:
    - **Capture**: Intercept the full stderr/stdout from the docker build.
    - **Analyze**: Cross-reference the error with the recent merge changes. (e.g., Is a file missing? Is an import path broken? Is a dependency version conflicting?)
    - **Propose**: Generate a specific fix for the identified error.
    - **Notify & Wait**: Use the "Logic Review" protocol to present the error and the suggested fix to the user. Ask: "Should I apply this fix and retry the build?"
5. **Iteration**: If the user approves, apply the fix and **return to Step 2**. Repeat this loop until the build exits with code 0.