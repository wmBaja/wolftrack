import { test, expect } from '@playwright/test';

test('shows the dashboard navigation controls', async ({ page }) => {
  await page.goto('/');

  await expect(page.getByRole('navigation')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Toggle File Manager' })).toBeVisible();
  await expect(page.getByRole('textbox', { name: 'Log filename template' })).toBeVisible();
});

test('compares Dockview dashboards and Gridview tiles in the workspace spike', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('dashboard-widgets', JSON.stringify([{
      i: 'spike-chart', type: 'chart', title: 'Spike chart',
      x: 0, y: 0, w: 8, h: 12, minW: 2, minH: 2,
      config: {}, signals: ['fixture-signal'], createdAt: 1,
    }]));
  });
  await page.goto('/#/workspace-spike?candidate=dockview');

  await expect(page.getByRole('heading', { name: 'Workspace spike' })).toBeVisible();
  await expect(page.getByText('Dashboard A', { exact: true })).toBeVisible();
  await expect(page.getByText('Dashboard B', { exact: true })).toBeVisible();
  await expect(page.locator('.uplot').first()).toBeVisible();

  await page.getByRole('link', { name: 'Gridview tiles' }).click();
  await expect(page.getByText('Tile A')).toBeVisible();
  await expect(page.getByText('Tile B')).toBeVisible();
  await expect(page.getByText('Tile C')).toBeVisible();
});

test('renders registered features and preserves an unavailable saved widget', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('dashboard-widgets', JSON.stringify([{
      i: 'saved-plugin-widget', type: 'sample-plugin/plot', title: 'Saved plugin plot',
      x: 0, y: 0, w: 4, h: 4, minW: 2, minH: 2, config: {}, signals: [], createdAt: 1,
    }]));
  });
  await page.goto('/');

  await expect(page.getByText('Widget unavailable')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Toggle File Manager' })).toBeVisible();
  await page.getByRole('button', { name: 'Toggle File Manager' }).click();
  await expect(page.getByRole('heading', { name: 'File Manager' })).toBeVisible();

  await page.locator('#datasource-config-btn').click();
  await expect(page.getByRole('dialog', { name: 'Data Source Configuration' })).toBeVisible();
  await page.reload();
  await page.locator('#export-panel-btn').click();
  await expect(page.getByRole('dialog', { name: 'BLF CSV Export' })).toBeVisible();
  await page.reload();
  await page.locator('.dashboard-grid-container').click({ button: 'right', position: { x: 900, y: 500 } });
  await page.getByText('Add Chart Widget').click();
  await expect(page.getByText('No signals configured.')).toBeVisible();
});
