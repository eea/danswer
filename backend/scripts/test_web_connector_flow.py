"""
End-to-end smoke test for Web connectors.

`run` creates one or more Web connectors against a live Onyx deployment (or,
with --connector-id, triggers re-indexing of an existing connector instead),
polls until the latest index attempt reaches a terminal state, and prints a
detailed pass/fail report. Useful for confirming that docfetching,
docprocessing, and the light worker (vespa sync) are all healthy end-to-end
on a given deployment (e.g. a helm-deployed stack).

`run` never deletes anything, including connectors it just created. Deletion
is a fully separate subcommand (`delete`) that requires an explicit
connector/credential id and --yes confirmation, so a connector is never
deleted as a side effect of running a test.

Usage:
    python scripts/test_web_connector_flow.py run --base-url https://onyx.example.com
    python scripts/test_web_connector_flow.py run --connector-id 1246 --base-url ...
    python scripts/test_web_connector_flow.py delete --connector-id 1246 \\
        --credential-id 1221 --yes --base-url ...

Auth defaults to email/password login.
Override with --email/--password or ONYX_EMAIL/ONYX_PASSWORD env vars.
Use --api-key for deployments using SSO (e.g. EntraID) instead.
"""

import argparse
import dataclasses
import os
import sys
import time
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=True)


@dataclasses.dataclass
class WebConnectorTestCase:
    name: str
    base_url: str
    web_connector_type: str = "single"  # "single", "recursive", or "sitemap"


# All smoke-test connector names must start with this prefix.
SMOKE_TEST_NAME_PREFIX = "smoke-test-"

# Array of connectors to test. Add/remove entries as needed. Ignored when
# --connector-id is passed to `run`.
CONNECTORS_TO_TEST: list[WebConnectorTestCase] = [
    WebConnectorTestCase(
        name=f"{SMOKE_TEST_NAME_PREFIX}single-page",
        base_url="https://onyx.app",
        web_connector_type="single",
    ),
]

TERMINAL_STATUSES = {"success", "failed", "canceled", "completed_with_errors"}


@dataclasses.dataclass
class ConnectorTestResult:
    name: str
    connector_id: int | None = None
    credential_id: int | None = None
    cc_pair_id: int | None = None
    final_status: str | None = None
    new_docs_indexed: int = 0
    total_docs_indexed: int = 0
    docs_removed_from_index: int = 0
    error_msg: str | None = None
    error_count: int = 0
    elapsed_seconds: float = 0.0
    failure_reason: str | None = None

    @property
    def passed(self) -> bool:
        return self.failure_reason is None and self.final_status == "success"


class OnyxClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()

    def login(self, email: str, password: str) -> None:
        response = self.session.post(
            f"{self.base_url}/api/auth/login",
            data={"username": email, "password": password},
        )
        response.raise_for_status()

    def use_api_key(self, api_key: str) -> None:
        self.session.headers["Authorization"] = f"Bearer {api_key}"

    def create_connector(
        self, name: str, connector_specific_config: dict[str, Any]
    ) -> int:
        response = self.session.post(
            f"{self.base_url}/api/manage/admin/connector",
            json={
                "name": name,
                "source": "web",
                "input_type": "load_state",
                "connector_specific_config": connector_specific_config,
                "access_type": "public",
                "groups": [],
            },
        )
        response.raise_for_status()
        return response.json()["id"]

    def create_credential(self, name: str) -> int:
        response = self.session.post(
            f"{self.base_url}/api/manage/credential",
            json={
                "name": name,
                "source": "web",
                "credential_json": {},
                "admin_public": True,
                "groups": [],
            },
        )
        response.raise_for_status()
        return response.json()["id"]

    def create_cc_pair(self, connector_id: int, credential_id: int, name: str) -> int:
        response = self.session.put(
            f"{self.base_url}/api/manage/connector/{connector_id}/credential/{credential_id}",
            json={"name": name, "access_type": "public", "groups": []},
        )
        response.raise_for_status()
        return response.json()["data"]

    def get_connector(self, connector_id: int) -> dict[str, Any] | None:
        response = self.session.get(
            f"{self.base_url}/api/manage/connector/{connector_id}"
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()

    def get_cc_pairs_for_connector(self, connector_id: int) -> list[dict[str, Any]]:
        response = self.session.get(
            f"{self.base_url}/api/manage/admin/connector/status"
        )
        response.raise_for_status()
        return [
            item for item in response.json() if item["connector"]["id"] == connector_id
        ]

    def trigger_run_once(self, connector_id: int, from_beginning: bool = False) -> None:
        response = self.session.post(
            f"{self.base_url}/api/manage/admin/connector/run-once",
            json={
                "connector_id": connector_id,
                "credential_ids": None,
                "from_beginning": from_beginning,
            },
        )
        response.raise_for_status()

    def get_latest_index_attempt(self, cc_pair_id: int) -> dict[str, Any] | None:
        response = self.session.get(
            f"{self.base_url}/api/manage/admin/cc-pair/{cc_pair_id}/index-attempts",
            params={"page_num": 0, "page_size": 1},
        )
        response.raise_for_status()
        items = response.json()["items"]
        return items[0] if items else None

    def get_cc_pair(self, cc_pair_id: int) -> dict[str, Any] | None:
        response = self.session.get(
            f"{self.base_url}/api/manage/admin/cc-pair/{cc_pair_id}"
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()

    def request_deletion(self, connector_id: int, credential_id: int) -> None:
        response = self.session.post(
            f"{self.base_url}/api/manage/admin/deletion-attempt",
            json={"connector_id": connector_id, "credential_id": credential_id},
        )
        response.raise_for_status()


def poll_cc_pair_for_new_attempt(
    client: OnyxClient,
    result: ConnectorTestResult,
    baseline_attempt_id: int | None,
    poll_timeout_seconds: float,
) -> None:
    start_time = time.monotonic()
    while True:
        elapsed = time.monotonic() - start_time
        if elapsed > poll_timeout_seconds:
            result.failure_reason = (
                f"Timed out after {poll_timeout_seconds:.0f}s waiting for indexing "
                "to reach a terminal state"
            )
            result.elapsed_seconds = elapsed
            return

        attempt = client.get_latest_index_attempt(result.cc_pair_id)
        if attempt is not None and attempt["id"] != baseline_attempt_id:
            status = attempt["status"]
            result.final_status = status
            result.new_docs_indexed = attempt["new_docs_indexed"]
            result.total_docs_indexed = attempt["total_docs_indexed"]
            result.docs_removed_from_index = attempt["docs_removed_from_index"]
            result.error_msg = attempt["error_msg"]
            result.error_count = attempt["error_count"]

            if status in TERMINAL_STATUSES:
                result.elapsed_seconds = time.monotonic() - start_time
                if status != "success":
                    result.failure_reason = f"Indexing ended with status={status}"
                return

        time.sleep(3)


def run_new_connector_test_case(
    client: OnyxClient, test_case: WebConnectorTestCase, poll_timeout_seconds: float
) -> ConnectorTestResult:
    run_name = f"{test_case.name}-{int(time.time())}"
    result = ConnectorTestResult(name=run_name)
    start_time = time.monotonic()

    try:
        result.connector_id = client.create_connector(
            name=run_name,
            connector_specific_config={
                "base_url": test_case.base_url,
                "web_connector_type": test_case.web_connector_type,
            },
        )
        result.credential_id = client.create_credential(name=f"{run_name}-credential")
        result.cc_pair_id = client.create_cc_pair(
            connector_id=result.connector_id,
            credential_id=result.credential_id,
            name=f"{run_name}-cc-pair",
        )
    except requests.HTTPError as e:
        result.failure_reason = f"Setup failed: {e}"
        result.elapsed_seconds = time.monotonic() - start_time
        return result

    # A newly created cc-pair has no prior attempts, so any attempt that shows
    # up is the one triggered by cc-pair creation.
    poll_cc_pair_for_new_attempt(
        client,
        result,
        baseline_attempt_id=None,
        poll_timeout_seconds=poll_timeout_seconds,
    )
    return result


def run_existing_connector_test_case(
    client: OnyxClient, connector_id: int, poll_timeout_seconds: float
) -> list[ConnectorTestResult]:
    connector = client.get_connector(connector_id)
    if connector is None:
        result = ConnectorTestResult(name=f"connector-{connector_id}")
        result.failure_reason = f"Connector {connector_id} does not exist"
        return [result]

    cc_pairs = client.get_cc_pairs_for_connector(connector_id)
    if not cc_pairs:
        result = ConnectorTestResult(name=connector["name"], connector_id=connector_id)
        result.failure_reason = (
            f"Connector {connector_id} has no associated credentials/cc-pairs"
        )
        return [result]

    results = []
    for cc_pair in cc_pairs:
        result = ConnectorTestResult(
            name=connector["name"],
            connector_id=connector_id,
            credential_id=cc_pair["credential"]["id"],
            cc_pair_id=cc_pair["cc_pair_id"],
        )
        baseline_attempt = client.get_latest_index_attempt(result.cc_pair_id)
        baseline_attempt_id = baseline_attempt["id"] if baseline_attempt else None

        try:
            client.trigger_run_once(connector_id)
        except requests.HTTPError as e:
            result.failure_reason = f"Failed to trigger run-once: {e}"
            results.append(result)
            continue

        poll_cc_pair_for_new_attempt(
            client, result, baseline_attempt_id, poll_timeout_seconds
        )
        results.append(result)

    return results


def print_report(results: list[ConnectorTestResult]) -> None:
    print("\n" + "=" * 80)
    print("WEB CONNECTOR TEST REPORT")
    print("=" * 80)

    for result in results:
        outcome = "PASS" if result.passed else "FAIL"
        print(f"\n[{outcome}] {result.name}")
        print(f"  connector_id: {result.connector_id}  cc_pair_id: {result.cc_pair_id}")
        print(f"  final_status: {result.final_status}")
        print(
            f"  docs: new={result.new_docs_indexed} "
            f"total={result.total_docs_indexed} "
            f"removed={result.docs_removed_from_index}"
        )
        print(f"  errors: count={result.error_count} msg={result.error_msg}")
        print(f"  elapsed: {result.elapsed_seconds:.1f}s")
        if result.failure_reason:
            print(f"  failure_reason: {result.failure_reason}")

    passed_count = sum(1 for r in results if r.passed)
    print("\n" + "-" * 80)
    print(f"SUMMARY: {passed_count}/{len(results)} connectors passed")
    print("=" * 80 + "\n")


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--base-url",
        default=os.environ.get("ONYX_BASE_URL", "http://localhost:3000"),
        help="Base URL of the deployed Onyx web server (default: %(default)s)",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("ONYX_API_KEY"),
        help="Onyx API key for Bearer auth. Required for deployments using SSO "
        "(e.g. EntraID) where email/password login is unavailable.",
    )
    parser.add_argument(
        "--email", default=os.environ.get("ONYX_EMAIL", "a@example.com")
    )
    parser.add_argument("--password", default=os.environ.get("ONYX_PASSWORD", "a"))


def build_client(args: argparse.Namespace) -> OnyxClient:
    client = OnyxClient(args.base_url)
    if args.api_key:
        client.use_api_key(args.api_key)
    else:
        client.login(args.email, args.password)
    return client


def cmd_run(args: argparse.Namespace) -> int:
    client = build_client(args)

    results: list[ConnectorTestResult] = []
    if args.connector_id is not None:
        print(f"Triggering existing connector {args.connector_id}")
        results.extend(
            run_existing_connector_test_case(
                client, args.connector_id, args.poll_timeout
            )
        )
    else:
        for test_case in CONNECTORS_TO_TEST:
            print(f"Running test case: {test_case.name} ({test_case.base_url})")
            results.append(
                run_new_connector_test_case(client, test_case, args.poll_timeout)
            )

    print_report(results)
    return 0 if all(r.passed for r in results) else 1


def cmd_delete(args: argparse.Namespace) -> int:
    client = build_client(args)

    connector = client.get_connector(args.connector_id)
    if connector is None:
        print(f"Connector {args.connector_id} does not exist (already deleted?)")
        return 1

    print(
        f"About to request deletion of connector_id={args.connector_id} "
        f"credential_id={args.credential_id} name={connector['name']!r} "
        f"source={connector['source']!r}"
    )
    if not args.yes:
        print("Refusing to delete without --yes. Re-run with --yes to confirm.")
        return 1

    client.request_deletion(args.connector_id, args.credential_id)

    start_time = time.monotonic()
    while True:
        if time.monotonic() - start_time > args.timeout:
            print(f"Timed out after {args.timeout:.0f}s waiting for deletion")
            return 1

        connector = client.get_connector(args.connector_id)
        if connector is None:
            print("Deleted.")
            return 0

        time.sleep(3)


ENV_VARS = [
    ("ONYX_BASE_URL", "Base URL of the deployed Onyx web server", False),
    (
        "ONYX_API_KEY",
        "API key for Bearer auth (needed for SSO/EntraID deployments)",
        True,
    ),
    ("ONYX_EMAIL", "Email for password login (ignored if ONYX_API_KEY is set)", False),
    (
        "ONYX_PASSWORD",
        "Password for password login (ignored if ONYX_API_KEY is set)",
        True,
    ),
]


def mask_secret(value: str) -> str:
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}...{value[-4:]}"


