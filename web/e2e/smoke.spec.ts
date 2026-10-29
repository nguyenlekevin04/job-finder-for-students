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

  await undo.click();
  await expect(page.getByRole("button", { name: "Remove from saved" })).toBeFocused();
  await expect(savedLink(page)).toContainText("1");

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

for (const path of ["/", "/saved/"]) {
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
