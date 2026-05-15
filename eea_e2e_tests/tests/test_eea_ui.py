import json
import re
import pytest
from playwright.sync_api import expect, Page
from page_objects.eea_page import EeaPage

@pytest.mark.branding
def test_branding_logo_on_login(page: Page, settings, eea_page: EeaPage):
    """Verify EEA logo and AI Hub text on the login page."""
    # We need a fresh context for login page to avoid being auto-redirected
    page.goto("/auth/login")
    
    # Verify Logo
    expect(eea_page.logo.first).to_be_visible()
    
    # Verify AI Hub text
    expect(page.locator(eea_page.selectors.AI_HUB_TEXT).first).to_be_visible()

@pytest.mark.branding
def test_branding_logo_in_sidebar(page: Page, eea_page: EeaPage):
    """Verify EEA logo, AI Hub text, and Powered by Onyx in the sidebar."""
    page.goto("/chat") # Redirects to /chat usually
    
    # Sidebar logo
    expect(eea_page.logo.first).to_be_visible()
    
    # AI Hub and Powered by Onyx
    expect(page.locator(eea_page.selectors.AI_HUB_TEXT).first).to_be_visible()
    expect(page.locator(eea_page.selectors.POWERED_BY_ONYX).first).to_be_visible()

@pytest.mark.user_menu
def test_user_menu_custom_page_links(page: Page, eea_page: EeaPage):
    """Verify custom page links are present in the user menu."""
    page.goto("/chat")
    
    eea_page.open_user_menu()
    
    # Verify links
    expect(eea_page.get_menu_link("/pages/disclaimer")).to_be_visible()
    expect(eea_page.get_menu_link("/pages/privacy")).to_be_visible()
    expect(eea_page.get_menu_link("/pages/privacy-statement")).to_be_visible()
    expect(eea_page.get_menu_link("/pages/whats-new")).to_be_visible()

@pytest.mark.user_menu
def test_user_menu_navigation_to_pages(page: Page, eea_page: EeaPage, eea_config_available, settings):
    """Verify clicking a custom page link navigates to the pages subdirectory."""
    if not eea_config_available:
        pytest.skip("EEA config API not available")
        
    page.goto("/chat")
    eea_page.open_user_menu()
    
    # Click Disclaimer
    link = eea_page.get_menu_link("/pages/disclaimer")
    link.wait_for(state="visible")
    link.click()
    
    # Wait for navigation
    page.wait_for_url("**/pages/disclaimer", timeout=15000)
    
    # Assert URL
    assert "/pages/disclaimer" in page.url
    
    # Assert 'Back to AI Hub' button
    expect(page.locator(eea_page.selectors.BACK_TO_AI_HUB)).to_be_visible()

@pytest.mark.accessibility
def test_custom_pages_accessibility(page: Page):
    """Verify that static custom pages are accessible and not redirected."""
    static_pages = ["disclaimer", "privacy", "privacy-statement", "whats-new"]
            
    # Test each page
    for page_title in static_pages:
        target_url = f"/pages/{page_title}"
        print(f"Checking accessibility of {target_url}")
        
        page.goto(target_url)
        
        # We wait a bit to allow any redirection to happen
        page.wait_for_timeout(2000)
        
        # Verify URL - it should NOT be redirected to /chat or /app
        current_url = page.url
        assert target_url in current_url, f"Page {target_url} was redirected to {current_url}"

@pytest.mark.admin
def test_admin_customize_layout_pages(page: Page, eea_page: EeaPage, eea_config_available):
    """Verify navigation to Admin -> Customize Layout -> Pages."""
    if not eea_config_available:
        pytest.skip("EEA config API not available")
        
    page.goto("/admin/indexing/status") # Standard admin entry
    
    # Verify Sidebar section
    expect(page.locator(eea_page.selectors.ADMIN_SIDEBAR_CUSTOMIZE_LAYOUT)).to_be_visible()
    
    # Click Pages
    page.locator(eea_page.selectors.ADMIN_SIDEBAR_PAGES).click()
    
    # Verify we are on the pages list
    expect(page.get_by_label("admin-page-title")).to_contain_text("Pages")
    expect(page.locator(eea_page.selectors.ADMIN_NEW_PAGE_BTN)).to_be_visible()
