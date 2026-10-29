// Builds the static export the smoke tests run against (`npm run test:e2e`).
//
// - Copies e2e/fixtures/jobs.json to public/jobs.json (git-ignored; this replaces
//   any local fetcher output there).
// - Builds with the Supabase and deploy-env variables set to empty strings, so the
//   site reads jobs.json and shows no staging banner. Empty, not deleted: Next.js
//   would otherwise fill them from web/.env.local, and it never overrides a
//   variable that is already set.
//
// Browsers are installed once with `npx playwright install --with-deps chromium`
// (in CI; locally `npx playwright install chromium` is enough).
import { spawnSync } from "node:child_process";
import { copyFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const web = join(dirname(fileURLToPath(import.meta.url)), "..");
mkdirSync(join(web, "public"), { recursive: true }); // absent in a fresh checkout
copyFileSync(join(web, "e2e/fixtures/jobs.json"), join(web, "public/jobs.json"));

const env = {
  ...process.env,
  NEXT_PUBLIC_SUPABASE_URL: "",
  NEXT_PUBLIC_SUPABASE_ANON_KEY: "",
  NEXT_PUBLIC_DEPLOY_ENV: "",
  NEXT_BASE_PATH: "",
};
const res = spawnSync("npx", ["next", "build"], { cwd: web, env, stdio: "inherit", shell: process.platform === "win32" });
process.exit(res.status ?? 1);
