import os
import sys
import shutil
import json

# Ensure the scripts directory is on sys.path for imports
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from eea_merge_utils import (
    load_state, save_state, run_cmd, run_gemini, VENV_PYTHON,
    save_prompt, log_validation
)

MAX_RETRIES = {
    ".py": 3,
    ".ts": 2,
    ".tsx": 2,
    "default": 2,
}


def backup_file(filepath):
    """Copy the conflicted file to .eea_merge/backups/ before any processing."""
    backup_dir = os.path.join(".eea_merge", "backups")
    os.makedirs(backup_dir, exist_ok=True)
    safe_name = filepath.replace("/", "_").replace("\\", "_")
    backup_path = os.path.join(backup_dir, safe_name)
    if os.path.exists(filepath):
        shutil.copy2(filepath, backup_path)
    return backup_path


def has_conflict_markers(content):
    """Check if the content still contains git conflict markers."""
    markers = ["<<<<<<<", "|||||||", "=======", ">>>>>>>"]
    for line in content.splitlines():
        for marker in markers:
            if line.startswith(marker):
                return True
    return False


def run_file_validation(filepath, content, attempt):
    """Validate resolved content — write to resolutions/ and run appropriate linter."""
    res_path = os.path.join(".eea_merge", "resolutions", filepath)
    os.makedirs(os.path.dirname(res_path), exist_ok=True)
    with open(res_path, "w") as f:
        f.write(content)

    if has_conflict_markers(content):
        msg = "File still contains git conflict markers (<<<<<<<, =======, etc)."
        log_validation(filepath, attempt, "conflict_markers", False, msg)
        return False, msg

    ext = os.path.splitext(filepath)[1]

    if ext == ".py":
        out, err, ret = run_cmd(
            [VENV_PYTHON, "-m", "ruff", "check", "--select=E9", res_path],
            check=False
        )
        if ret != 0:
            msg = f"Ruff syntax check failed:\n{out}\n{err}"
            log_validation(filepath, attempt, "ruff", False, msg)
            return False, msg
        log_validation(filepath, attempt, "ruff", True, "Passed")

    elif ext in [".yaml", ".yml"]:
        out, err, ret = run_cmd(
            [VENV_PYTHON, "-m", "yamllint", "-d", "relaxed", res_path],
            check=False
        )
        if ret != 0:
            msg = f"Yamllint failed:\n{out}\n{err}"
            log_validation(filepath, attempt, "yamllint", False, msg)
            return False, msg
        log_validation(filepath, attempt, "yamllint", True, "Passed")

    elif ext == ".json":
        out, err, ret = run_cmd(
            [sys.executable, "-m", "json.tool", res_path],
            check=False
        )
        if ret != 0:
            msg = f"JSON validation failed:\n{err}"
            log_validation(filepath, attempt, "json.tool", False, msg)
            return False, msg
        log_validation(filepath, attempt, "json.tool", True, "Passed")

    else:
        log_validation(filepath, attempt, "conflict_markers_only", True,
                       "No specific linter for this file type; marker check passed.")

    return True, "Passed"


