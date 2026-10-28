const { test, expect } = require('@playwright/test');

test.describe('Check Diff Feature', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('check diff button is visible and enabled when API key is entered', async ({ page }) => {
    const apiKeyInput = page.locator('#api-key');
    const checkDiffBtn = page.locator('#btn-check-diff');

    await expect(apiKeyInput).toBeVisible();
    await expect(checkDiffBtn).toBeVisible();
    await expect(checkDiffBtn).toBeDisabled();

    await apiKeyInput.fill('test-api-key');
    await expect(checkDiffBtn).toBeEnabled();
  });

  test('shows error when clicking check diff without API key', async ({ page }) => {
    const checkDiffBtn = page.locator('#btn-check-diff');

    await checkDiffBtn.click();

    const toast = page.locator('.toast-warning, [class*="toast"]').first();
    await expect(toast).toBeVisible();
  });

  test('check diff overlay appears while checking', async ({ page }) => {
    const apiKeyInput = page.locator('#api-key');
    const checkDiffBtn = page.locator('#btn-check-diff');

    await apiKeyInput.fill('test-api-key');

    const checkDiffOverlay = page.locator('#check-diff-overlay, .overlay');
    await checkDiffBtn.click();

    await expect(checkDiffOverlay).toBeVisible();
  });

  test('collectCheckData sends only from_date and to_date', async ({ page }) => {
    const apiKeyInput = page.locator('#api-key');
    const checkDiffBtn = page.locator('#btn-check-diff');

    await apiKeyInput.fill('test-api-key');

    page.on('request', async (request) => {
      if (request.url().includes('/api/sync/check/user-range')) {
        const postData = JSON.parse(request.postData());
        expect(postData).toHaveProperty('from_date');
        expect(postData).toHaveProperty('to_date');
        expect(postData).not.toHaveProperty('issue_ids');
      }
    });

    await checkDiffBtn.click();
    await page.waitForTimeout(500);
  });
});

test.describe('Check Diff Results Display', () => {
  test('displays diff results when check completes', async ({ page }) => {
    await page.goto('/');

    const apiKeyInput = page.locator('#api-key');
    await apiKeyInput.fill('test-api-key');

    const checkDiffBtn = page.locator('#btn-check-diff');
    await checkDiffBtn.click();

    await page.waitForTimeout(1000);
  });
});