import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  fullyParallel: true,
  workers: 2,
  use: {
    baseURL: "http://127.0.0.1:4173",
    viewport: { width: 390, height: 844 },
    isMobile: true,
    hasTouch: true,
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  projects: [
    { name: "chromium", use: { browserName: "chromium", channel: process.env.PLAYWRIGHT_CHANNEL } },
    { name: "webkit", use: { browserName: "webkit" } },
  ],
  webServer: {
    command: "npm run dev -- --host 127.0.0.1 --port 4173 --strictPort",
    url: "http://127.0.0.1:4173",
    reuseExistingServer: !process.env.CI,
  },
});
