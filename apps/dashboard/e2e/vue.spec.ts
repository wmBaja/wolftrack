import { test, expect } from '@playwright/test';

test('shows the dashboard navigation controls', async ({ page }) => {
  await page.goto('/');

  await expect(page.getByRole('navigation')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Toggle File Manager' })).toBeVisible();
  await expect(page.getByRole('textbox', { name: 'Log filename template' })).toBeVisible();
});

test('creates dashboard and view tabs and restores the active view state', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('dashboard-widgets', '[]'));
  await page.goto('/');

  await page.getByRole('button', { name: 'Add workspace tab' }).click();
  await page.getByRole('menuitem', { name: 'New Dashboard' }).click();
  await expect(page.getByText('Dashboard 2', { exact: true })).toBeVisible();
  await page.getByRole('tabpanel', { name: 'Dashboard 2' }).click({ button: 'right', position: { x: 700, y: 450 } });
  await page.getByText('Add Chart Widget').click();
  await expect(page.getByText('No signals configured.')).toBeVisible();
  const tileGrid = await page.locator('.tile-grid').boundingBox();
  const dashboardBounds = await page.locator('.dashboard-tiles-container').boundingBox();
  expect(tileGrid?.height).toBeGreaterThan((dashboardBounds?.height ?? 0) * 0.9);
  await expect.poll(() => page.evaluate(() => {
    const workspace = JSON.parse(localStorage.getItem('wolftrack-workspace-dev') ?? 'null')
    const dashboard = workspace?.tabs?.find((tab: { kind: string; title: string }) => tab.kind === 'dashboard' && tab.title === 'Dashboard 2')
    return workspace?.version === 3 && dashboard?.layout?.type === 'tiles' && Boolean(dashboard.layout.state?.grid)
  })).toBe(true)
  await page.reload()
  await expect(page.getByText('No signals configured.')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Maximize tile' })).toBeVisible()
  await page.locator('.tile-panel__toolbar').first().click({ button: 'right', position: { x: 50, y: 12 } })
  await page.getByText('Add Chart Widget').click()
  await expect(page.locator('.tile-panel')).toHaveCount(2)
  const sourceHeader = await page.locator('.tile-panel').first().locator('.base-widget__header').boundingBox()
  const targetTile = await page.locator('.tile-panel').nth(1).boundingBox()
  expect(sourceHeader).not.toBeNull()
  expect(targetTile).not.toBeNull()
  await page.mouse.move(sourceHeader!.x + sourceHeader!.width / 2, sourceHeader!.y + sourceHeader!.height / 2)
  await page.mouse.down()
  await page.mouse.move(targetTile!.x + targetTile!.width / 2, targetTile!.y + 12, { steps: 12 })
  const preview = page.locator('.tile-drop-preview__region')
  await expect(preview).toBeVisible()
  const previewBounds = await preview.boundingBox()
  expect(previewBounds?.height).toBeGreaterThan(targetTile!.height * 0.48)
  expect(previewBounds?.height).toBeLessThan(targetTile!.height * 0.52)
  await page.mouse.up()
  await expect(page.locator('.tile-panel')).toHaveCount(2)
  await page.getByRole('button', { name: 'Replace…' }).first().click()
  await page.getByRole('menuitem', { name: 'Base Widget' }).first().click()
  await expect(page.locator('.tile-panel').first()).toContainText('Base Widget')
  await page.getByRole('button', { name: 'Maximize tile' }).first().click()
  await expect(page.locator('.tile-panel--maximized')).toBeVisible()
  const maximizedBounds = await page.locator('.tile-panel--maximized').boundingBox()
  const viewportSize = page.viewportSize()
  expect(maximizedBounds?.x).toBeGreaterThanOrEqual(0)
  expect(maximizedBounds?.y).toBeGreaterThanOrEqual(0)
  expect(maximizedBounds?.width).toBeGreaterThan((viewportSize?.width ?? 0) * 0.9)
  expect(maximizedBounds?.height).toBeGreaterThan((viewportSize?.height ?? 0) * 0.75)
  expect((maximizedBounds?.x ?? Infinity) + (maximizedBounds?.width ?? 0))
    .toBeLessThanOrEqual(viewportSize?.width ?? 0)
  expect((maximizedBounds?.y ?? Infinity) + (maximizedBounds?.height ?? 0))
    .toBeLessThanOrEqual(viewportSize?.height ?? 0)
  await page.getByRole('button', { name: 'Restore tile size' }).click()
  await expect(page.locator('.tile-panel--maximized')).toHaveCount(0)
  page.once('dialog', (dialog) => dialog.accept('Test Dashboard'));
  await page.getByRole('button', { name: 'Rename active tab' }).click();
  await expect(page.getByRole('tab', { name: 'Test Dashboard' })).toBeVisible();
  await page.getByRole('button', { name: 'Close active tab' }).click();
  await expect(page.getByRole('tab', { name: 'Dashboard 1' })).toBeVisible();

  await page.getByRole('button', { name: 'Add workspace tab' }).click();
  await page.getByRole('menuitem', { name: 'Workspace Guide' }).click();
  await expect(page.getByRole('heading', { name: 'Workspace guide' })).toBeVisible();
  await page.getByRole('button', { name: 'Save view state' }).click();
  await expect(page.locator('.workspace-summary [role="status"]')).toHaveText('View state saved with this tab.');
  await expect.poll(() => page.evaluate(() => {
    const workspace = JSON.parse(localStorage.getItem('wolftrack-workspace-dev') ?? 'null')
    return workspace?.tabs?.some((tab: { kind: string; state?: { visited?: boolean } }) => tab.kind === 'view' && tab.state?.visited)
  })).toBe(true)

  await page.reload();
  await expect(page.getByRole('heading', { name: 'Workspace guide' })).toBeVisible();
  await expect(page.locator('.workspace-summary [role="status"]')).toHaveText('View state saved with this tab.');
  await expect.poll(() => page.evaluate(() => localStorage.getItem('dashboard-widgets'))).toBeNull();
  await expect.poll(() => page.evaluate(() => localStorage.getItem('dashboard-widgets-migrated-v1'))).toBe('[]');
});

