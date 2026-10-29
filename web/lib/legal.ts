// Who runs the site, for the imprint (§ 5 DDG / § 18 Abs. 2 MStV) and the privacy page.
// The one place for this data: fill in the real values and set LEGAL_PLACEHOLDERS to
// false before release. While it's true, both pages show a visible warning.
export const OPERATOR = {
  name: "[Name]",
  street: "[Street and number]",
  city: "[Postcode] Dresden",
  email: "[email@example.com]",
} as const;

export const LEGAL_PLACEHOLDERS = true;
