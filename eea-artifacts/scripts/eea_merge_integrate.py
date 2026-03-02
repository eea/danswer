import os
import sys
import shutil
import glob

# Ensure the scripts directory is on sys.path for imports
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from eea_merge_utils import load_state, run_cmd, VENV_PYTHON


def phase3_integration(state):
    """Copy resolved files from .eea_merge/resolutions/ to the working tree and git add."""
    print("\n--- Phase 3: Integration & Staging ---")
    failed_or_human = []

    for filepath, entry in state.items():
        if entry["status"] == "resolved_and_verified":
            res_path = os.path.join(".eea_merge", "resolutions", filepath)
            if os.path.exists(res_path):
                # Ensure target directory exists (for new files)
                target_dir = os.path.dirname(filepath)
                if target_dir:
                    os.makedirs(target_dir, exist_ok=True)
                shutil.copy2(res_path, filepath)
                run_cmd(["git", "add", filepath])
            else:
                print(f"Error: Resolved file {res_path} not found.")
                failed_or_human.append(filepath)
        else:
            failed_or_human.append(filepath)

    # Integrity check: verify no conflict markers remain in staged files
    print("Running git diff --check on staged files...")
    out, err, ret = run_cmd(["git", "diff", "--check", "--cached"], check=False)
    if ret != 0:
        print("Warning: git diff --check found potential issues in staged files.")
        print(out)

    if failed_or_human:
        print("\nThe following files require HUMAN INTERVENTION:")
        for f in failed_or_human:
            status = state[f]["status"] if f in state else "unknown"
            print(f"  - {f} (Status: {status})")

    return len(failed_or_human) == 0, failed_or_human


def phase4_validation():
    """Full-project build validation to catch semantic integration errors."""
    print("\n--- Phase 4: Post-Merge Validation (Full-Project Build) ---")
    passed = True

    # 1. Backend: ruff check
    print("Running ruff check backend/ ...")
    if os.path.exists("backend"):
        out, err, ret = run_cmd(
            [VENV_PYTHON, "-m", "ruff", "check", "backend/"],
            check=False
        )
        if ret != 0:
            print(f"Backend ruff check FAILED:\n{out}\n{err}")
            passed = False
        else:
            print("Backend ruff check passed.")

    # 2. Frontend: npm install & tsc --noEmit
    print("Running frontend validation (npm install & tsc) ...")
    if os.path.exists("web"):
        out, err, ret = run_cmd(["npm", "install"], cwd="web", check=False)
        if ret != 0:
            print(f"Frontend npm install FAILED:\n{err}")
            passed = False
        else:
            out, err, ret = run_cmd(["npx", "tsc", "--noEmit"], cwd="web", check=False)
            if ret != 0:
                print(f"Frontend tsc check FAILED:\n{out}\n{err}")
                passed = False
            else:
                print("Frontend validation passed.")

    # 3. Alembic migration chain verification
    print("Running Alembic migration chain verification...")
    alembic_ok = verify_alembic_chain()
    if not alembic_ok:
        passed = False

    return passed


def verify_alembic_chain():
    """
    Walk Alembic migration files and verify that every down_revision
    points to an existing revision (or is None for the root).
    Checks both alembic/versions and alembic_tenants/versions directories.
    """
    all_ok = True

    for versions_dir in ["backend/alembic/versions", "backend/alembic_tenants/versions"]:
        if not os.path.exists(versions_dir):
            continue

        print(f"  Checking {versions_dir}...")
        revisions = {}       # revision_id -> filepath
        down_revisions = {}  # revision_id -> down_revision (or None)

        migration_files = glob.glob(os.path.join(versions_dir, "*.py"))
        for mf in migration_files:
            revision_id = None
            down_revision = None
            try:
                with open(mf, "r") as f:
                    for line in f:
                        stripped = line.strip()
                        if stripped.startswith("revision") and "=" in stripped and not stripped.startswith("down_revision"):
                            # Parse: revision = "abc123"
                            val = stripped.split("=", 1)[1].strip().strip("'\"")
                            revision_id = val
                        elif stripped.startswith("down_revision") and "=" in stripped:
                            val = stripped.split("=", 1)[1].strip().strip("'\"")
                            if val in ("None", ""):
                                down_revision = None
                            else:
                                down_revision = val
            except Exception as e:
                print(f"    Warning: Could not parse {mf}: {e}")
                continue

            if revision_id:
                revisions[revision_id] = mf
                down_revisions[revision_id] = down_revision

        # Verify chain integrity: every down_revision must point to an existing revision
        broken = 0
        for rev_id, down_rev in down_revisions.items():
            if down_rev is not None and down_rev not in revisions:
                print(f"    ERROR: Revision {rev_id} points to down_revision "
                      f"{down_rev} which does not exist!")
                print(f"           File: {revisions[rev_id]}")
                all_ok = False
                broken += 1

        if broken == 0:
            print(f"    {versions_dir}: {len(revisions)} migration(s), chain OK.")

    return all_ok


def main():
    if len(sys.argv) < 2:
        print("Usage: python eea_merge_integrate.py <target_tag>")
        sys.exit(1)

    target_tag = sys.argv[1]
    state = load_state()

    if not state:
        print("No state found. Aborting integration.")
        sys.exit(1)

    p3_success, failed_files = phase3_integration(state)
    p4_success = phase4_validation()

    print("\n--- Phase 5: Commit or Abort ---")
    if p3_success and p4_success:
        commit_msg = f"Merge upstream tag {target_tag} (Automated AI Resolution)"
        print(f"All checks passed. Committing merge: '{commit_msg}'")
        run_cmd(["git", "commit", "-m", commit_msg])
        print("\nSuccess! The merge was completed automatically.")
        sys.exit(0)
    else:
        print("\nMERGE NOT COMMITTED.")
        print("Reasons:")
        if not p3_success:
            print(f"  - {len(failed_files)} file(s) require human resolution.")
        if not p4_success:
            print("  - Post-merge validation (Phase 4) failed.")
        print("\nThe .eea_merge/ directory has been preserved for debugging.")
        print("Options:")
        print("  - Fix remaining issues manually, then run: git commit")
        print("  - Abort the merge entirely: git merge --abort")
        print("  - Re-run Phase 2 for specific files: edit state.json, re-run eea_merge_resolve.py")
        sys.exit(1)


if __name__ == "__main__":
    main()