def cmd_env(_: argparse.Namespace) -> int:
    print("Environment variables recognized by this script:\n")
    for name, description, is_secret in ENV_VARS:
        value = os.environ.get(name)
        if value is None:
            status = "(not set)"
        elif is_secret:
            status = f"set ({mask_secret(value)})"
        else:
            status = f"set ({value})"
        print(f"  {name:<16} {status}")
        print(f"    {description}")
    print(
        "\nEach can also be passed as a CLI flag instead (e.g. --base-url), "
        "which takes precedence over the env var."
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    env_parser = subparsers.add_parser(
        "env",
        help="Show which environment variables this script reads and their current values",
    )
    env_parser.set_defaults(func=cmd_env)

    run_parser = subparsers.add_parser(
        "run", help="Create/trigger a connector and follow indexing to completion"
    )
    add_common_args(run_parser)
    run_parser.add_argument(
        "--connector-id",
        type=int,
        default=None,
        help="Trigger re-indexing of this existing connector instead of "
        "creating new ones from CONNECTORS_TO_TEST. Never deletes it.",
    )
    run_parser.add_argument(
        "--poll-timeout",
        type=float,
        default=300.0,
        help="Max seconds to wait per connector for indexing to finish (default: %(default)s)",
    )
    run_parser.set_defaults(func=cmd_run)

    delete_parser = subparsers.add_parser(
        "delete",
        help="Explicitly delete one connector by id (never run automatically by `run`)",
    )
    add_common_args(delete_parser)
    delete_parser.add_argument("--connector-id", type=int, required=True)
    delete_parser.add_argument("--credential-id", type=int, required=True)
    delete_parser.add_argument(
        "--yes", action="store_true", help="Confirm the deletion (required)"
    )
    delete_parser.add_argument(
        "--timeout",
        type=float,
        default=120.0,
        help="Max seconds to wait for deletion to finish (default: %(default)s)",
    )
    delete_parser.set_defaults(func=cmd_delete)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
