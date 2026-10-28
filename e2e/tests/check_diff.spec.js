const { test, expect } = require('@playwright/test');

// Lưu sẵn 1 API key và chọn nó (ô nhập key đã được thay bằng dropdown đọc từ localStorage)
async function selectTestApiKey(page) {
  await page.evaluate(() => {
    localStorage.setItem('redmine_log_time.apiKeys', JSON.stringify({
      activeId: 'k_test',
      items: [{ id: 'k_test', name: 'Test key', key: 'test-api-key' }]
    }));
  });
  await page.reload();
}

test.describe('Check Diff Feature', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('check diff button is visible and enabled when API key is entered', async ({ page }) => {
    const apiKeySelect = page.locator('#btn-api-key-select');
    const checkDiffBtn = page.locator('#btn-check-diff');

    await expect(apiKeySelect).toBeVisible();
    await expect(checkDiffBtn).toBeVisible();
    await expect(checkDiffBtn).toBeDisabled();

    await selectTestApiKey(page);
    await expect(checkDiffBtn).toBeEnabled();
  });

  test('shows error when clicking check diff without API key', async ({ page }) => {
    const checkDiffBtn = page.locator('#btn-check-diff');

    await checkDiffBtn.click();

    const toast = page.locator('.toast-warning, [class*="toast"]').first();
    await expect(toast).toBeVisible();
  });

  test('check diff overlay appears while checking', async ({ page }) => {
    const checkDiffBtn = page.locator('#btn-check-diff');

    await selectTestApiKey(page);

    const checkDiffOverlay = page.locator('#check-diff-overlay, .overlay');
    await checkDiffBtn.click();

    await expect(checkDiffOverlay).toBeVisible();
  });

  test('collectCheckData sends only from_date and to_date', async ({ page }) => {
    const checkDiffBtn = page.locator('#btn-check-diff');

    await selectTestApiKey(page);

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

    await selectTestApiKey(page);

    const checkDiffBtn = page.locator('#btn-check-diff');
    await checkDiffBtn.click();

    await page.waitForTimeout(1000);
  });
});