test('shows a directional preview while moving a widget from its title bar', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('wolftrack-workspace-dev', JSON.stringify({
    format: 'wolftrack-workspace',
    version: 4,
    activeTabId: 'drag-dashboard',
    tabs: [{
      id: 'drag-dashboard',
      kind: 'dashboard',
      title: 'Drag Dashboard',
      dataContextId: 'shared',
      layout: {
        type: 'tiles',
        widgets: [
          { i: 'drag-source', type: 'chart', title: 'Source chart', signals: [], config: {}, createdAt: 1 },
          { i: 'drag-target', type: 'chart', title: 'Target chart', signals: [], config: {}, createdAt: 2 },
        ],
        state: null,
      },
    }],
    dockviewLayout: null,
  })))
  await page.goto('/')
  await expect(page.locator('.tile-panel')).toHaveCount(2)

  const sourceHeader = await page.locator('[data-widget-id="drag-source"] .base-widget__header').boundingBox()
  const targetTile = await page.locator('[data-widget-id="drag-target"]').boundingBox()
  expect(sourceHeader).not.toBeNull()
  expect(targetTile).not.toBeNull()
  await page.mouse.move(sourceHeader!.x + sourceHeader!.width / 2, sourceHeader!.y + sourceHeader!.height / 2)
  await page.mouse.down()
  await page.mouse.move(targetTile!.x + targetTile!.width / 2, targetTile!.y + 12, { steps: 12 })
  const preview = page.locator('.tile-drop-preview__region')
  await expect(preview).toBeVisible()
  const previewBounds = await preview.boundingBox()
  expect(previewBounds?.height).toBeGreaterThan(targetTile!.height * 0.48)
  expect(previewBounds?.height).toBeLessThan(targetTile!.height * 0.52)
  await page.mouse.up()
  await expect(page.locator('.tile-panel')).toHaveCount(2)
  const movedSource = await page.locator('[data-widget-id="drag-source"]').boundingBox()
  const movedTarget = await page.locator('[data-widget-id="drag-target"]').boundingBox()
  expect(movedSource).not.toBeNull()
  expect(movedTarget).not.toBeNull()
  expect(movedSource!.y + movedSource!.height).toBeLessThanOrEqual(movedTarget!.y + 2)
})

