import re
import os
import json
import pytest
from pathlib import Path
from playwright.sync_api import Page, expect, BrowserContext

from config import get_settings
from page_objects.eea_page import EeaPage

@pytest.fixture(scope="session")
def settings():
    """Get the test settings."""
    return get_settings()

@pytest.fixture(scope="session", autouse=True)
def configure_expect_timeout(settings):
    """Set the global timeout for expect assertions."""
    expect.set_options(timeout=settings.expect_timeout)

@pytest.fixture(scope="session")
def browser_type_launch_args(settings):
    """Configure browser launch based on settings."""
    return {
        "headless": settings.headless,
    }

@pytest.fixture(scope="session")
def storage_state_path(browser, settings):
    """
    Authenticate once via the browser UI and save storage state.
    This implements the 'Login Once' strategy.
    """
    state_path = Path("storageState.json")
    
    # Create a fresh context and page for the initial login
    context = browser.new_context(base_url=settings.base_url)
    page = context.new_page()
    
    try:
        # Navigate to login page
        page.goto("/auth/login")
        
        # Fill credentials
        # These selectors match Onyx/Danswer login form
        page.fill('input[name="email"]', settings.admin_email)
        page.fill('input[name="password"]', settings.admin_password)
        
        # Click login button
        page.click('button[type="submit"]')
        
        # Wait for redirection to the app (handle both /chat and /app)
        page.wait_for_url(re.compile(r".*/(chat|app).*"), timeout=settings.timeout)
        
        # Save storage state (cookies, etc)
        context.storage_state(path=state_path)
        return state_path
    finally:
        context.close()

@pytest.fixture
def context(browser, settings, storage_state_path, request):
    """Create a new browser context for each test, reusing storage state."""
    # Setup tracing and video if requested
    test_name = request.node.name
    video_dir = Path(settings.reports_dir) / "videos" / test_name
    
    ctx = browser.new_context(
        base_url=settings.base_url,
        storage_state=storage_state_path,
        viewport={"width": 1280, "height": 800},
        record_video_dir=video_dir
    )
    
    # Start tracing
    trace_path = Path(settings.reports_dir) / "traces" / f"{test_name}.zip"
    ctx.tracing.start(screenshots=True, snapshots=True, sources=True)
    
    yield ctx
    
    # Stop tracing and save
    ctx.tracing.stop(path=trace_path)
    ctx.close()

@pytest.fixture
def page(context, settings) -> Page:
    """Create a new page in the context."""
    p = context.new_page()
    p.set_default_timeout(settings.timeout)
    return p

@pytest.fixture
def eea_page(page: Page) -> EeaPage:
    """Get an EeaPage page object."""
    return EeaPage(page)

@pytest.fixture(scope="session")
def eea_config_available(playwright, settings):
    """Check if the EEA config backend is available."""
    api_context = playwright.request.new_context(base_url=settings.base_url)
    try:
        response = api_context.get("/api/eea_config/get_eea_config")
        return response.ok
    except:
        return False
    finally:
        api_context.dispose()
