import { expect, test, type Page } from "@playwright/test";
import { mockApi } from "./fixtures";

const errors = new WeakMap<Page, string[]>();
const controls = new WeakMap<Page, Awaited<ReturnType<typeof mockApi>>>();

test.beforeEach(async ({ page }) => {
  const messages: string[] = [];
  errors.set(page, messages);
  page.on("pageerror", (e) => messages.push(e.message));
  controls.set(page, await mockApi(page));
});

test.afterEach(async ({ page }) => {
  expect(errors.get(page), "No uncaught errors while rendering or using the phone UI").toEqual([]);
});

async function noPageOverflow(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth), "Only tables and tab strips should scroll sideways")
    .toBeLessThanOrEqual(await page.evaluate(() => innerWidth));
}

for (const width of [320, 390, 430]) {
  test(`all stock chart ranges are visible and tappable at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 844 });
    await page.goto("/t/TEST");
    const ranges = page.getByRole("group", { name: "Chart range", exact: true });
    await expect(page.locator(".chart-status")).toHaveText("1Y chart");
    await expect(page.locator(".chart-settings")).not.toHaveAttribute("open", "");
    for (const [label, period, interval] of [
      ["1D", "1d", "5m"], ["5D", "5d", "15m"], ["1M", "1mo", "1d"], ["3M", "3mo", "1d"],
      ["6M", "6mo", "1d"], ["YTD", "ytd", "1d"], ["1Y", "1y", "1d"], ["5Y", "5y", "1d"], ["Max", "max", "1d"],
    ]) {
      const button = ranges.getByRole("button", { name: new RegExp(`^${label}\\b`) });
      const box = (await button.boundingBox())!;
      expect(box.x).toBeGreaterThanOrEqual(0);
      expect(box.x + box.width).toBeLessThanOrEqual(width);
      expect(box.height).toBeGreaterThanOrEqual(44);
      const request = page.waitForResponse((r) => {
        const url = new URL(r.url());
        return url.pathname === "/api/history/TEST" && url.searchParams.get("period") === period
          && url.searchParams.get("interval") === interval;
      });
      await button.tap();
      await request;
      await expect(button).toHaveAttribute("aria-pressed", "true");
      await expect(page.locator(".chart-status")).toHaveText(`${label} chart`);
    }
    await noPageOverflow(page);
    await page.getByRole("button", { name: "Reset zoom" }).tap();
    await page.setViewportSize({ width: 844, height: width });
    await noPageOverflow(page);
  });
}

test("phone menu reaches every page, closes after navigation, and exposes market details", async ({ page }) => {
  await page.goto("/");
  const nav = page.getByRole("navigation", { name: "Main navigation" });
  const menu = page.getByRole("button", { name: "Menu", exact: true });
  await expect(nav).toBeHidden();
  await menu.tap();
  await expect(nav.getByRole("link")).toHaveCount(9);
  await nav.getByRole("link", { name: "Transactions" }).tap();
  await expect(page).toHaveURL(/\/transactions$/);
  await expect(nav).toBeHidden();
  await menu.tap();
  await page.keyboard.press("Escape");
  await expect(nav).toBeHidden();
  await expect(menu).toBeFocused();
  await page.locator(".market-status summary").tap();
  await expect(page.locator(".market-detail")).toBeVisible();
  await noPageOverflow(page);
});

test("autocomplete completes on touch without submitting, and fields avoid iPhone input zoom", async ({ page }) => {
  await page.goto("/watchlist");
  const input = page.getByRole("combobox", { name: "Tickers" });
  await input.fill("app");
  const option = page.getByRole("option", { name: /AAPL Apple/ });
  await expect(option).toBeVisible();
  await option.tap();
  await expect(input).toHaveValue("AAPL");
  await expect(page.getByRole("listbox")).toBeHidden();
  expect(await input.evaluate((el) => parseFloat(getComputedStyle(el).fontSize))).toBeGreaterThanOrEqual(16);
  await noPageOverflow(page);
});

test("holdings keep the symbol visible when scrolling columns", async ({ page }) => {
  await page.goto("/");
  const table = page.locator(".table-wrap").first();
  await expect(table.locator("td.symbol-col")).toHaveText(/TEST/);
  await table.scrollIntoViewIfNeeded();
  await table.evaluate((el) => { el.scrollLeft = el.scrollWidth; });
  const tableBox = (await table.boundingBox())!;
  const symbolBox = (await table.locator("td.symbol-col").boundingBox())!;
  expect(symbolBox.x).toBeGreaterThanOrEqual(tableBox.x - 1);
  expect(symbolBox.x + symbolBox.width).toBeLessThanOrEqual(tableBox.x + tableBox.width);
  await noPageOverflow(page);
});

test("range changes show progress, recover from failure, and ignore an older response", async ({ page }) => {
  const control = controls.get(page)!;
  await page.goto("/t/TEST");
  await expect(page.locator(".chart-status")).toHaveText("1Y chart");
  control.failNextHistory = true;
  const ranges = page.getByRole("group", { name: "Chart range", exact: true });
  await ranges.getByRole("button", { name: /^5Y\b/ }).tap();
  await expect(page.getByText("Price history temporarily unavailable.")).toBeVisible();
  await page.getByRole("button", { name: "Retry chart" }).tap();
  await expect(page.locator(".chart-canvas canvas").first()).toBeVisible();
  control.historyDelay.set("3mo", 600);
  const slow = page.waitForResponse((r) => r.url().includes("period=3mo"));
  await ranges.getByRole("button", { name: /^3M\b/ }).tap();
  await expect(page.locator(".chart-status")).toHaveText("Loading 3M chart…");
  await ranges.getByRole("button", { name: /^1M\b/ }).tap();
  await expect(page.locator(".chart-status")).toHaveText("1M chart");
  await slow;
  await expect(page.locator(".chart-status")).toHaveText("1M chart");
  await page.locator(".chart-settings summary").tap();
  await page.getByRole("button", { name: "RSI 14", exact: true }).tap();
  await expect(page.getByRole("button", { name: "RSI 14", exact: true })).toHaveAttribute("aria-pressed", "true");
});

test("a vertical touch drag over the candle chart scrolls the page", async ({ page, browserName }) => {
  test.skip(browserName !== "chromium", "Native touch gesture dispatch uses Chromium's test protocol");
  await page.goto("/t/TEST");
  await expect(page.locator(".chart-canvas canvas").first()).toBeVisible();
  await page.locator(".chart-box").evaluate((el) => window.scrollTo(0, el.getBoundingClientRect().top + scrollY - 150));
  const before = await page.evaluate(() => scrollY);
  const box = (await page.locator(".chart-box").boundingBox())!;
  const client = await page.context().newCDPSession(page);
  const x = box.x + box.width / 2, y = box.y + 230;
  await client.send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [{ x, y }] });
  for (let i = 1; i <= 8; i++) await client.send("Input.dispatchTouchEvent", {
    type: "touchMove", touchPoints: [{ x, y: y - i * 20 }],
  });
  await client.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] });
  await expect.poll(() => page.evaluate(() => scrollY)).toBeGreaterThan(before + 50);
});

test("comparison ranges and chart inspection work with touch", async ({ page }) => {
  await page.goto("/compare?s=TEST,AAPL");
  const ranges = page.getByRole("group", { name: "Comparison range" });
  await expect(ranges).toBeVisible();
  await ranges.getByRole("button", { name: "5Y", exact: true }).tap();
  await expect(ranges.getByRole("button", { name: "5Y", exact: true })).toHaveAttribute("aria-pressed", "true");
  const chart = page.locator(".compare-chart svg");
  await expect(chart).toBeVisible();
  await chart.tap({ position: { x: 100, y: 100 } });
  await expect(page.locator('[aria-label="Legend"]')).toContainText("·");
  await noPageOverflow(page);
});

for (const width of [320, 390]) {
  test(`main sections fit a ${width}px phone`, async ({ page }) => {
    await page.setViewportSize({ width, height: 844 });
    for (const path of ["/", "/watchlist", "/transactions", "/analysis", "/markets", "/screener", "/compare?s=TEST,AAPL", "/alerts", "/data"]) {
      await page.goto(path);
      await expect(page.locator("main .card, main .tile").first()).toBeVisible();
      await noPageOverflow(page);
    }
  });
}

test.describe("desktop and tablet", () => {
  test.use({ isMobile: false, hasTouch: false });
  test("navigation and chart controls remain available", async ({ page }) => {
    for (const width of [768, 1440]) {
      await page.setViewportSize({ width, height: 1000 });
      await page.goto("/t/TEST");
      await expect(page.getByRole("navigation")).toBeVisible();
      await expect(page.getByRole("button", { name: "Menu", exact: true })).toBeHidden();
      await expect(page.locator(".chart-settings")).toHaveAttribute("open", "");
      await expect(page.locator(".chart-status")).toHaveText("1Y chart");
      await noPageOverflow(page);
    }
  });
});
