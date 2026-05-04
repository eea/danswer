import { test, expect } from "@playwright/test";
import { loginAsAdmin } from "../utils/auth"; // Assumed existing utility for admin login

test.describe("EEA UI Customizations", () => {
  test("Rebranding on login page", async ({ page }) => {
    // Navigate to login page
    await page.goto("/auth/login");

    // Wait for the page to load
    await page.waitForLoadState("networkidle");

    // Check for EEA branding text (either in title or directly on page)
    const pageTitle = await page.title();
    // Rebranding often sets document title or specific headings
    expect(pageTitle.includes("EEA AI Hub") || await page.locator("text=EEA AI Hub").isVisible()).toBeTruthy();

    // Check for the custom SVG logo by looking for an SVG or image with EEA specific class or alt
    const logoLocator = page.locator("svg").first();
    await expect(logoLocator).toBeVisible();
  });

  test("Disclaimer Modal behavior", async ({ page }) => {
    // Navigate to home to trigger the disclaimer for a fresh state (no localStorage)
    await page.goto("/");

    const disclaimerModal = page.locator("text=Disclaimer");
    
    // Check if the modal exists in the DOM.
    if (await disclaimerModal.isVisible()) {
      // Click 'I Agree' or equivalent accept button
      const agreeButton = page.locator("button:has-text('I Agree'), button:has-text('Accept')");
      await agreeButton.click();

      // Ensure modal disappears
      await expect(disclaimerModal).not.toBeVisible();

      // Refresh the page
      await page.reload();
      await page.waitForLoadState("networkidle");

      // Assert the modal does not reappear after refresh
      await expect(disclaimerModal).not.toBeVisible();
    }
  });

  test("Custom Pages: Creation and Navigation", async ({ page, browser }) => {
    // Log in as admin and create a custom page
    await loginAsAdmin(page);
    await page.goto("/admin/eea_config/pages");
    
    // Check if we are on the custom pages admin dashboard
    await expect(page.locator("text=Custom Pages")).toBeVisible();

    // Navigate to create page form
    const createButton = page.locator("button:has-text('Create New Page'), a:has-text('Create')");
    if (await createButton.isVisible()) {
        await createButton.click();

        // Fill out custom page form
        await page.fill("input[name='title'], input[placeholder='Page Title']", "E2E Test Page");
        await page.fill("textarea[name='content']", "This is a custom test page for Playwright.");
        
        // Submit
        await page.locator("button:has-text('Save'), button:has-text('Submit')").click();

        // Check if saved successfully
        await expect(page.locator("text=E2E Test Page")).toBeVisible();

        // Verify the custom page is available in the user dropdown
        const userDropdown = page.locator("[aria-label='User Menu'], button[id='user-menu']");
        if (await userDropdown.isVisible()) {
            await userDropdown.click();
            const customPageLink = page.locator("a:has-text('E2E Test Page')");
            await expect(customPageLink).toBeVisible();
            await customPageLink.click();
            
            // Check that the page rendered correctly
            await expect(page.locator("text=This is a custom test page for Playwright.")).toBeVisible();
        }
    }
  });
});
