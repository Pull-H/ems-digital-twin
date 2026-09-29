import { test, expect } from '@playwright/test';

test('NYC engine, territory, controls and mobile framing', async ({ page }) => {
  test.setTimeout(180000);
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.setViewportSize({ width: 1440, height: 1100 });
  await page.goto('http://localhost:5173');
  await expect(page.getByTestId('historical-workspace')).toBeVisible({ timeout: 60000 });
  const canvas = page.locator('canvas[aria-label="Territorio NYC 3D y unidades simuladas"]');
  await expect(canvas).toBeVisible({ timeout: 30000 });
  await page.waitForTimeout(1500);
  const sample = () => canvas.evaluate((element: HTMLCanvasElement) => {
    const copy = document.createElement('canvas'); copy.width = 96; copy.height = 96;
    const ctx = copy.getContext('2d')!; ctx.drawImage(element, 0, 0, 96, 96);
    const pixels = ctx.getImageData(0, 0, 96, 96).data;
    const colors = new Set<string>();
    for (let i = 0; i < pixels.length; i += 4) colors.add(`${pixels[i]},${pixels[i + 1]},${pixels[i + 2]}`);
    return { count: colors.size, pixels: Array.from(pixels).join(',') };
  });
  const initial = await sample(); expect(initial.count).toBeGreaterThan(30);
  const checkLabels = async () => {
    const labels = await page.locator('[data-zone-label]').evaluateAll(elements => elements.map(e => {
      const r = e.getBoundingClientRect(); return { left: r.left, right: r.right, top: r.top, bottom: r.bottom };
    }));
    expect(labels).toHaveLength(5);
    for (let i = 0; i < labels.length; i++) for (let j = i + 1; j < labels.length; j++) {
      const a = labels[i], b = labels[j];
      expect(a.right <= b.left || b.right <= a.left || a.bottom <= b.top || b.bottom <= a.top).toBeTruthy();
    }
  };
  await checkLabels();
  await canvas.screenshot({ path: 'test-results/nyc-desktop-canvas.png' });
  await page.getByRole('button', { name: 'Avanzar 5 minutos', exact: true }).click();
  await expect(page.getByTestId('simulation-clock')).toContainText('00:05:00', { timeout: 20000 });
  await page.waitForTimeout(500);
  expect((await sample()).pixels).not.toEqual(initial.pixels);
  await page.getByRole('button', { name: 'Vista cenital', exact: true }).click();
  await page.waitForTimeout(700);
  expect((await sample()).pixels).not.toEqual(initial.pixels);
  await page.screenshot({ path: 'test-results/nyc-desktop.png', fullPage: true });
  await page.getByRole('button', { name: '2D', exact: true }).click();
  await expect(page.getByLabel('Mapa NYC 2D')).toBeVisible();
  await expect(page.locator('.leaflet-container canvas')).toBeVisible();
  await page.getByRole('button', { name: 'Dividida', exact: true }).click();
  await expect(canvas).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(1000);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
  expect((await sample()).count).toBeGreaterThan(30);
  await checkLabels();
  await page.screenshot({ path: 'test-results/nyc-mobile.png', fullPage: true });
  await page.getByLabel('Entrada de demanda').selectOption('forecast');
  await page.getByLabel('Duracion NYC').selectOption('60');
  await page.getByLabel('Flota asumida').fill('40');
  await page.getByRole('button', { name: 'Nueva corrida', exact: true }).click();
  await expect(page.getByText('Llegadas sinteticas desde pronosticos', { exact: false })).toBeVisible({ timeout: 60000 });
  await page.getByRole('button', { name: 'Avanzar 5 minutos', exact: true }).click();
  await expect(page.getByTestId('simulation-clock')).toContainText('00:05:00');
  await page.route('**/api/simulations/step', route => route.abort());
  await page.getByRole('button', { name: 'Avanzar 5 minutos', exact: true }).click();
  await expect(page.getByText('La corrida NYC se ha pausado', { exact: false })).toBeVisible();
  await expect(page.getByTestId('historical-workspace')).toBeVisible();
  expect(errors).toEqual([]);
});
