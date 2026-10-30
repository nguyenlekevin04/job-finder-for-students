import { expect, test, type Page } from "@playwright/test";
import fixture from "./fixtures/jobs.json" with { type: "json" };

// Release smoke test: the site built from e2e/fixtures/jobs.json (see e2e/build.mjs).
const TOTAL = fixture.jobs.length;
const BOOKMARKS = "dsj:bookmarks:v1";

const count = (page: Page) => page.getByTestId("results-count");
const savedLink = (page: Page) => page.getByRole("link", { name: /^Saved/ });
const typeOption = (page: Page, name: string) =>
  page.getByRole("group", { name: "Type" }).getByRole("button", { name: new RegExp(`^${name}`) });
const row = (page: Page, title: string) => page.getByRole("button", { name: new RegExp(title) });

async function openBoard(page: Page, path = "/") {
  await page.goto(path);
  await expect(count(page)).toBeVisible();
}

test("loads every job", async ({ page }) => {
  await openBoard(page);
  await expect(count(page)).toHaveText(new RegExp(`^${TOTAL} jobs`));
  await expect(page.locator('li[id^="row-"]')).toHaveCount(TOTAL);
  await expect(page).toHaveTitle("dresden/jobs · Student tech jobs in Dresden");
});

test("search narrows the list, syncs ?q= and clearing returns focus to the field", async ({ page }) => {
  await openBoard(page);
  const search = page.getByRole("searchbox", { name: "Search jobs" });
  await search.fill("Backend");
  await expect(count(page)).toHaveText(new RegExp(`^1 of ${TOTAL} jobs`));
  await expect(page).toHaveURL(/[?&]q=Backend/);

  await page.getByRole("button", { name: "Clear search" }).click();
  await expect(search).toBeFocused();
  await expect(search).toHaveValue("");
  await expect(count(page)).toHaveText(new RegExp(`^${TOTAL} jobs`));
  await expect(page).not.toHaveURL(/q=/);
});

test("type filter narrows, syncs the URL and survives a reload", async ({ page }) => {
  await openBoard(page);
  await typeOption(page, "Internship").click();
  await expect(count(page)).toHaveText(new RegExp(`^2 of ${TOTAL} jobs`));
  await expect(page).toHaveURL(/[?&]type=internship/);

  await page.reload();
  await expect(count(page)).toHaveText(new RegExp(`^2 of ${TOTAL} jobs`));
  await expect(typeOption(page, "Internship")).toHaveAttribute("aria-pressed", "true");
});

test("hours and pay show in the row and as facts when the posting states them", async ({ page }) => {
  const [ml, , thesis, backend, , frontend] = fixture.jobs;
  const rowItem = (title: string) => page.locator("li", { has: row(page, title) });
  await openBoard(page);
  await expect(rowItem(ml.title).getByText("15–20 h/week · €15/h", { exact: true })).toBeVisible();
  await expect(rowItem(backend.title).getByText("up to 20 h/week", { exact: true })).toBeVisible();
  await expect(rowItem(frontend.title).getByText("from 25 h/week", { exact: true })).toBeVisible();
  await expect(rowItem(thesis.title)).not.toContainText("h/week");

  await row(page, ml.title).click();
  const facts = rowItem(ml.title).locator("dl");
  await expect(facts.locator("div").first()).toHaveText("Hours15–20 h/week");
  await expect(facts.locator("div").nth(1)).toHaveText("Pay€15/h");

  await row(page, thesis.title).click();
  await expect(rowItem(thesis.title).locator("dt", { hasText: /^(Hours|Pay)$/ })).toHaveCount(0);
});

test("on a phone the terms follow the type on its line", async ({ page }) => {
  const ml = fixture.jobs[0];
  await page.setViewportSize({ width: 375, height: 812 });
  await openBoard(page);
  const item = page.locator("li", { has: row(page, ml.title) });
  await expect(item.getByText("New · Werkstudent · 15–20 h/week · €15/h", { exact: true })).toBeVisible();
});

