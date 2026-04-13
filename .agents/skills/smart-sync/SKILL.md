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

## Feature-Specific Rules: Langfuse & LiteLLM
We have a critical customization that adds metadata to all `litellm` calls for Langfuse tracing.

1. **Identify Call Sites**: Search for all instances of `completion(`, `litellm.completion(`, or `get_llm_callback`.
2. **Inject Metadata**: Ensure every call includes a `metadata` parameter with the following keys if they are missing:
    - `generation_name`: Should match the feature calling it (e.g., "deep_research" or "standard_query").
    - `trace_id` / `tags`: Ensure our Langfuse environment tags are preserved.
3. **Deep Research Special Case**: In the "Deep Research" module (likely under `danswer/tools/search` or similar), ensure the recursive/agentic calls pass through the `metadata` dictionary to all child spans.
4. **Validation**: If a merge removes a `metadata` argument from a LiteLLM call, flag this as a "Logic Violation" and re-apply our implementation from commits `bdc0955` and `8d3f8e1`.
5. **Onyx Tracing Processor (Deep Research)**:
    - **Target File**: `danswer/backend/onyx/tracing/langfuse_tracing_processor.py`
    - **Logic**: Identify where the "Generation with" string is constructed. 
    - **Modification**: If the metadata indicates a "Clarification Step", set the name to: `Clarification needed for "<original_question>"` (where `<original_question>` is extracted from the metadata context).Ensure the processor pulls from the `extra_metadata` or `tags` passed in the LiteLLM call. The modifications should be as minimal as possible. Do not add any new dependencies or change the overall structure of the file.
    - **Consistency**: The processor must prioritize the metadata we injected in the LiteLLM call over its own default naming conventions.

## Global LLM Metadata Audit
Before finalizing the merge, the agent must perform a "Call Trace Audit":

1. **Discovery**: Scan the entire `onyx/` and `danswer/` directories for any imports of `litellm` or references to `completion`, `get_llm_callback`, or `get_default_llm`.
2. **Branch Analysis**: For every identified call site:
    - Trace the logic backwards to the entry point (e.g., `dr_loop`, `standard_search`).
    - Check all conditional branches (`if/elif/else`) and `try/except` blocks.
    - **Requirement**: Every single logical path that leads to an LLM call MUST include the `metadata` dictionary.
3. **Parameter Propagation**: If a helper function is called that eventually triggers an LLM, ensure the `metadata` is passed as an argument through the entire chain.
4. **Validation**: Use static analysis to flag any `completion()` call that does not explicitly pass a `metadata=` argument. Fix these by injecting the contextually relevant metadata (including the `original_question` for naming).

## Constraints
- Do not delete our custom features.
- Always use 'Planning Mode' for conflicts involving more than 3 files.

## Post-Merge Validation
Before declaring "Done":
- Scan all modified `.tsx` and `.ts` files for `import` errors (Red squiggles).
- Verify that every custom feature identified in the "Mapping" phase still exists in the codebase.
- If a symbol is "Undefined," attempt to find its new location before asking the user.

## Automated Build & Runtime Self-Healing Loop
Execute the following verification steps in order:

### Phase 1: Build Check
1. **Target Directory**: `cd deployment/docker_compose/eea`
2. **Action**: Run `docker compose build --no-cache`
3. **On Build Failure**:
    - **Analyze**: Intercept stderr. Cross-reference with recent merge changes (missing files, broken imports, etc.).
    - **Propose & Wait**: Generate a fix, notify the user via "Logic Review," and if approved, apply and restart Phase 1.

### Phase 2: Runtime Check (API Server)
4. **Action**: Run `docker compose up -d`
5. **Monitor**: Run `docker compose logs -f api-server` for 30 seconds.
6. **On Runtime Failure**:
    - **Detection**: If `api-server` exits or the logs contain a Python Traceback (e.g., `ImportError`, `AttributeError`, `ModuleNotFoundError`).
    - **Analyze**: Compare the Traceback symbols against the `upstream` changes. (e.g., "Did the upstream change a database schema or an environment variable name?")
    - **Heal**: 
        - Stop the stack: `docker compose down`.
        - Propose the fix to the user.
        - If approved, apply the fix and **return to Phase 1 (Step 2)** to ensure the fix doesn't break the build.
7. **On Success**: Once logs show "Application startup complete" or no errors for 30s, notify user: "Build & Runtime Successful. Sync Complete."