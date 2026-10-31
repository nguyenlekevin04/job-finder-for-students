// Builds the static export the smoke tests run against (`npm run test:e2e`), with the same
// `npm run build` as Vercel, so the pages carry their Content-Security-Policy.
//
// - Copies e2e/fixtures/jobs.json to public/jobs.json for the build and puts any
//   existing local fetcher output back afterwards. The first job's firstSeen is set to today, so
//   the "new" features always have exactly one new job, however old the fixture is.
// - Builds with the Supabase and deploy-env variables set to empty strings, so the
//   site reads jobs.json and shows no staging banner. Empty, not deleted: Next.js
//   would otherwise fill them from web/.env.local, and it never overrides a
//   variable that is already set.
//
// Browsers are installed once with `npx playwright install --with-deps chromium`
// (in CI; locally `npx playwright install chromium` is enough).
import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, renameSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const web = join(dirname(fileURLToPath(import.meta.url)), "..");
mkdirSync(join(web, "public"), { recursive: true }); // absent in a fresh checkout
const data = JSON.parse(readFileSync(join(web, "e2e/fixtures/jobs.json"), "utf8"));
const now = new Date();
const today = [now.getFullYear(), now.getMonth() + 1, now.getDate()].map((n) => String(n).padStart(2, "0")).join("-");
data.jobs[0].firstSeen = today; // local date, the way the site compares it
data.jobs[0].lastSeen = today;
const target = join(web, "public/jobs.json");
const backup = join(web, ".jobs.json.e2e-backup"); // outside public/, so it is never exported
const hadData = existsSync(target);
if (hadData) renameSync(target, backup); // keep the developer's real data
writeFileSync(target, JSON.stringify(data, null, 2));

const env = {
  ...process.env,
  NEXT_PUBLIC_SUPABASE_URL: "",
  NEXT_PUBLIC_SUPABASE_ANON_KEY: "",
  NEXT_PUBLIC_DEPLOY_ENV: "",
  NEXT_BASE_PATH: "",
};
const res = spawnSync("npm", ["run", "build"], { cwd: web, env, stdio: "inherit", shell: process.platform === "win32" });
if (hadData) renameSync(backup, target); // the export in out/ already holds the fixture
process.exit(res.status ?? 1);
