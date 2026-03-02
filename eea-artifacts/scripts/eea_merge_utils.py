import subprocess
import json
import os
import sys
import datetime

STATE_FILE = ".eea_merge/state.json"
TOOLS_DIR = ".eea_merge/.tools"
LOGS_DIR = ".eea_merge/logs"
PROMPTS_DIR = ".eea_merge/prompts"
VENV_PYTHON = os.path.join(TOOLS_DIR, "python_env", "bin", "python")


def run_cmd(cmd, cwd=None, check=True, capture_output=True, env=None):
    try:
        res = subprocess.run(
            cmd,
            cwd=cwd,
            check=check,
            capture_output=capture_output,
            text=True,
            shell=isinstance(cmd, str),
            env=env
        )
        return res.stdout, res.stderr, res.returncode
    except subprocess.CalledProcessError as e:
        if check:
            print(f"Command failed: {cmd}")
            if capture_output:
                print(f"STDOUT: {e.stdout}")
                print(f"STDERR: {e.stderr}")
            sys.exit(e.returncode)
        return e.stdout, e.stderr, e.returncode


def load_state():
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE, "r") as f:
        return json.load(f)


def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def run_gemini(prompt, model="gemini-3.1-pro-preview", expect_json=True):
    cmd = ["gemini", "-m", model]

    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    stdout, stderr = process.communicate(input=prompt)
    if process.returncode != 0:
        print(f"Gemini API failed with error:\n{stderr}")
        return None

    out = stdout.strip()

    # Simple JSON extraction if wrapped in markdown fences
    if expect_json:
        if out.startswith("```json"):
            out = out[7:]
            if out.endswith("```"):
                out = out[:-3]
        elif out.startswith("```"):
            out = out[3:]
            if out.endswith("```"):
                out = out[:-3]

        try:
            return json.loads(out)
        except json.JSONDecodeError as e:
            print(f"Failed to parse Gemini JSON output:\n{out}\nError: {e}")
            return None

    return out


def get_unmerged_files():
    out, _, _ = run_cmd(["git", "diff", "--name-only", "--diff-filter=U"])
    return [line for line in out.strip().split("\n") if line]


def get_git_status(filepath):
    out, _, _ = run_cmd(["git", "status", "--porcelain", filepath])
    status = out[:2] if out else ""
    return status


def is_binary(filepath):
    out, _, _ = run_cmd(["git", "diff", "--numstat", filepath], check=False)
    if out and out.startswith("-\t-"):
        return True
    return False


def check_gemini_available():
    _, _, returncode = run_cmd(["gemini", "--version"], check=False)
    return returncode == 0


def save_prompt(filepath, prompt, attempt):
    """Save a prompt to the prompts directory for auditing/debugging."""
    os.makedirs(PROMPTS_DIR, exist_ok=True)
    safe_name = filepath.replace("/", "_").replace("\\", "_")
    prompt_file = os.path.join(PROMPTS_DIR, f"{safe_name}_attempt{attempt}.txt")
    with open(prompt_file, "w") as f:
        f.write(prompt)


def log_validation(filepath, attempt, validator, passed, message):
    """Write validation results to the logs directory."""
    os.makedirs(LOGS_DIR, exist_ok=True)
    safe_name = filepath.replace("/", "_").replace("\\", "_")
    log_file = os.path.join(LOGS_DIR, f"{safe_name}_attempt{attempt}.log")
    timestamp = datetime.datetime.now().isoformat()
    with open(log_file, "a") as f:
        f.write(f"[{timestamp}] Validator: {validator}\n")
        f.write(f"Result: {'PASS' if passed else 'FAIL'}\n")
        f.write(f"Message:\n{message}\n")
        f.write("-" * 60 + "\n")


def load_prompt_template(template_name):
    """Load a prompt template from eea-artifacts/scripts/prompts/."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(script_dir, "prompts", template_name)
    with open(template_path, "r") as f:
        return f.read()
