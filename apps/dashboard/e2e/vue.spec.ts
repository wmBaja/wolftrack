import { test, expect } from '@playwright/test';

test('shows the dashboard navigation controls', async ({ page }) => {
  await page.goto('/');

  await expect(page.getByRole('navigation')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Toggle File Manager' })).toBeVisible();
  await expect(page.getByRole('textbox', { name: 'Log filename template' })).toBeVisible();
});