test('scrolls the dashboard in both directions when widget minimums exceed the viewport', async ({ page }) => {
  await page.addInitScript(() => {
    const widgets = Array.from({ length: 8 }, (_, index) => ({
      i: `scroll-widget-${index}`,
      type: 'chart',
      title: `Scroll widget ${index}`,
      signals: [],
      config: {},
      createdAt: index,
    }))
    localStorage.setItem('wolftrack-workspace-dev', JSON.stringify({
      format: 'wolftrack-workspace',
      version: 4,
      activeTabId: 'scroll-dashboard',
      tabs: [{
        id: 'scroll-dashboard',
        kind: 'dashboard',
        title: 'Scroll dashboard',
        dataContextId: 'shared',
        layout: { type: 'tiles', widgets, state: null },
      }],
      dockviewLayout: null,
    }))
  })
  await page.goto('/')
  await expect(page.locator('.tile-panel')).toHaveCount(8)

  const viewport = page.locator('.dashboard-viewport')
  await expect.poll(() => viewport.evaluate((element) => ({
    horizontal: element.scrollWidth > element.clientWidth,
    vertical: element.scrollHeight > element.clientHeight,
  }))).toEqual({ horizontal: true, vertical: true })

  const firstTile = await page.locator('.tile-panel').first().boundingBox()
  expect(firstTile?.width).toBeGreaterThanOrEqual(319)
  expect(firstTile?.height).toBeGreaterThanOrEqual(219)

  await viewport.evaluate((element) => {
    element.scrollTo({ left: element.scrollWidth, top: element.scrollHeight })
  })
  await expect.poll(() => viewport.evaluate((element) => element.scrollLeft)).toBeGreaterThan(0)
  await expect.poll(() => viewport.evaluate((element) => element.scrollTop)).toBeGreaterThan(0)
})

test('resizes a single widget from its border and restores the canvas size', async ({ page }) => {
  await page.addInitScript(() => {
    if (localStorage.getItem('wolftrack-workspace-dev')) return
    localStorage.setItem('wolftrack-workspace-dev', JSON.stringify({
      format: 'wolftrack-workspace',
      version: 4,
      activeTabId: 'expand-dashboard',
      tabs: [{
        id: 'expand-dashboard',
        kind: 'dashboard',
        title: 'Expand dashboard',
        dataContextId: 'shared',
        layout: {
          type: 'tiles',
          widgets: [{
            i: 'expand-widget', type: 'chart', title: 'Expandable chart',
            signals: [], config: {}, createdAt: 1,
          }],
          state: null,
        },
      }],
      dockviewLayout: null,
    }))
  })
  await page.goto('/')
  await expect(page.locator('.tile-panel')).toHaveCount(1)

  const viewport = page.locator('.dashboard-viewport')
  const canvas = page.locator('.dashboard-canvas')
  const panel = page.locator('.tile-panel')
  const viewportBounds = await viewport.boundingBox()
  expect(viewportBounds).not.toBeNull()
  let bounds = await panel.boundingBox()
  expect(bounds).not.toBeNull()
  await page.mouse.move(bounds!.x + bounds!.width - 28, bounds!.y + bounds!.height / 2)
  await page.mouse.down()
  await page.mouse.move(viewportBounds!.x + viewportBounds!.width - 4, bounds!.y + bounds!.height / 2, { steps: 6 })
  await expect(page.locator('.dashboard-tiles-container')).toHaveAttribute('data-canvas-resize-hover', 'width')
  await page.waitForTimeout(180)
  await page.mouse.up()
  await expect.poll(() => viewport.evaluate((element) => element.scrollWidth > element.clientWidth)).toBe(true)

  await viewport.evaluate((element) => element.scrollTo({ left: element.scrollWidth, top: 0 }))
  bounds = await panel.boundingBox()
  expect(bounds).not.toBeNull()
  await page.mouse.move(bounds!.x + 100, bounds!.y + bounds!.height - 28)
  await page.mouse.down()
  await page.mouse.move(bounds!.x + 100, viewportBounds!.y + viewportBounds!.height - 4, { steps: 6 })
  await expect(page.locator('.dashboard-tiles-container')).toHaveAttribute('data-canvas-resize-hover', 'height')
  await page.waitForTimeout(180)
  await page.mouse.up()
  await expect.poll(() => viewport.evaluate((element) => element.scrollHeight > element.clientHeight)).toBe(true)
  await expect(page.locator('.tile-panel')).toHaveCount(1)
  await expect.poll(() => page.evaluate(() => {
    const workspace = JSON.parse(localStorage.getItem('wolftrack-workspace-dev') ?? 'null')
    const canvasSize = workspace?.tabs?.[0]?.layout?.state?.canvasSize
    return Boolean(canvasSize?.width && canvasSize?.height)
  })).toBe(true)
  await page.reload()
  await expect(page.locator('.tile-panel')).toHaveCount(1)
  const restoredViewport = page.locator('.dashboard-viewport')
  await expect.poll(() => restoredViewport.evaluate((element) => element.scrollWidth > element.clientWidth)).toBe(true)
  await expect.poll(() => restoredViewport.evaluate((element) => element.scrollHeight > element.clientHeight)).toBe(true)

  const restoredPanel = page.locator('.tile-panel')
  await restoredViewport.evaluate((element) => element.scrollTo({ left: element.scrollWidth, top: element.scrollHeight }))
  bounds = await restoredPanel.boundingBox()
  expect(bounds).not.toBeNull()
  await page.mouse.move(bounds!.x + bounds!.width - 28, bounds!.y + bounds!.height / 2)
  await page.mouse.down()
  await page.mouse.move(bounds!.x + bounds!.width - 160, bounds!.y + bounds!.height / 2, { steps: 8 })
  await page.mouse.up()
  await expect.poll(() => restoredViewport.evaluate((element) => element.scrollWidth <= element.clientWidth)).toBe(true)

  bounds = await restoredPanel.boundingBox()
  expect(bounds).not.toBeNull()
  await page.mouse.move(bounds!.x + 100, bounds!.y + bounds!.height - 28)
  await page.mouse.down()
  await page.mouse.move(bounds!.x + 100, bounds!.y + bounds!.height - 160, { steps: 8 })
  await page.mouse.up()
  await expect.poll(() => restoredViewport.evaluate((element) => element.scrollHeight <= element.clientHeight)).toBe(true)
})