test("'Up to 20 h/week' keeps jobs stating at most 20 hours, syncs ?hours=20 and survives a reload", async ({ page }) => {
  const option = () => page.getByRole("group", { name: "Options" }).getByRole("button", { name: /^Up to 20 h\/week/ });
  const note = () => page.getByText("Only jobs that state their hours.");
  await openBoard(page);
  await page.getByRole("button", { name: "More filters" }).click();
  await expect(option()).toContainText("2"); // the count sup
  await expect(note()).toHaveCount(0);

  await option().click();
  await expect(count(page)).toHaveText(new RegExp(`^2 of ${TOTAL} jobs`));
  await expect(page.locator('li[id^="row-"]')).toHaveCount(2);
  await expect(page.locator("#row-e2e-ml-werkstudent")).toBeVisible();
  await expect(page.locator("#row-e2e-remote-backend")).toBeVisible();
  await expect(page).toHaveURL(/[?&]hours=20/);
  await expect(note()).toBeVisible();
  await expect(page.getByRole("button", { name: "Clear 1 filter" })).toBeVisible();

  await page.reload();
  await expect(count(page)).toHaveText(new RegExp(`^2 of ${TOTAL} jobs`));
  await expect(option()).toBeVisible(); // the panel opened itself
  await expect(option()).toHaveAttribute("aria-pressed", "true");

  await typeOption(page, "Werkstudent").click();
  await expect(page.getByRole("button", { name: "Clear 2 filters" })).toBeVisible();
  await page.getByRole("button", { name: "Clear 2 filters" }).click();
  await expect(count(page)).toHaveText(new RegExp(`^${TOTAL} jobs`));
  await expect(page).not.toHaveURL(/hours=/);
});

test("'Up to 20 h/week' is hidden while no job states its hours", async ({ page }) => {
  // Serve the built fixture with every hours value removed.
  await page.route("**/jobs.json", async (route) => {
    const res = await route.fetch();
    const data = await res.json();
    for (const j of data.jobs) j.hoursMin = j.hoursMax = null;
    await route.fulfill({ response: res, json: data });
  });
  await openBoard(page);
  await page.getByRole("button", { name: "More filters" }).click();
  const options = page.getByRole("group", { name: "Options" });
  await expect(options.getByRole("button", { name: "Include remote" })).toBeVisible();
  await expect(options.getByRole("button", { name: /^Up to 20 h\/week/ })).toHaveCount(0);
});

test("back and forward restore filters", async ({ page }) => {
  await openBoard(page);
  await typeOption(page, "Thesis").click();
  await expect(page).toHaveURL(/[?&]type=thesis/);

  await savedLink(page).click();
  await expect(page).toHaveURL(/\/saved\/$/);

  await page.goBack();
  await expect(page).toHaveURL(/[?&]type=thesis/);
  await expect(count(page)).toHaveText(new RegExp(`^1 of ${TOTAL} jobs`));

  await page.goForward();
  await expect(page).toHaveURL(/\/saved\/$/);
});

