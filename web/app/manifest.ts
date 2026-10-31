import type { MetadataRoute } from "next";

// Lets students add the board to their phone's home screen ("Install app" / "Add to Home Screen").
// Static: exported as /manifest.webmanifest at build time.
export const dynamic = "force-static";

export default function manifest(): MetadataRoute.Manifest {
  const base = process.env.NEXT_PUBLIC_BASE_PATH ?? "";
  return {
    name: "dresden/jobs · Student tech jobs in Dresden",
    short_name: "dresden/jobs",
    description: "Werkstudent, internship and thesis positions in AI, data and software around Dresden, updated daily.",
    start_url: `${base}/`,
    scope: `${base}/`,
    display: "standalone",
    background_color: "#f8f5ee",
    theme_color: "#252523",
    icons: [
      { src: `${base}/icon-192.png`, sizes: "192x192", type: "image/png" },
      { src: `${base}/icon-512.png`, sizes: "512x512", type: "image/png", purpose: "any" },
    ],
  };
}