test('extends a multi-widget canvas by dragging its existing splitter', async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('wolftrack-workspace-dev', JSON.stringify({
      format: 'wolftrack-workspace',
      version: 4,
      activeTabId: 'split-dashboard',
      tabs: [{
        id: 'split-dashboard',
        kind: 'dashboard',
        title: 'Split dashboard',
        dataContextId: 'shared',
        layout: {
          type: 'tiles',
          widgets: ['left-widget', 'right-widget'].map((i) => ({
            i, type: 'chart', title: i, signals: [], config: {}, createdAt: 1,
          })),
          state: null,
        },
      }],
      dockviewLayout: null,
    }))
  })
  await page.goto('/')
  await expect(page.locator('.tile-panel')).toHaveCount(2)

  const viewport = page.locator('.dashboard-viewport')
  const sash = page.locator('.dv-sash').first()
  await expect(sash).toBeVisible()
  const bounds = await sash.boundingBox()
  expect(bounds).not.toBeNull()
  await page.mouse.move(bounds!.x + bounds!.width / 2, bounds!.y + bounds!.height / 2)
  await page.mouse.down()
  await page.mouse.move(bounds!.x + bounds!.width / 2 + 450, bounds!.y + bounds!.height / 2, { steps: 18 })
  await page.mouse.up()
  await expect.poll(() => viewport.evaluate((element) => element.scrollWidth > element.clientWidth)).toBe(true)
  await expect(page.locator('.tile-panel')).toHaveCount(2)

  const initialScrollWidth = await viewport.evaluate((element) => element.scrollWidth)
  const viewportBounds = await viewport.boundingBox()
  expect(viewportBounds).not.toBeNull()
  await viewport.evaluate((element) => element.scrollTo({ left: element.scrollWidth, top: 0 }))
  const outerPanel = page.locator('.tile-panel').last()
  const outerBounds = await outerPanel.boundingBox()
  expect(outerBounds).not.toBeNull()
  await page.mouse.move(outerBounds!.x + outerBounds!.width - 28, outerBounds!.y + outerBounds!.height / 2)
  await page.mouse.down()
  await page.mouse.move(viewportBounds!.x + viewportBounds!.width - 4, outerBounds!.y + outerBounds!.height / 2, { steps: 6 })
  await page.waitForTimeout(180)
  await page.mouse.up()
  await expect.poll(() => viewport.evaluate((element) => element.scrollWidth)).toBeGreaterThan(initialScrollWidth)
})

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
  await page.locator('.tile-panel__toolbar').first().click({ button: 'right', position: { x: 50, y: 12 } });
  await page.getByText('Add Chart Widget').click();
  await expect(page.getByText('No signals configured.')).toBeVisible();
});