test("opening a job sets ?job= and shows an https Apply link", async ({ page }) => {
  const job = fixture.jobs[0];
  await openBoard(page);
  await row(page, job.title).click();
  await expect(page).toHaveURL(new RegExp(`[?&]job=${job.id}`));
  const apply = page.getByRole("link", { name: "Apply now" });
  await expect(apply).toHaveAttribute("href", job.links[0].url);
  expect(job.links[0].url).toMatch(/^https:\/\//);
});

test("save a job, find it on /saved/, remove it and undo", async ({ page }) => {
  const job = fixture.jobs[1];
  await openBoard(page);
  await expect(savedLink(page)).toContainText("0");
  await row(page, job.title).click();
  await page.getByRole("button", { name: "Save for later" }).click();
  await expect(savedLink(page)).toContainText("1");

  await savedLink(page).click();
  await expect(page).toHaveURL(/\/saved\/$/);
  await expect(page).toHaveTitle("Saved jobs · dresden/jobs");
  await row(page, job.title).click();

  const remove = page.getByRole("button", { name: "Remove from saved" });
  await remove.click();
  // The row stays for this visit; the same button now re-saves it and keeps focus.
  const undo = page.getByRole("button", { name: "Save for later" });
  await expect(undo).toBeFocused();
  await expect(savedLink(page)).toContainText("0");
  await expect(row(page, job.title)).toBeVisible();
  await expect(page.getByText("0 jobs kept for later, stored in this browser only.")).toBeVisible();
  await expect(page.getByText("Jobs you save show up here.", { exact: false })).toHaveCount(0);
  await expect(page.getByRole("status").filter({ hasText: /Removed .+ from saved/ })).toBeAttached();

  await undo.click();
  await expect(page.getByRole("button", { name: "Remove from saved" })).toBeFocused();
  await expect(savedLink(page)).toContainText("1");
  await expect(page.getByRole("status").filter({ hasText: /Saved .+ again/ })).toBeAttached();

  await page.getByRole("button", { name: "Remove from saved" }).click();
  await page.reload();
  await expect(page.getByText("Nothing saved yet")).toBeVisible();
});

test("a saved job that left the data shows as closed", async ({ page }) => {
  const live = fixture.jobs[0]; // has a future deadline
  const gone = {
    ...live,
    id: "e2e-closed-job",
    title: "Werkstudent Closed Position",
    deadline: "2099-12-31",
    links: [{ source: "Example", url: "https://jobs.example.com/closed-position" }],
  };
  await page.addInitScript(
    ([key, value]) => window.localStorage.setItem(key, value),
    [BOOKMARKS, JSON.stringify({ [live.id]: live, [gone.id]: gone })],
  );
  await page.goto("/saved/");

  const closedRow = page.locator("li", { has: row(page, gone.title) });
  await expect(closedRow).toContainText("Closed");
  await row(page, gone.title).click();
  await expect(closedRow).toContainText("This job is no longer available.");
  await expect(closedRow.getByRole("link", { name: "View original posting" })).toHaveAttribute("href", gone.links[0].url);
  await expect(closedRow).not.toContainText("Apply by");

  // The live job still shows its deadline, so the check above means something.
  await row(page, live.title).click();
  await expect(page.locator("li", { has: row(page, live.title) })).toContainText("Apply by");
});

test("?job= for an unknown job shows a notice that Dismiss clears", async ({ page }) => {
  await openBoard(page, "/?job=unknown");
  const notice = page.getByText("This job is no longer available.");
  await expect(notice).toBeVisible();
  await page.getByRole("button", { name: "Dismiss" }).click();
  await expect(notice).toBeHidden();
  await expect(count(page)).toBeFocused();
  await expect(page).not.toHaveURL(/job=/);
});

for (const path of ["/", "/saved/", "/imprint/", "/privacy/"]) {
  test(`no console errors on ${path}`, async ({ page }) => {
    const errors: string[] = [];
    page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
    page.on("pageerror", (e) => errors.push(e.message));
    await page.goto(path);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await page.waitForLoadState("networkidle");
    expect(errors).toEqual([]);
  });

  test(`no horizontal scroll at 375px on ${path}`, async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto(path);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await page.waitForLoadState("networkidle");
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow).toBeLessThanOrEqual(0);
  });
}

test("Copy link copies a ?job= link and confirms it", async ({ page, context, baseURL }) => {
  await context.grantPermissions(["clipboard-read", "clipboard-write"], { origin: baseURL });
  const job = fixture.jobs[2];
  await openBoard(page);
  await row(page, job.title).click();
  await page.getByRole("button", { name: "Copy link" }).click();
  await expect(page.getByRole("button", { name: "Link copied" })).toBeVisible();
  await expect(page.getByRole("status").filter({ hasText: "Link copied" })).toBeAttached();
  const copied = await page.evaluate(() => navigator.clipboard.readText());
  expect(copied).toBe(`${baseURL}/?job=${job.id}`);
});

test("a failed copy says so briefly and gives the full hint to screen readers", async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText: () => Promise.reject(new Error("denied")) },
      configurable: true,
    });
  });
  const job = fixture.jobs[2];
  await openBoard(page);
  await row(page, job.title).click();
  await page.getByRole("button", { name: "Copy link" }).click();
  await expect(page.getByRole("button", { name: "Copy failed" })).toBeVisible();
  await expect(page.getByRole("status").filter({ hasText: "Couldn't copy, use the address bar" })).toBeAttached();
});