def resolve_file(filepath, state_entry, patches_content):
    """Run the self-correcting AI resolution loop for a single file."""
    ext = os.path.splitext(filepath)[1]
    max_retries = MAX_RETRIES.get(ext, MAX_RETRIES["default"])
    conflict_type = state_entry.get("conflict_type", "content")

    with open(filepath, "r") as f:
        file_content = f.read()

    # Build patch context
    patch_id = state_entry.get("patch_id")
    if patch_id and patches_content:
        patch_info = (
            f"This file is related to EEA Patch {patch_id}. "
            f"Please ensure the custom logic described in the patch is preserved."
        )
    else:
        patch_info = (
            "No EEA patch documentation exists for this file. "
            "Prefer upstream changes. Preserve any lines clearly marked with "
            "`// EEA` or `# EEA` comments."
        )

    # Special note for both_added conflicts (no common base ancestor)
    both_added_note = ""
    if conflict_type == "both_added":
        both_added_note = (
            "\n**IMPORTANT:** This is a 'both added' conflict — both sides created "
            "this file independently. There is NO common base ancestor. You must "
            "intelligently merge both versions, keeping EEA-specific additions while "
            "adopting upstream structure where appropriate.\n"
        )

    base_prompt = (
        f"We are resolving a git merge conflict for the file: `{filepath}`.\n"
        f"{patch_info}\n"
        f"{both_added_note}\n"
        "Here is the conflicted file content with `diff3` markers "
        "(<<<<<<< HEAD, ||||||| merged common ancestors, =======, >>>>>>> MERGE_HEAD):\n\n"
        "```\n"
        f"{file_content}\n"
        "```\n\n"
        "Instructions:\n"
        "1. Analyze the divergence between HEAD (EEA fork) and MERGE_HEAD (Upstream).\n"
        "2. Write an analysis explaining the intent of both sides and your resolution strategy.\n"
        "3. Provide the full, perfectly resolved file content without any git conflict markers.\n\n"
        "Output strictly valid JSON in this format:\n"
        "{\n"
        "  \"analysis\": {\n"
        "    \"eea_intent\": \"...\",\n"
        "    \"upstream_intent\": \"...\",\n"
        "    \"strategy\": \"...\"\n"
        "  },\n"
        "  \"resolved_file_content\": \"...\"\n"
        "}\n"
    )

    current_prompt = base_prompt

    while state_entry["retries"] <= max_retries:
        attempt = state_entry["retries"] + 1
        print(f"  Attempt {attempt} for {filepath}...")

        # Save the prompt for auditing
        save_prompt(filepath, current_prompt, attempt)

        result = run_gemini(current_prompt, model="gemini-2.5-pro", expect_json=True)

        if not result or "resolved_file_content" not in result:
            err_msg = "Failed to parse valid JSON from Gemini or missing 'resolved_file_content'."
            print(f"  {err_msg}")
            log_validation(filepath, attempt, "json_parse", False, err_msg)
            current_prompt = (
                base_prompt +
                f"\n\nERROR ON PREVIOUS ATTEMPT:\n{err_msg}\n"
                "Please ensure strictly valid JSON."
            )
            state_entry["retries"] += 1
            continue

        resolved_content = result["resolved_file_content"]

        # Log the AI's analysis for auditing
        if "analysis" in result:
            log_validation(
                filepath, attempt, "ai_analysis", True,
                json.dumps(result["analysis"], indent=2)
            )

        is_valid, val_msg = run_file_validation(filepath, resolved_content, attempt)

        if is_valid:
            print(f"  Successfully resolved and validated {filepath}.")
            state_entry["status"] = "resolved_and_verified"
            return True

        print(f"  Validation failed for {filepath}: {val_msg}")
        current_prompt = (
            base_prompt +
            f"\n\nYOUR PREVIOUS RESOLUTION FAILED VALIDATION:\n{val_msg}\n"
            "Please fix the errors and try again."
        )
        state_entry["retries"] += 1

    print(f"  Exhausted retries for {filepath}.")
    state_entry["status"] = "failed_requires_human"
    return False


# ---------------------------------------------------------------------------
# Programmatic resolution helpers (for special files: package.json, etc.)
# ---------------------------------------------------------------------------

def get_merge_base():
    """Get the merge-base commit between HEAD and MERGE_HEAD."""
    out, _, ret = run_cmd(["git", "merge-base", "HEAD", "MERGE_HEAD"], check=False)
    if ret == 0:
        return out.strip()
    return None


def get_eea_specific_deps_json(filepath, merge_base):
    """
    Diff the EEA branch's package.json against the merge-base to find
    EEA-specific dependency additions.
    Returns (eea_deps, eea_dev_deps) dicts of {name: version}.
    """
    base_content, _, ret = run_cmd(["git", "show", f"{merge_base}:{filepath}"], check=False)
    if ret != 0:
        return {}, {}

    eea_content, _, ret = run_cmd(["git", "show", f"HEAD:{filepath}"], check=False)
    if ret != 0:
        return {}, {}

    try:
        base_json = json.loads(base_content)
        eea_json = json.loads(eea_content)
    except json.JSONDecodeError:
        return {}, {}

    eea_deps = {}
    eea_dev_deps = {}

    for dep_key, eea_target in [
        ("dependencies", eea_deps),
        ("devDependencies", eea_dev_deps),
    ]:
        base_dict = base_json.get(dep_key, {})
        eea_dict = eea_json.get(dep_key, {})
        for name, version in eea_dict.items():
            if name not in base_dict:
                eea_target[name] = version

    return eea_deps, eea_dev_deps


def get_eea_specific_deps_python(filepath, merge_base):
    """
    Diff the EEA branch's requirements.txt (or pyproject.toml) against the
    merge-base to find EEA-specific dependency additions.
    Returns a list of lines added by EEA.
    """
    base_content, _, ret = run_cmd(["git", "show", f"{merge_base}:{filepath}"], check=False)
    if ret != 0:
        return []

    eea_content, _, ret = run_cmd(["git", "show", f"HEAD:{filepath}"], check=False)
    if ret != 0:
        return []

    base_lines = set(base_content.strip().splitlines())
    eea_lines = eea_content.strip().splitlines()

    # Lines present in EEA but not in the merge-base
    added = [line for line in eea_lines if line.strip() and line not in base_lines]
    return added


