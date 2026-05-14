from playwright.sync_api import Page, Locator, expect

class EeaPageSelectors:
    """Selectors for EEA-specific UI elements."""
    
    # Branding
    LOGO = 'img[alt="Logo"]'
    AI_HUB_TEXT = 'text=AI Hub'
    POWERED_BY_ONYX = 'text=Powered by Onyx'
    
    # User Menu
    USER_DROPDOWN_TRIGGER = '#onyx-user-dropdown'
    MENU_DISCLAIMER = 'a[href="/pages/disclaimer"]'
    MENU_PRIVACY_ARCH = 'a[href="/pages/privacy"]'
    MENU_PRIVACY_STMT = 'a[href="/pages/privacy-statement"]'
    MENU_WHATS_NEW = 'a[href="/pages/whats-new"]'
    
    # Pages
    BACK_TO_AI_HUB = 'text=Back to AI Hub'
    
    # Admin
    ADMIN_SIDEBAR_CUSTOMIZE_LAYOUT = 'text=Customize Layout'
    ADMIN_SIDEBAR_PAGES = 'a[href="/admin/eea_config/pages"]'
    ADMIN_PAGES_HEADER = 'text=User defined pages'
    ADMIN_NEW_PAGE_BTN = 'a:has-text("New Page")'
    
    # Page Editor
    EDITOR_TITLE_INPUT = 'input[name="page_title"]'
    EDITOR_TEXT_AREA = 'textarea[name="page_text"]'
    EDITOR_SUBMIT_BTN = 'button[type="submit"]:has-text("Submit")'
    
    # Toasts
    TOAST_SUCCESS = '.toast-success, text=Page saved successfully'

class EeaPage:
    """Page object for EEA customizations."""
    
    def __init__(self, page: Page):
        self.page = page
        self.selectors = EeaPageSelectors
        
    @property
    def logo(self) -> Locator:
        return self.page.locator(self.selectors.LOGO)
        
    @property
    def user_dropdown(self) -> Locator:
        return self.page.locator(self.selectors.USER_DROPDOWN_TRIGGER)
        
    def open_user_menu(self):
        """Click to open the user dropdown menu."""
        self.user_dropdown.click()
        
    def get_menu_link(self, href: str) -> Locator:
        """Get a menu link by its href."""
        return self.page.locator(f'a[href="{href}"]')
        
    def navigate_to_admin_pages(self):
        """Navigate directly to the admin pages config."""
        self.page.goto("/admin/eea_config/pages")
        
    def click_new_page(self):
        """Click the 'New Page' button."""
        self.page.locator(self.selectors.ADMIN_NEW_PAGE_BTN).click()
        
    def fill_page_form(self, title: str, text: str):
        """Fill out the page editor form."""
        self.page.fill(self.selectors.EDITOR_TITLE_INPUT, title)
        self.page.fill(self.selectors.EDITOR_TEXT_AREA, text)
        
    def submit_page_form(self):
        """Click the submit button in the editor."""
        self.page.locator(self.selectors.EDITOR_SUBMIT_BTN).click()
        
    def delete_page_if_exists(self, title: str):
        """
        Attempt to delete a page by its title if it exists in the table.
        This is a best-effort cleanup.
        """
        # We find the row containing the title and then the delete button in that row
        # Based on pages/page.tsx, it's a TableRow with a DeleteButton component
        row = self.page.locator("tr").filter(has_text=title)
        if row.count() > 0:
            # The DeleteButton has an icon, usually FiTrash or similar
            # Let's try to find a button with a trash icon or standard delete selector
            delete_btn = row.locator('button').filter(has=self.page.locator('svg'))
            if delete_btn.count() > 0:
                delete_btn.first.click()
                # If there's a confirmation dialog, we might need to handle it
                # Assuming simple delete for now
