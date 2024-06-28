from typing import cast

from fastapi import FastAPI
from fastapi.dependencies.models import Dependant
from starlette.routing import BaseRoute

from danswer.auth.users import current_admin_user
from danswer.auth.users import current_user
from danswer.configs.app_configs import APP_API_PREFIX
from danswer.server.danswer_api.ingestion import api_key_dep


PUBLIC_ENDPOINT_SPECS = [
    # built-in documentation functions
    ("/openapi.json", {"GET", "HEAD"}),
    ("/docs", {"GET", "HEAD"}),
    ("/docs/oauth2-redirect", {"GET", "HEAD"}),
    ("/redoc", {"GET", "HEAD"}),
    # should always be callable, will just return 401 if not authenticated
    ("/me", {"GET"}),
    # just returns 200 to validate that the server is up
    ("/health", {"GET"}),
    # just returns auth type, needs to be accessible before the user is logged
    # in to determine what flow to give the user
    ("/auth/type", {"GET"}),
    # just gets the version of Danswer (e.g. 0.3.11)
    ("/version", {"GET"}),
    # stuff related to basic auth
    ("/auth/register", {"POST"}),
    ("/auth/login", {"POST"}),
    ("/auth/logout", {"POST"}),
    ("/auth/forgot-password", {"POST"}),
    ("/auth/reset-password", {"POST"}),
    ("/auth/request-verify-token", {"POST"}),
    ("/auth/verify", {"POST"}),
    ("/users/me", {"GET"}),
    ("/users/me", {"PATCH"}),
    ("/users/{id}", {"GET"}),
    ("/users/{id}", {"PATCH"}),
    ("/users/{id}", {"DELETE"}),
    # oauth
    ("/auth/oauth/authorize", {"GET"}),
    ("/auth/oauth/callback", {"GET"}),
    ("/eea_config/get_eea_config", {"GET"}),
    ("/llm_guard/anonymize", {"GET"}),
    ("/llm_guard/deanonymize", {"GET"}),
]


def is_route_in_spec_list(
    route: BaseRoute, public_endpoint_specs: list[tuple[str, set[str]]]
) -> bool:
    if not hasattr(route, "path") or not hasattr(route, "methods"):
        return False

    # try adding the prefix AND not adding the prefix, since some endpoints
    # are not prefixed (e.g. /openapi.json)
    if (route.path, route.methods) in public_endpoint_specs:
        return True

    processed_global_prefix = f"/{APP_API_PREFIX.strip('/')}" if APP_API_PREFIX else ""
    if not processed_global_prefix:
        return False

    for endpoint_spec in public_endpoint_specs:
        base_path, methods = endpoint_spec
        prefixed_path = f"{processed_global_prefix}/{base_path.strip('/')}"

        if prefixed_path == route.path and route.methods == methods:
            return True

    return False


def check_router_auth(
    application: FastAPI,
    public_endpoint_specs: list[tuple[str, set[str]]] = PUBLIC_ENDPOINT_SPECS,
) -> None:
    """Ensures that all endpoints on the passed in application either
    (1) have auth enabled OR
    (2) are explicitly marked as a public endpoint
    """
    for route in application.routes:
        # explicitly marked as public
        if is_route_in_spec_list(route, public_endpoint_specs):
            continue

        # check for auth
        found_auth = False
        route_dependant_obj = cast(
            Dependant | None, route.dependant if hasattr(route, "dependant") else None
        )
        if route_dependant_obj:
            for dependency in route_dependant_obj.dependencies:
                depends_fn = dependency.cache_key[0]
                if (
                    depends_fn == current_user
                    or depends_fn == current_admin_user
                    or depends_fn == api_key_dep
                ):
                    found_auth = True
                    break

        if not found_auth:
            # uncomment to print out all route(s) that are missing auth
            # print(f"(\"{route.path}\", {set(route.methods)}),")

            raise RuntimeError(
                f"Did not find current_user or current_admin_user dependency in route - {route}"
            )
