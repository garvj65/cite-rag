import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  use: { baseURL: 'http://127.0.0.1:8080', browserName: 'chromium', headless: true },
  reporter: 'list',
  retries: 0,
  workers: 1,
});
