import { expect, test } from '@playwright/test';
import { refusalAnswer, supportedAnswer } from '../src/test/fixtures';

test.beforeEach(async ({ page }): Promise<void> => {
  // Local assets are allowed; all non-loopback requests are blocked, including source links.
  await page.route('**/*', async (route): Promise<void> => {
    const host = new URL(route.request().url()).hostname;
    if (['127.0.0.1', 'localhost'].includes(host)) await route.continue();
    else await route.abort();
  });
});

test('question to supported answer with expandable exact citation', async ({ page }): Promise<void> => {
  await page.route('**/api/ask', (route) => route.fulfill({ json: supportedAnswer }));
  await page.goto('/');
  await page.getByRole('textbox').fill('What should I retain?');
  await page.getByRole('button', { name: 'Find an answer' }).click();
  await expect(page.getByText(supportedAnswer.answer, { exact: true })).toBeVisible();
  await page.getByText('Offline UI fixture').click();
  await expect(page.locator('blockquote')).toHaveText('Keep the original document');
  await expect(page.getByRole('link', { name: 'Open document ↗' })).toHaveAttribute('href',
    'https://example.test/document.pdf#page=2');
  await expect(page.getByText('Scripted demo response')).toBeVisible();
});

test('refusal contains no citation cards', async ({ page }): Promise<void> => {
  await page.route('**/api/ask', (route) => route.fulfill({ json: refusalAnswer }));
  await page.goto('/');
  await page.getByRole('textbox').fill('Unsupported question');
  await page.getByRole('button', { name: 'Find an answer' }).click();
  await expect(page.getByText(refusalAnswer.answer)).toBeVisible();
  await expect(page.locator('details')).toHaveCount(0);
});

test('mobile layout fits the viewport and handles API failures', async ({ page }): Promise<void> => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.route('**/api/ask', (route) => route.fulfill({ status: 504,
    json: { error: { code: 'provider_timeout', message: 'private text' } } }));
  await page.goto('/');
  await page.getByRole('textbox').fill('A question');
  await page.getByRole('button', { name: 'Find an answer' }).click();
  await expect(page.getByRole('alert')).toContainText('The model took too long');
  expect(await page.evaluate((): boolean => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});