def programmatic_resolution(filepath, state_entry):
    """Handle special files programmatically instead of via AI."""
    print(f"Executing programmatic resolution for {filepath}...")
    res_path = os.path.join(".eea_merge", "resolutions", filepath)
    os.makedirs(os.path.dirname(res_path), exist_ok=True)

    filename = os.path.basename(filepath)
    merge_base = get_merge_base()

    # --- Alembic migrations: accept upstream ---
    if "alembic" in filepath:
        out, _, ret = run_cmd(["git", "show", f"MERGE_HEAD:{filepath}"], check=False)
        if ret == 0:
            with open(res_path, "w") as f:
                f.write(out)
        return True

    # --- package.json: accept upstream + re-inject EEA deps ---
    if filename == "package.json" and merge_base:
        upstream_content, _, ret = run_cmd(["git", "show", f"MERGE_HEAD:{filepath}"], check=False)
        if ret != 0:
            print(f"  Warning: Could not read upstream version of {filepath}")
            return False

        try:
            upstream_json = json.loads(upstream_content)
        except json.JSONDecodeError:
            print(f"  Warning: Could not parse upstream {filepath} as JSON, accepting raw.")
            with open(res_path, "w") as f:
                f.write(upstream_content)
            return True

        eea_deps, eea_dev_deps = get_eea_specific_deps_json(filepath, merge_base)

        if eea_deps:
            upstream_json.setdefault("dependencies", {}).update(eea_deps)
            print(f"  Re-injected EEA dependencies: {list(eea_deps.keys())}")

        if eea_dev_deps:
            upstream_json.setdefault("devDependencies", {}).update(eea_dev_deps)
            print(f"  Re-injected EEA devDependencies: {list(eea_dev_deps.keys())}")

        with open(res_path, "w") as f:
            json.dump(upstream_json, f, indent=2)
            f.write("\n")
        return True

    # --- Lockfiles: accept upstream (regenerated later by npm install / uv lock) ---
    if filename in ("package-lock.json", "uv.lock"):
        out, _, ret = run_cmd(["git", "show", f"MERGE_HEAD:{filepath}"], check=False)
        if ret == 0:
            with open(res_path, "w") as f:
                f.write(out)
        return True

    # --- pyproject.toml / requirements.txt: accept upstream + re-inject EEA deps ---
    if filename in ("pyproject.toml", "requirements.txt") and merge_base:
        upstream_content, _, ret = run_cmd(["git", "show", f"MERGE_HEAD:{filepath}"], check=False)
        if ret != 0:
            print(f"  Warning: Could not read upstream version of {filepath}")
            return False

        eea_added = get_eea_specific_deps_python(filepath, merge_base)

        if eea_added:
            content = upstream_content.rstrip("\n") + "\n"
            content += "\n# EEA-specific dependencies (re-injected during merge)\n"
            for line in eea_added:
                content += line + "\n"
            print(f"  Re-injected {len(eea_added)} EEA-specific line(s) into {filename}")
            with open(res_path, "w") as f:
                f.write(content)
        else:
            with open(res_path, "w") as f:
                f.write(upstream_content)
        return True

    # --- Fallback: accept upstream ---
    out, _, ret = run_cmd(["git", "show", f"MERGE_HEAD:{filepath}"], check=False)
    if ret == 0:
        with open(res_path, "w") as f:
            f.write(out)
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    state = load_state()
    if not state:
        print("No state found. Did Phase 1 run correctly?")
        sys.exit(1)

    patch_doc_path = "eea-artifacts/patches-overview.md"
    patches_content = ""
    if os.path.exists(patch_doc_path):
        with open(patch_doc_path, "r") as f:
            patches_content = f.read()

    # Phase 2a: AI resolution for pending files (sequential, one at a time)
    for filepath, entry in state.items():
        if entry["status"] == "pending":
            print(f"\nResolving {filepath}...")
            backup_file(filepath)
            resolve_file(filepath, entry, patches_content)
            save_state(state)

    # Phase 2b: Programmatic resolution for special files
    for filepath, entry in state.items():
        if entry["status"] == "programmatic_resolution":
            if programmatic_resolution(filepath, entry):
                entry["status"] = "resolved_and_verified"
            else:
                entry["status"] = "failed_requires_human"
            save_state(state)

    # Summary
    resolved = len([f for f in state if state[f]["status"] == "resolved_and_verified"])
    failed = len([f for f in state if state[f]["status"] == "failed_requires_human"])
    human = len([f for f in state if state[f]["status"] == "requires_human"])

    print("\nPhase 2 Complete.")
    print(f"  Resolved: {resolved}")
    print(f"  Failed (needs human): {failed}")
    print(f"  Requires human: {human}")


if __name__ == "__main__":
    main()
