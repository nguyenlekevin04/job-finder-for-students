// After `next build`: give every exported page a strict Content-Security-Policy.
//
// Static export can't send per-page headers, and Next.js inlines different scripts on
// each page, so the policy goes into a <meta http-equiv> tag at the top of <head> with
// a sha256 hash for every inline script on that page. Only our own files and those
// hashes may run; the browser may only talk to us, Supabase and Umami's gateway.
// frame-ancestors can't be set by a meta tag; it stays in the header (vercel.json).
import { createHash } from "node:crypto";
import { readdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import nextEnv from "@next/env";

const web = join(dirname(fileURLToPath(import.meta.url)), "..");
const out = join(web, "out");
nextEnv.loadEnvConfig(web); // the same .env files `next build` read; real env vars still win

const origin = (url) => {
  try {
    return url ? new URL(url).origin : "";
  } catch {
    return "";
  }
};
// Vercel's toolbar (comments, preview feedback) is injected on preview deployments only.
const preview = process.env.NEXT_PUBLIC_DEPLOY_ENV === "staging" ? "https://vercel.live" : "";
const connect = [
  "'self'",
  origin(process.env.NEXT_PUBLIC_SUPABASE_URL),
  process.env.NEXT_PUBLIC_UMAMI_WEBSITE_ID?.trim() ? "https://gateway.umami.is" : "",
  preview,
].filter(Boolean);

const INLINE = /<script(?![^>]*\ssrc=)[^>]*>([\s\S]*?)<\/script>/g;

export function policy(html) {
  const hashes = [...html.matchAll(INLINE)]
    .filter((m) => m[1].length) // empty inline scripts run nothing
    .map((m) => `'sha256-${createHash("sha256").update(m[1], "utf8").digest("base64")}'`);
  return [
    "default-src 'self'",
    `script-src 'self' ${preview} ${[...new Set(hashes)].join(" ")}`.replace(/ +/g, " ").trim(),
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data:",
    "font-src 'self'",
    `connect-src ${connect.join(" ")}`,
    ...(preview ? [`frame-src ${preview}`] : []),
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
  ].join("; ");
}

export function withPolicy(html) {
  if (html.includes('http-equiv="Content-Security-Policy"')) return html;
  const tag = `<meta http-equiv="Content-Security-Policy" content="${policy(html)}"/>`;
  // Right after the charset meta, so it comes before every script.
  return html.replace(/(<head>(?:<meta charSet="utf-8"\/>)?)/i, `$1${tag}`);
}

function* pages(dir) {
  for (const e of readdirSync(dir, { withFileTypes: true })) {
    const p = join(dir, e.name);
    if (e.isDirectory()) yield* pages(p);
    else if (e.name.endsWith(".html")) yield p;
  }
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  let n = 0;
  for (const file of pages(out)) {
    const html = readFileSync(file, "utf8");
    if (html.includes('http-equiv="Content-Security-Policy"')) continue; // already done
    const next = withPolicy(html);
    if (next === html) throw new Error(`csp: no <head> in ${file}`);
    writeFileSync(file, next);
    n++;
  }
  console.log(`csp: policy added to ${n} pages (connect-src ${connect.join(" ")})`);
}
