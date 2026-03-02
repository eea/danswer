import sys
import os
import datetime
import json

# Ensure the scripts directory is on sys.path for imports
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from eea_merge_utils import (
    run_cmd, get_unmerged_files, get_git_status, is_binary, save_state, run_gemini
)

SPECIAL_FILES = [
    "package.json",
    "package-lock.json",
    "pyproject.toml",
    "uv.lock",
    "requirements.txt",
]


def is_special_file(filepath):
    filename = os.path.basename(filepath)
    if filename in SPECIAL_FILES:
        return True
    if "alembic/versions" in filepath or "alembic_tenants/versions" in filepath:
        return True
    return False


def get_conflict_type(filepath):
    """Classify the conflict type and determine initial resolution strategy."""
    status = get_git_status(filepath)

    if is_binary(filepath):
        return "binary", "requires_human"

    if is_special_file(filepath):
        return "special", "programmatic_resolution"

    if status == "UU":
        return "content", "pending"
    elif status == "UD":
        # EEA modified, upstream deleted — needs human review
        return "deleted_by_them", "requires_human"
    elif status == "DU":
        # EEA deleted, upstream modified — accept upstream automatically
        return "deleted_by_us", "auto_accept_upstream"
    elif status == "AA":
        return "both_added", "pending"
    elif status == "AU":
        return "added_by_us", "pending"
    elif status == "UA":
        return "added_by_them", "pending"
    elif "R" in status:
        return "rename", "pending"

    return "unknown", "requires_human"


def auto_accept_upstream(filepath):
    """For files EEA deleted but upstream modified: accept the upstream version."""
    res_path = os.path.join(".eea_merge", "resolutions", filepath)
    os.makedirs(os.path.dirname(res_path), exist_ok=True)
    out, _, ret = run_cmd(["git", "show", f"MERGE_HEAD:{filepath}"], check=False)
    if ret == 0:
        with open(res_path, "w") as f:
            f.write(out)
        return True
    return False


def map_files_to_patches(ai_files):
    """Use a fast LLM call to map conflicted files to EEA Patch IDs."""
    if not ai_files:
        return {}

    patch_doc_path = "eea-artifacts/patches-overview.md"
    patch_content = ""
    if os.path.exists(patch_doc_path):
        with open(patch_doc_path, "r") as f:
            patch_content = f.read()

    if not patch_content:
        # No patches available, map everything to null
        return {f: None for f in ai_files}

    prompt = (
        "We are resolving git merge conflicts between our EEA fork and the Onyx upstream project.\n"
        "Below is the content of our EEA patches overview document:\n\n"
        "<patches_overview>\n"
        f"{patch_content}\n"
        "</patches_overview>\n\n"
        "Below is a list of conflicted files:\n"
        f"{json.dumps(ai_files, indent=2)}\n\n"
        "Please map each conflicted file to its relevant EEA Patch ID (e.g. \"EEA-001\") "
        "if it is documented in the overview.\n"
        "If a file does not seem to relate to any documented patch, map it to null.\n\n"
        "Output strictly valid JSON mapping filenames to patch IDs (or null).\n"
        "Format:\n"
        "{\n"
        "  \"backend/onyx/main.py\": \"EEA-001\",\n"
        "  \"web/package.json\": null\n"
        "}\n"
    )

    print("Mapping files to patches using Gemini 2.5 Flash...")
    mapping = run_gemini(prompt, model="gemini-2.5-flash", expect_json=True)
    if not mapping:
        print("Warning: Failed to map files to patches. Defaulting to null.")
        return {f: None for f in ai_files}
    return mapping


def main():
    if len(sys.argv) < 2:
        print("Usage: python eea_merge_init.py <target_tag>")
        sys.exit(1)

    target_tag = sys.argv[1]

    # 1. Branch Creation
    datestamp = datetime.datetime.now().strftime("%Y%m%d")
    branch_name = f"eea-merge-{target_tag}-{datestamp}"

    print(f"Creating and checking out branch {branch_name}...")
    run_cmd(["git", "checkout", "-b", branch_name])

    # 2. Git Prep
    print("Setting merge.conflictstyle to diff3...")
    run_cmd(["git", "config", "merge.conflictstyle", "diff3"])

    print(f"Initiating merge with {target_tag} (expecting conflicts)...")
    _, _, _ = run_cmd(["git", "merge", target_tag, "--no-commit", "--no-ff"], check=False)

    # 3. Manifest Generation
    print("Gathering unmerged files...")
    unmerged_files = get_unmerged_files()

    if not unmerged_files:
        print("No conflicts detected! The merge might have been perfectly clean.")
        save_state({})
        sys.exit(0)

    state = {}
    ai_files = []

    for f in unmerged_files:
        c_type, status = get_conflict_type(f)
        state[f] = {
            "conflict_type": c_type,
            "status": status,
            "patch_id": None,
            "retries": 0,
        }
        if status == "pending":
            ai_files.append(f)
        elif status == "auto_accept_upstream":
            # Auto-resolve: EEA deleted, upstream modified -> accept upstream
            if auto_accept_upstream(f):
                state[f]["status"] = "resolved_and_verified"
                print(f"  Auto-accepted upstream version for deleted-by-us file: {f}")
            else:
                state[f]["status"] = "requires_human"
                print(f"  Failed to auto-accept upstream for: {f}")

    # 6. The Mapping Pass
    patch_mapping = map_files_to_patches(ai_files)
    for f, patch_id in patch_mapping.items():
        if f in state:
            state[f]["patch_id"] = patch_id

    # 7. Save state
    save_state(state)

    # 8. Summary Output
    auto_resolved = len([f for f in state if state[f]["conflict_type"] == "deleted_by_us" and state[f]["status"] == "resolved_and_verified"])
    programmatic_count = len([f for f in state if state[f]["status"] == "programmatic_resolution"])
    human_count = len([f for f in state if state[f]["status"] == "requires_human"])

    print(f"\n--- Conflict Summary ---")
    print(f"Total unmerged files: {len(unmerged_files)}")
    print(f"Pending AI resolution: {len(ai_files)}")
    print(f"Auto-accepted (deleted by us): {auto_resolved}")
    print(f"Programmatic resolution: {programmatic_count}")
    print(f"Requires human intervention: {human_count}")
    print(f"Estimated LLM calls: {len(ai_files)} (+ retries)")
    print("------------------------\n")


if __name__ == "__main__":
    main()