test("a first visit shows this week's new jobs", async ({ page }) => {
  await openBoard(page);
  await expect(page.getByRole("paragraph").filter({ hasText: /^Fresh this week$/ })).toBeVisible();
  await expect(page.getByText("Welcome back")).toHaveCount(0);
  await page.getByRole("button", { name: "Show only new →" }).click();
  await expect(page).toHaveURL(/[?&]new=1/);
  await expect(count(page)).toHaveText(new RegExp(`^1 of ${TOTAL} jobs`));
});

test("a returning visit shows what's new since then and filters to it", async ({ page }) => {
  // e2e/build.mjs sets the first job's firstSeen to today; the others are months old.
  // The stored record says the last visit was three days ago and the newest job then was
  // from that day, so this load rolls it forward and shows the job from today as new.
  const at = new Date(Date.now() - 3 * 86_400_000).toISOString();
  const day = at.slice(0, 10);
  const record = JSON.stringify({ seen: null, seenAt: at, next: day, nextAt: at });
  await page.addInitScript(
    ([key, value]) => {
      if (sessionStorage.getItem("e2e-seeded")) return; // seed once, not on reload
      localStorage.setItem(key, value);
      sessionStorage.setItem("e2e-seeded", "1");
    },
    ["dsj:lastVisit", record],
  );
  await openBoard(page);
  await expect(page.getByText("Welcome back")).toBeVisible();
  await expect(page.getByText(/^Since \w+day$/)).toBeVisible();
  // The ticket already offers "new"; the week filter would compete with it.
  await page.getByRole("button", { name: "More filters" }).click();
  await expect(page.getByRole("group", { name: "Options" }).getByRole("button", { name: "Fresh this week" })).toHaveCount(0);
  await page.getByRole("button", { name: "Show only new →" }).click();
  await expect(page).toHaveURL(/[?&]since=\d{4}-\d{2}-\d{2}/);
  await expect(count(page)).toHaveText(new RegExp(`^1 of ${TOTAL} jobs`));
  await expect(page.getByRole("button", { name: "Show all →" })).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByRole("button", { name: "Clear 1 filter" })).toBeVisible();

  // A reload within 30 minutes is the same visit: the record isn't rolled again.
  await page.reload();
  await expect(page.getByText("Welcome back")).toBeVisible();
  await expect(count(page)).toHaveText(new RegExp(`^1 of ${TOTAL} jobs`));
});

test("when every job is new since the last visit, the board falls back to the 7-day view", async ({ page }) => {
  // The newest job on the last visit is older than every job in the fixture.
  const at = new Date(Date.now() - 3 * 86_400_000).toISOString();
  const record = JSON.stringify({ seen: "2000-01-01", seenAt: at, next: "2000-01-01", nextAt: at });
  await page.addInitScript(([key, value]) => localStorage.setItem(key, value), ["dsj:lastVisit", record]);
  await page.setViewportSize({ width: 375, height: 812 }); // the per-row "New ·" label is in the phone line
  await openBoard(page);
  await expect(count(page)).toHaveText(new RegExp(`^${TOTAL} jobs`));
  // No "since" view that would highlight everything; the normal 7-day ticket instead,
  // which in this fixture has exactly one job first seen today.
  await expect(page.getByText("Welcome back")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Show only new →" })).toBeVisible();
  await expect(page.locator('li[id^="row-"]').filter({ hasText: "New · " })).toHaveCount(1);
});

test("an impossible ?since= date is ignored instead of crashing the board", async ({ page }) => {
  const errors: string[] = [];
  page.on("console", (m) => {
    if (m.type() === "error") errors.push(m.text());
  });
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/?since=2020-13-45");
  await expect(count(page)).toHaveText(new RegExp(`^${TOTAL} jobs`));
  expect(errors).toEqual([]);
});

test("the footer links to the imprint and privacy pages", async ({ page }) => {
  await openBoard(page);
  const legal = page.getByRole("navigation", { name: "Legal" });
  await legal.getByRole("link", { name: "Imprint" }).click();
  await expect(page).toHaveURL(/\/imprint\/$/);
  await expect(page).toHaveTitle("Imprint · dresden/jobs");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Who runs this board.");

  await legal.getByRole("link", { name: "Privacy" }).click();
  await expect(page).toHaveURL(/\/privacy\/$/);
  await expect(page).toHaveTitle("Privacy · dresden/jobs");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Your privacy.");
});
