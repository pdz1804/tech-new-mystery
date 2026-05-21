import { test, expect } from '@playwright/test';

test.use({
  viewport: {
    height: 900,
    width: 1440
  }
});

test('test', async ({ page }) => {
  await page.goto('http://localhost:3000/');
});