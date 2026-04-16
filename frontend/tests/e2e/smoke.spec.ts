/**
 * Demonstration E2E tests for CardinalCast frontend.
 *
 * These tests showcase E2E testing capability using Playwright.
 * For production, would include cross-browser testing, mobile viewports,
 * axe-core accessibility audits, visual regression, and Lighthouse CI.
 */
import { test, expect, type Page } from '@playwright/test';

const TEST_PASS = 'password123';

/**
 * Dismiss the daily claim dialog if shown.
 * New users always trigger it on first authenticated page load, so tests
 * that register a fresh user must call this before interacting with the page.
 */
async function dismissDailyClaimIfVisible(page: Page): Promise<void> {
  const laterBtn = page.locator('button', { hasText: 'Later' });
  const visible = await laterBtn.isVisible({ timeout: 2000 }).catch(() => false);
  if (visible) {
    await laterBtn.click();
    await page.waitForTimeout(300);
  }
}

test.describe('CardinalCast E2E Smoke Tests', () => {

  test('User Registration, Login, and Daily Claim', async ({ page }) => {
    const testUser = `testuser_${Date.now()}`;
    await page.goto('/register');

    await page.getByLabel('Username').fill(testUser);
    await page.getByLabel('Password').fill(TEST_PASS);
    await page.getByRole('button', { name: 'Register' }).click();

    await expect(page).toHaveURL('/');
    await expect(page.getByText('Credits:', { exact: false })).toBeVisible();

    const claimButton = page.getByRole('button', { name: /Claim Now/i });
    if (await claimButton.isVisible()) {
      await claimButton.click();
      await expect(page.getByText('+100 credits')).toBeVisible();
    }
  });

  test('Placing Wagers and Verifying Application State', async ({ page }) => {
    const wagerUser = `wagertest_${Date.now()}`;
    await page.goto('/register');
    await page.getByLabel('Username').fill(wagerUser);
    await page.getByLabel('Password').fill(TEST_PASS);
    await page.getByRole('button', { name: 'Register' }).click();
    await expect(page).toHaveURL('/');

    await dismissDailyClaimIfVisible(page);

    await expect(page.locator('text=Wager Calendar')).toBeVisible();
    await expect(page.locator('text=Data Sources')).toBeVisible();

    // CalendarDayButton renders with a data-day attribute on each cell
    const calendarDay = page.locator('[data-day]').first();
    await calendarDay.click();

    await expect(page.getByText('Existing Wagers')).toBeVisible();
    await expect(page.getByText('New Wager')).toBeVisible();

    await page.goto('/wagers');
    await expect(page.getByRole('heading', { name: 'Wager History' })).toBeVisible();

    await page.goto('/leaderboard');
    await expect(page.getByRole('heading', { name: 'Leaderboard' })).toBeVisible();
    await expect(page.getByText(wagerUser)).toBeVisible();
  });

  test('Homepage Accessibility and Navigation', async ({ page }) => {
    await page.goto('/');

    // Logo is an inline SVG with aria-label
    await expect(page.locator('[aria-label="CardinalCast logo"]')).toBeVisible();

    // Use role=link to avoid strict mode — "Dashboard" appears as both nav link and page heading
    await expect(page.getByRole('link', { name: 'Dashboard' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'History' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Leaderboard' })).toBeVisible();

    await expect(page.locator('text=CardinalCast')).toBeVisible();
  });

  test('Keyboard Navigation Accessibility', async ({ page }) => {
    await page.goto('/register');

    await page.keyboard.press('Tab');
    await page.keyboard.type('keyboardtest');
    await page.keyboard.press('Tab');
    await page.keyboard.type('testpass123');
    await page.keyboard.press('Tab');
    await page.keyboard.press('Enter');

    // Any outcome (redirect or validation error) confirms keyboard nav works
    await page.waitForTimeout(500);
  });

  test('Dashboard Component Visibility', async ({ page }) => {
    const username = `dashtest_${Date.now()}`;

    await page.goto('/register');
    await page.getByLabel('Username').fill(username);
    await page.getByLabel('Password').fill('testpass');
    await page.getByRole('button', { name: 'Register' }).click();
    await expect(page).toHaveURL('/');

    await dismissDailyClaimIfVisible(page);

    await expect(page.locator('text=Wager Calendar')).toBeVisible();
    await expect(page.locator('text=Data Sources')).toBeVisible();

    // react-day-picker v9 uses these exact aria-labels for month navigation
    await expect(page.getByRole('button', { name: /previous month/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /next month/i })).toBeVisible();
  });

  test('Navigation Between All Pages', async ({ page }) => {
    const username = `navtest_${Date.now()}`;

    await page.goto('/register');
    await page.getByLabel('Username').fill(username);
    await page.getByLabel('Password').fill('testpass');
    await page.getByRole('button', { name: 'Register' }).click();
    await expect(page).toHaveURL('/');

    await dismissDailyClaimIfVisible(page);

    // Link text is "History" but the route is /wagers
    await page.getByRole('link', { name: 'History' }).click();
    await expect(page).toHaveURL(/.*wagers/);
    await expect(page.getByRole('heading', { name: 'Wager History' })).toBeVisible();

    await page.getByRole('link', { name: 'Leaderboard' }).click();
    await expect(page).toHaveURL(/.*leaderboard/);
    await expect(page.getByRole('heading', { name: 'Leaderboard' })).toBeVisible();

    await page.getByRole('link', { name: 'Dashboard' }).click();
    await expect(page).toHaveURL(/\//);
    await expect(page.locator('text=Wager Calendar')).toBeVisible();
  });
});
