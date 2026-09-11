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
   - **Missing UI Elements**: Pay special attention to the "Customize Layout" admin panel feature. If its source code is in place but missing from the UI, ensure its corresponding menu item is restored and properly wired into the updated admin sidebar/navigation.
   - **Langfuse EEA Tracing**: Follow the dedicated guide below. Ensure `eea_start_turn` is called in `build_chat_turn`, `eea_set_turn_output` is called in `llm_loop_completion_handle` with `attached_message`, and `langfuse_tracing_processor.py` propagates `user_id` to the trace entity.

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

---

# EEA Customizations: Langfuse Tracing Implementation Guide

The goal of this customization is to produce clean, well-structured traces in Langfuse for each chat turn:
- **Trace Name**: The user's actual question text (truncated to 200 chars if needed for UI limits).
- **Trace Input**: The full user question (clean, untruncated, avoiding raw prompt / system JSON).
- **Trace Output**: The final assistant answer text.
- **User ID**: Formatted as `{user_email} - {persona_name}` (with API key prefix stripped).
- **Session ID**: Composite session identifier formatted as `{session_id}:{assistant_message.id}`.

### 1. Helper Logic: `backend/onyx/utils/eea_utils.py`
Maintain turn state across the generation stream using `_eea_thread_local = threading.local()` with a session-backed dictionary fallback (to protect against thread hopping in decoupled stream worker/writer threadpools):

```python
import threading
from typing import Any

_eea_thread_local = threading.local()
_eea_turn_data_by_session: dict[str, dict[str, Any]] = {}
_eea_turn_data_lock = threading.Lock()

def get_eea_user_id(user_email: str, persona_name: str) -> str:
    """Helper to get a consistent user ID for EEA tracing."""
    user_id = user_email
    if user_id.startswith(DANSWER_API_KEY_PREFIX.lower()):
        user_id = user_id.split("@")[0].split(DANSWER_API_KEY_PREFIX.lower())[1]
    return f"{user_id} - {persona_name}"

def eea_start_turn(
    user_message: ChatMessage,
    user_email: str,
    persona_name: str,
    session_id: str,
) -> None:
    """Store turn metadata at turn initiation."""
    turn_data = {
        "user_message_id": user_message.id,
        "user_message": user_message.message,
        "user_email": user_email,
        "persona_name": persona_name,
        "session_id": session_id,
    }
    _eea_thread_local.turn_data = turn_data
    with _eea_turn_data_lock:
        _eea_turn_data_by_session[str(session_id)] = turn_data
        if len(_eea_turn_data_by_session) > 500:
            for k in list(_eea_turn_data_by_session.keys())[:100]:
                _eea_turn_data_by_session.pop(k, None)

def eea_set_turn_output(assistant_message: ChatMessage) -> None:
    """Record the completed turn with question and answer in Langfuse."""
    data: dict[str, Any] | None = getattr(_eea_thread_local, "turn_data", None)
    if data is None and hasattr(assistant_message, "chat_session_id"):
        with _eea_turn_data_lock:
            data = _eea_turn_data_by_session.pop(str(assistant_message.chat_session_id), None)

    if data is None:
        return

    try:
        from onyx.tracing.framework.create import trace, function_span

        trace_name = data["user_message"]
        if len(trace_name) > 200:
            trace_name = trace_name[:197] + "..."

        metadata = {
            "chat_session_id": f"{data['session_id']}:{assistant_message.id}",
            "assistant_message_id": assistant_message.id,
            "user_email": data["user_email"],
            "user_id": get_eea_user_id(data["user_email"], data["persona_name"]),
            "persona_name": data["persona_name"],
            "trace_name": trace_name,
            "trace_input": data["user_message"],
        }

        with trace(workflow_name=trace_name, metadata=metadata):
            with function_span(
                name=data["user_message"],
                input=data["user_message"],
                output=assistant_message.message,
            ):
                pass  # synchronous span creation and completion
    except Exception:
        logger.warning("EEA: failed to log turn to tracing framework", exc_info=True)
```

### 2. Turn Hook Injections: `backend/onyx/chat/process_message.py`
Two surgical hook calls are required:

1. **Start of turn (`build_chat_turn`)**:
   Immediately after `user_message` is created and appended to `chat_history`:
   ```python
   # EEA: store turn metadata so eea_set_turn_output() can log it later.
   from onyx.utils.eea_utils import eea_start_turn
   eea_start_turn(
       user_message=user_message,
       user_email=user.email if (user and user.email) else "anon",
       persona_name=persona.name if persona else "Default",
       session_id=str(chat_session.id),
   )
   ```

2. **Completion of turn (`llm_loop_completion_handle`)**:
   At the end of `llm_loop_completion_handle`, after `save_chat_turn` and history compression:
   ```python
   # EEA: record final answer in the active tracing span
   from onyx.utils.eea_utils import eea_set_turn_output
   eea_set_turn_output(attached_message)
   ```
   *(Note: `db_session` is NOT needed by `eea_set_turn_output`)*.

### 3. Trace Processor Propagation: `backend/onyx/tracing/langfuse_tracing_processor.py`
In `on_trace_start`:
Ensure `user_id` and `session_id` are extracted from span `metadata` and forwarded to `langfuse_span.update_trace`:
```python
session_id = metadata.get("chat_session_id")
user_id = metadata.get("user_id")
langfuse_span.update_trace(
    name=trace.name,
    session_id=session_id if session_id else None,
    user_id=str(user_id) if user_id else None,
    metadata=metadata if metadata else None,
)
```