/** Explicit live evaluation only: exercise the real UI without intercepting answers. */
import assert from 'node:assert/strict';
import { readFile, mkdir, writeFile } from 'node:fs/promises';
import process from 'node:process';
import { chromium, expect } from '@playwright/test';
import type { AskResponse } from '../src/api/ask.ts';

if (!process.argv.includes('--allow-real-calls') || process.env.ENABLE_REAL_PROVIDERS !== 'true') {
  throw new Error('Explicit real-provider authorization is required.');
}

const rows = (await readFile('eval/golden.jsonl', 'utf8')).trim().split('\n')
  .map((line): { id: string; question: string } => JSON.parse(line) as { id: string; question: string });
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 1100 } });
page.setDefaultTimeout(95000);
await mkdir('eval/results', { recursive: true });
const records: { id: string; answer: AskResponse }[] = [];
try {
  // External source links are inspected, never followed during this check.
  await page.route('**/*', async (route): Promise<void> => {
    if (new URL(route.request().url()).hostname === '127.0.0.1') await route.continue();
    else await route.abort();
  });
  await page.goto('http://127.0.0.1:8080/');
  await expect(page.getByRole('button', { name: 'Vector', exact: true }))
    .toHaveAttribute('aria-pressed', 'true');
  for (const id of ['q01', 'q05']) {
    const question = rows.find((row) => row.id === id);
    assert(question, 'Required browser evaluation question is missing.');
    await page.getByRole('textbox').fill(question.question);
    const responsePromise = page.waitForResponse((response) =>
      response.url().endsWith('/api/ask') && response.request().method() === 'POST');
    await page.getByRole('button', { name: 'Find an answer' }).click();
    const response = await responsePromise;
    assert.equal(response.status(), 200, 'Live browser API request failed.');
    const answer = await response.json() as AskResponse;
    records.push({ id, answer });
    assert.equal(answer.supported, id === 'q01');
    assert.notEqual(answer.mode, 'scripted');
    if (answer.supported) assert.equal(answer.mode, 'model');
    await expect(page.getByText(answer.answer, { exact: true })).toBeVisible();
    if (answer.supported) {
      assert(answer.citations.length > 0);
      assert.equal(answer.verification.valid, answer.verification.proposed);
      await expect(page.locator('.citation-card')).toHaveCount(answer.citations.length);
      const citation = answer.citations[0];
      assert(citation);
      await page.locator('.citation-card summary').first().click();
      await expect(page.locator('blockquote').first()).toHaveText(citation.quote);
      assert(citation.source_url);
      const link = new URL(citation.source_url);
      link.hash = `page=${citation.page}`;
      await expect(page.getByRole('link', { name: 'Open document ↗' }).first())
        .toHaveAttribute('href', link.toString());
    } else {
      assert.equal(answer.citations.length, 0);
      await expect(page.locator('.citation-card')).toHaveCount(0);
    }
    await page.screenshot({ path: `eval/results/browser-${id}.png`, fullPage: true });
  }
  await writeFile('eval/results/browser-check.json', JSON.stringify({ ok: true, records }, null, 2));
  process.stdout.write('Real browser answer, expanded citation, page link, and refusal passed.\n');
} catch {
  await page.screenshot({ path: 'eval/results/browser-failure.png', fullPage: true });
  await writeFile('eval/results/browser-check.json', JSON.stringify({ ok: false, records }, null, 2));
  throw new Error('Live browser evaluation failed; review its sanitized artifact.');
} finally {
  await browser.close();
}
