import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright');

const input = await new Promise((resolve, reject) => {
  let data = '';
  process.stdin.setEncoding('utf8');
  process.stdin.on('data', chunk => data += chunk);
  process.stdin.on('end', () => resolve(data));
  process.stdin.on('error', reject);
});

const payload = JSON.parse(input || '{}');
const items = payload.items || [];
const timeout = Math.max(3000, Math.min(45000, Number(payload.timeoutMs || 15000)));
const results = [];

let browser;
try {
  const launchOptions = { headless: true };
  if (process.env.CHROME_EXE) launchOptions.executablePath = process.env.CHROME_EXE;
  browser = await chromium.launch(launchOptions);
  const context = await browser.newContext({
    viewport: { width: 1366, height: 900 },
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36',
    locale: 'en-US',
  });

  for (const item of items) {
    const page = await context.newPage();
    const started = item.url || '';
    try {
      let target = started;
      if (target && !/^https?:\/\//i.test(target) && !/^[a-z][a-z0-9+.-]*:/i.test(target)) {
        target = 'https://' + target;
      }
      if (/^[a-z][a-z0-9+.-]*:/i.test(target) && !/^https?:\/\//i.test(target)) {
        results.push({ row: item.row, url: started, final: target, statusCode: 200, note: '非网页深链，浏览器未打开' });
        await page.close();
        continue;
      }
      const response = await page.goto(target, { waitUntil: 'domcontentloaded', timeout });
      try { await page.waitForLoadState('networkidle', { timeout: Math.min(6000, timeout) }); } catch {}
      await page.waitForTimeout(1800);
      results.push({
        row: item.row,
        url: started,
        final: page.url(),
        statusCode: response ? response.status() : 200,
        title: await page.title().catch(() => ''),
        note: '浏览器真实打开完成'
      });
    } catch (err) {
      results.push({ row: item.row, url: started, final: page.url(), statusCode: null, error: String(err && err.message || err) });
    } finally {
      await page.close().catch(() => {});
    }
  }
  await context.close();
} catch (err) {
  console.log(JSON.stringify({ error: String(err && err.message || err), results }, null, 0));
  process.exit(0);
} finally {
  if (browser) await browser.close().catch(() => {});
}

console.log(JSON.stringify({ results }, null, 0));




