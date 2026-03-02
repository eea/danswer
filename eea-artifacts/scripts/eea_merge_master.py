import sys
import os

# Ensure the scripts directory is on sys.path for imports
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from eea_merge_utils import run_cmd, check_gemini_available


def preflight_checks(target_tag):
    print("Running pre-flight checks...")

    # 1. Clean working tree
    out, _, _ = run_cmd(["git", "status", "--porcelain"])
    if out.strip():
        print("Error: Working tree is not clean. Please commit or stash your changes before upgrading.")
        sys.exit(1)

    # 2. Source branch
    out, _, _ = run_cmd(["git", "branch", "--show-current"])
    current_branch = out.strip()
    if current_branch != "eea":
        print(f"Warning: Current branch is '{current_branch}', not 'eea'.")
        print("Proceeding anyway, but ensure this is correct.")

    # 3. Tag exists
    _, _, returncode = run_cmd(["git", "rev-parse", target_tag], check=False, capture_output=True)
    if returncode != 0:
        print(f"Tag {target_tag} not found locally. Fetching from onyx...")
        out, err, ret = run_cmd(["git", "fetch", "onyx", "tag", target_tag], check=False)
        if ret != 0:
            print(f"Failed to fetch tag {target_tag} from remote 'onyx'. Trying 'origin'...")
            out, err, ret = run_cmd(["git", "fetch", "origin", "tag", target_tag], check=False)
            if ret != 0:
                print(f"Error: Target tag {target_tag} does not exist.")
                sys.exit(1)

    # 4. gemini available
    if not check_gemini_available():
        print("Error: 'gemini' CLI is not available on PATH or not authenticated.")
        sys.exit(1)

    print("Pre-flight checks passed.\n")


def setup_environment():
    """Phase -1: Environment Bootstrap — isolated Python venv with pinned tools."""
    print("--- Phase -1: Environment Bootstrap ---")
    print("Setting up isolated Python environment...")
    tools_dir = ".eea_merge/.tools"
    venv_dir = os.path.join(tools_dir, "python_env")

    if not os.path.exists(venv_dir):
        run_cmd(["python3", "-m", "venv", venv_dir])

    pip_path = os.path.join(venv_dir, "bin", "pip")
    print("Installing ruff and yamllint...")
    run_cmd([pip_path, "install", "ruff", "yamllint"])
    print("Environment setup complete.\n")


def main():
    if len(sys.argv) < 2:
        print("Usage: python eea_merge_master.py <target_tag>")
        sys.exit(1)

    target_tag = sys.argv[1]

    # Create the full directory structure up front
    os.makedirs(".eea_merge/.tools", exist_ok=True)
    os.makedirs(".eea_merge/prompts", exist_ok=True)
    os.makedirs(".eea_merge/resolutions", exist_ok=True)
    os.makedirs(".eea_merge/logs", exist_ok=True)
    os.makedirs(".eea_merge/backups", exist_ok=True)

    preflight_checks(target_tag)
    setup_environment()

    # Execute Phase 1
    init_script = os.path.join(SCRIPT_DIR, "eea_merge_init.py")
    print(">>> Phase 1: Setup & Context Mapping")
    out, _, ret = run_cmd([sys.executable, init_script, target_tag], check=False)
    print(out)
    if ret != 0:
        print("Phase 1 failed. Aborting.")
        sys.exit(1)

    # Execute Phase 2
    resolve_script = os.path.join(SCRIPT_DIR, "eea_merge_resolve.py")
    print(">>> Phase 2: Self-Correcting Resolution Loop")
    out, _, ret = run_cmd([sys.executable, resolve_script], check=False)
    print(out)
    if ret != 0:
        print("Phase 2 failed. Aborting.")
        sys.exit(1)

    # Execute Phase 3, 4, 5
    integrate_script = os.path.join(SCRIPT_DIR, "eea_merge_integrate.py")
    print(">>> Phase 3-5: Integration, Validation & Commit")
    out, _, ret = run_cmd([sys.executable, integrate_script, target_tag], check=False)
    print(out)
    if ret != 0:
        print("Post-resolution pipeline failed. See above for details.")
        sys.exit(1)

    print(f"\nSuccessfully resolved and merged {target_tag}!")


if __name__ == "__main__":
    main()
