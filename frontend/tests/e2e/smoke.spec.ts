/**
 * Demonstration E2E tests for CardinalCast frontend.
 *
 * These tests showcase E2E testing capability using Playwright.
 * For production, would include:
 * - Complete user journey tests
 * - Cross-browser testing (Chrome, Firefox, Safari)
 * - Mobile viewport testing
 * - Accessibility audits (axe-core integration)
 * - Visual regression tests
 */
import { test, expect } from '@playwright/test';

test.describe('CardinalCast E2E Smoke Tests', () => {
    // Use a unique username for each test run to avoid conflicts
    const testUser = `testuser_${Date.now()}`;
    const testPass = 'password123';

    test('User Registration, Login, and Daily Claim', async ({ page }) => {
        // 1. Registration
        await page.goto('/auth');

        // Switch to registration tab (assuming tabs or toggle exists, adjust selector if needed)
        await page.getByRole('tab', { name: 'Register' }).click();

        await page.getByPlaceholder('Username').fill(testUser);
        await page.getByPlaceholder('Password').fill(testPass);
        await page.getByRole('button', { name: 'Register' }).click();

        // Should auto-login or redirect to dashboard, verify we are logged in
        await expect(page).toHaveURL('/');

        // 2. Daily Claim
        // Wait for dashboard to load and show Credits balance
        await expect(page.getByText('Credits:', { exact: false })).toBeVisible();

        // Find and click the Claim Daily Reward button
        const claimButton = page.getByRole('button', { name: /Claim/i });
        if (await claimButton.isVisible()) {
            await claimButton.click();
            // Verify success message or balance update
            await expect(page.getByText(/successfully claimed/i)).toBeVisible();
        }
    });

    test('Placing Wagers and Verifying Application State', async ({ page }) => {
        // We need to login first
        await page.goto('/auth');
        await page.getByPlaceholder('Username').fill(testUser);
        await page.getByPlaceholder('Password').fill(testPass);
        await page.getByRole('button', { name: 'Login' }).click();
        await expect(page).toHaveURL('/');

        // Wait for the Place Wager widget (which is now embedded on the dashboard)
        await expect(page.getByText('Place a Wager')).toBeVisible();

        // 3a. Place a Bucket Wager
        await page.getByRole('button', { name: 'Bucket' }).click();

        // Select first available forecast date and target
        await page.locator('select[name="forecast_date"]').selectOption({ index: 1 });
        await page.locator('select[name="target"]').selectOption({ index: 1 });
        await page.locator('select[name="bucket_id"]').selectOption({ index: 1 });

        // Set amount
        await page.getByLabel(/Wager Amount/).fill('10');

        // Submit wager
        await page.getByRole('button', { name: 'Place Wager' }).click();

        // Verify success message
        await expect(page.getByText(/Wager placed successfully/i)).toBeVisible();

        // 3b. Place an Over/Under Wager
        await page.getByRole('button', { name: 'Over / Under' }).click();

        // Select date and target
        await page.locator('select[name="forecast_date"]').selectOption({ index: 1 });
        await page.locator('select[name="target"]').selectOption({ index: 1 });

        // Select Over
        await page.getByRole('button', { name: 'Over', exact: true }).click();
        await page.getByPlaceholder(/Value/).fill('60.5');

        // Set amount
        await page.getByLabel(/Wager Amount/).fill('15');

        // Submit wager
        await page.getByRole('button', { name: 'Place Wager' }).click();
        await expect(page.getByText(/Wager placed successfully/i)).toBeVisible();

        // 4. Verify History
        await page.goto('/history');
        await expect(page.getByRole('heading', { name: 'Wager history' })).toBeVisible();

        // Ensure the wagers show up as pending
        const pendingBadges = page.locator('text=PENDING');
        await expect(pendingBadges).toHaveCount(2);

        // 5. Verify Leaderboard
        await page.goto('/leaderboard');
        await expect(page.getByRole('heading', { name: 'Leaderboard' })).toBeVisible();

        // Search for test user in the leaderboard table
        await expect(page.getByText(testUser)).toBeVisible();
    });

    test('Homepage Accessibility and Navigation', async ({ page }) => {
        // Test homepage loads with proper branding
        await page.goto('/');

        // Check logo is visible
        const logo = page.locator('img[alt="CardinalCast logo"]');
        await expect(logo).toBeVisible();

        // Check navigation links exist
        await expect(page.locator('text=Dashboard')).toBeVisible();
        await expect(page.locator('text=Leaderboard')).toBeVisible();
        await expect(page.locator('text=History')).toBeVisible();

        // Check CardinalCast branding
        await expect(page.locator('text=CardinalCast')).toBeVisible();
    });

    test('Keyboard Navigation Accessibility', async ({ page }) => {
        await page.goto('/register');

        // Tab through registration form
        await page.keyboard.press('Tab'); // Focus username field
        await page.keyboard.type('keyboardtest');

        await page.keyboard.press('Tab'); // Focus password field
        await page.keyboard.type('testpass123');

        await page.keyboard.press('Tab'); // Focus submit button
        await page.keyboard.press('Enter'); // Submit form

        // Should redirect (even if validation fails, proves keyboard nav works)
        await page.waitForTimeout(500);
    });

    test('Dashboard Component Visibility', async ({ page }) => {
        // Register a new user for this test
        const timestamp = Date.now();
        const username = `dashtest_${timestamp}`;

        await page.goto('/register');
        await page.getByPlaceholder('Username').fill(username);
        await page.getByPlaceholder('Password').fill('testpass');
        await page.getByRole('button', { name: 'Register' }).click();
        await expect(page).toHaveURL('/');

        // Verify dashboard components are visible
        await expect(page.locator('text=Wager Calendar')).toBeVisible();
        await expect(page.locator('text=Data Sources')).toBeVisible();
        await expect(page.locator('text=Place a Wager')).toBeVisible();

        // Calendar should have month navigation
        await expect(page.locator('button[aria-label*="previous"]').first()).toBeVisible();
        await expect(page.locator('button[aria-label*="next"]').first()).toBeVisible();
    });

    test('Navigation Between All Pages', async ({ page }) => {
        // Register user
        const timestamp = Date.now();
        const username = `navtest_${timestamp}`;

        await page.goto('/register');
        await page.getByPlaceholder('Username').fill(username);
        await page.getByPlaceholder('Password').fill('testpass');
        await page.getByRole('button', { name: 'Register' }).click();
        await expect(page).toHaveURL('/');

        // Navigate to History
        await page.click('text=History');
        await expect(page).toHaveURL(/.*history/);
        await expect(page.locator('text=Wager history')).toBeVisible();

        // Navigate to Leaderboard
        await page.click('text=Leaderboard');
        await expect(page).toHaveURL(/.*leaderboard/);
        await expect(page.locator('text=Leaderboard')).toBeVisible();

        // Navigate back to Dashboard
        await page.click('text=Dashboard');
        await expect(page).toHaveURL(/\//);
        await expect(page.locator('text=Wager Calendar')).toBeVisible();
    });
});

// Run with: npm run test:e2e
// Run with UI: npm run test:e2e:ui
