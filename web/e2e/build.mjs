// Builds the static export the smoke tests run against (`npm run test:e2e`).
//
// - Copies e2e/fixtures/jobs.json to public/jobs.json (git-ignored; this replaces
//   any local fetcher output there). The first job's firstSeen is set to today, so
//   the "new" features always have exactly one new job, however old the fixture is.
// - Builds with the Supabase and deploy-env variables set to empty strings, so the
//   site reads jobs.json and shows no staging banner. Empty, not deleted: Next.js
//   would otherwise fill them from web/.env.local, and it never overrides a
//   variable that is already set.
//
// Browsers are installed once with `npx playwright install --with-deps chromium`
// (in CI; locally `npx playwright install chromium` is enough).
import { spawnSync } from "node:child_process";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const web = join(dirname(fileURLToPath(import.meta.url)), "..");
mkdirSync(join(web, "public"), { recursive: true }); // absent in a fresh checkout
const data = JSON.parse(readFileSync(join(web, "e2e/fixtures/jobs.json"), "utf8"));
const now = new Date();
const today = [now.getFullYear(), now.getMonth() + 1, now.getDate()].map((n) => String(n).padStart(2, "0")).join("-");
data.jobs[0].firstSeen = today; // local date, the way the site compares it
data.jobs[0].lastSeen = today;
writeFileSync(join(web, "public/jobs.json"), JSON.stringify(data, null, 2));

const env = {
  ...process.env,
  NEXT_PUBLIC_SUPABASE_URL: "",
  NEXT_PUBLIC_SUPABASE_ANON_KEY: "",
  NEXT_PUBLIC_DEPLOY_ENV: "",
  NEXT_BASE_PATH: "",
};
const res = spawnSync("npx", ["next", "build"], { cwd: web, env, stdio: "inherit", shell: process.platform === "win32" });
process.exit(res.status ?? 1);
