// Who runs the site, for the imprint (§ 5 DDG / § 18 Abs. 2 MStV) and the privacy page.
// The real values live in Vercel environment variables (set per environment), never in
// this public repo: NEXT_PUBLIC_OPERATOR_NAME, _STREET, _CITY, _EMAIL. They're inlined at
// build time, so redeploy after changing them. While any is missing, both pages show
// placeholders and a visible draft warning.
const env = {
  name: process.env.NEXT_PUBLIC_OPERATOR_NAME,
  street: process.env.NEXT_PUBLIC_OPERATOR_STREET,
  city: process.env.NEXT_PUBLIC_OPERATOR_CITY,
  email: process.env.NEXT_PUBLIC_OPERATOR_EMAIL,
};

export const LEGAL_PLACEHOLDERS = !Object.values(env).every((v) => v && v.trim());

export const OPERATOR = {
  name: env.name?.trim() || "[Name]",
  street: env.street?.trim() || "[Street and number]",
  city: env.city?.trim() || "[Postcode] Dresden",
  email: env.email?.trim() || "[email@example.com]",
} as const;
