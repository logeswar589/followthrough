// Records existing real model output. Run scripts/smoke.py first.
// Synthetic input remains labelled in the app; this video has no narration.
const { chromium } = require('playwright');
const fs = require('node:fs');
const path = require('node:path');

(async () => {
  const item = JSON.parse(fs.readFileSync('artifacts/live-smoke.json', 'utf8'));
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  try {
    const context = await browser.newContext({
      viewport: { width: 1440, height: 1000 },
      recordVideo: { dir: 'artifacts/video', size: { width: 1440, height: 1000 } },
    });
    const page = await context.newPage();
    const video = page.video();
    await page.goto('http://127.0.0.1:8000');
    await page.locator('[data-id="' + item.id + '"]').click();
    await page.waitForTimeout(2500);
    await page.locator('[data-tab="transcript"]').click();
    await page.locator('#detail').scrollIntoViewIfNeeded();
    await page.waitForTimeout(6000);
    await page.locator('[data-tab="actions"]').click();
    await page.locator('.action').first().scrollIntoViewIfNeeded();
    await page.waitForTimeout(5000);
    const download = page.waitForEvent('download');
    await page.getByRole('button', { name: 'Download .ics ↗' }).click();
    await (await download).saveAs('artifacts/demo-calendar.ics');
    await page.waitForTimeout(2000);
    await page.locator('.action').filter({ hasText: 'HDMI' }).scrollIntoViewIfNeeded();
    await page.waitForTimeout(5000);
    await page.locator('.action').filter({ hasText: 'Rahul' }).scrollIntoViewIfNeeded();
    await page.waitForTimeout(4000);
    await page.locator('[data-tab="recap"]').click();
    await page.locator('#recap').scrollIntoViewIfNeeded();
    await page.waitForTimeout(5000);
    await page.locator('[data-tab="actions"]').click();
    await page.locator('.action').first().scrollIntoViewIfNeeded();
    await page.screenshot({ path: 'artifacts/demo-preview.jpg' });
    await context.close();
    await video.saveAs(path.resolve('artifacts/followthrough-walkthrough.webm'));
    console.log('Saved artifacts/followthrough-walkthrough.webm (silent, existing real Gemma output).');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
