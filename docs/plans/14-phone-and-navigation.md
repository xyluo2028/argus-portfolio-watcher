# 14. Phone and navigation

Roadmap items I13, I15, B8. Effort: medium; four parts, any order.

## Why

The owner reads Argus on a phone over Tailscale. Every page fits a 390 px screen without
sideways page scroll, which earlier work got right. What remains is that the phone shows a squeezed
desktop page rather than a phone page:

- The holdings table leads with quantity, average cost and price. What you check on a phone, the
  day's move, the value and the gain, is off-screen to the right.
- The stock page is 6,250 px tall and Markets 6,300 px, with no way to jump to a section.
- Two phone tests fail on WebKit, the engine iPhones use (B8).
- "Check every page at phone width" has been reported in 21 loop rounds (backlog B-002); read that
  item for the specific complaints collected there.

## Part A: the two WebKit failures (B8)

Reproduce first:

```bash
cd frontend
npx playwright test --project=webkit --trace off -g "autocomplete|comparison"
```

Both pass on Chromium and fail on WebKit, on old commits too, so they are engine differences in
touch handling, and probably real on an iPhone.

1. **Tapping an autocomplete suggestion leaves the typed text** ("app" stays "app" instead of
   becoming "AAPL"). `components/TickerInput.tsx`: the input closes the list on blur
   (`onBlur={() => setOpen(false)}`); each option calls `preventDefault` on `pointerdown` to keep
   focus in the input and picks on `click`. A likely cause: on WebKit, preventing `pointerdown`
   doesn't stop the focus change that a touch triggers, so the input blurs, the list closes, and
   the click never reaches the option. Confirm before fixing. Fixes to consider: pick on
   `pointerdown` or `pointerup` instead of `click`; or defer the blur's close until after a
   pending pick.
2. **Tapping the comparison chart doesn't show values in the legend.**
   `components/CompareChart.tsx`: the SVG sets the hover point on `pointerdown` and `pointermove`
   and clears it on `pointerleave` and `pointercancel`. A likely cause: after a touch ends, WebKit
   fires `pointerleave` (the finger is gone) or `pointercancel` (the browser took the gesture for
   scrolling), which clears the hover the tap just set. Confirm. On touch, a tap should pin the
   inspected point until the next tap elsewhere; clearing on leave makes sense only for a mouse
   (check `event.pointerType`).

Once both pass, add WebKit to the CI job from plan 04.

## Part B: a phone holdings table

**Decided.** On narrow screens the table shows four columns: symbol (with the name beneath, as
now), day %, value, and gain %. The rest stay available: a "More columns" toggle above the table
switches to the full set, which scrolls sideways inside its card as today.

- `components/HoldingsTable.tsx` builds its columns from a list; mark each column as "phone" or
  not, and choose the set from the viewport width (a small `useMediaQuery` hook; the breakpoint the
  stylesheet already uses for the top bar is a reasonable one).
- Sorting, the rank column and the compare checkboxes keep working in both sets.
- The same treatment for the watchlist table (`pages/Watchlist.tsx`, `WatchTable`): symbol, price,
  day %, and one valuation column.
- The tabbed variants (Financials, Growth, Dividends…) in `components/HoldingsTabs.tsx` already
  keep the symbol column visible while scrolling; leave them.

## Part C: section navigation on long pages

**Decided.** The stock page and Markets get a row of section links under the top bar, sticky while
scrolling: on the stock page "Chart, Fundamentals, Position, Peers, Research, Notes, Events,
Financials"; on Markets "Indices, Sentiment, Sectors, Rates, Calendar". Tapping scrolls to the
section; the current section is highlighted (an `IntersectionObserver` is enough). On a phone the
row scrolls sideways within itself. Give each section an `id` so links can target it
(`/t/NVDA#research`).

The app's `Main` component scrolls to the top on every path change; make sure a hash in the
address wins over that.

## Part D: stock page proportions (I15)

- The "Reported financials" revenue chart is far larger than its neighbours and its labels are
  oversized. Size it like the other charts on the page, and fix the clipped axis label noted in
  backlog B-061.
- When you hold the stock or have a thesis note for it, show a one-line summary under the price:
  shares, value, gain, and the first line of the thesis, linking to the position card and the
  notes. Today that sits four screens down.

## Optional: installable app

A web app manifest (name, icons, `display: standalone`, theme colors for light and dark) lets
"Add to Home Screen" open Argus without browser chrome. No service worker and no offline mode:
Argus is live data. The manifest must be reachable without signing in, like the other static
files.

## Watch out

- The phone tests assert layout details (touch target sizes, no page overflow, the 16 px input
  font that stops iPhone zoom). Run them on both engines after every part.
- A shared portfolio is read-only (`useSharedBy()`): new controls that write must hide for it.
- Don't hide information on a phone without a way to reach it.

## Done when

- `npx playwright test --trace off` passes on Chromium and WebKit.
- At 390 px the dashboard's holdings show the day's move, value and gain without scrolling the
  table; "More columns" shows the rest.
- The section row works on the stock page and Markets at both widths, in light and dark, and a
  link with a hash lands on its section.
- Screenshots at 390 px of the dashboard, a stock page, Markets and the watchlist are in your
  report, before and after.
