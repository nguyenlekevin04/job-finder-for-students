import type { NextConfig } from "next";

// On GitHub Pages the site lives at /<repo-name>. The deploy workflow sets
// NEXT_BASE_PATH; locally it's empty so the site runs at "/".
const basePath = process.env.NEXT_BASE_PATH || "";

const nextConfig: NextConfig = {
  output: "export", // plain static files in ./out
  basePath,
  trailingSlash: true, // /saved -> /saved/index.html (works on GitHub Pages)
  images: { unoptimized: true },
  env: { NEXT_PUBLIC_BASE_PATH: basePath },
  // Note: cacheComponents / partialPrefetching (PPR) can't be used with output: "export".
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
