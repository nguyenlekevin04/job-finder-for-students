export type JobType = "werkstudent" | "internship" | "thesis";
export type Field = "ai" | "data" | "software" | "hardware" | "other";

export interface JobLink {
  source: string;
  url: string;
}

export interface Job {
  id: string;
  title: string;
  company: string;
  location: string;
  remote: boolean;
  type: JobType;
  types: JobType[];
  fields: Field[];
  englishFriendly: boolean;
  postedAt: string | null;
  deadline: string | null;
  firstSeen: string;
  lastSeen: string;
  links: JobLink[];
  snippet: string;
  // Only when the posting states them; null otherwise. A single value has min === max,
  // "max. 20 h" has only hoursMax, "mind. 10 h" only hoursMin.
  hoursMin?: number | null;
  hoursMax?: number | null;
  payAmount?: number | null; // EUR, as stated
  payUnit?: "hour" | "month" | null;
  germanLevel?: GermanLevel | null; // as the posting states it; null = not stated
  city?: City | ""; // "" for remote-only postings; missing in data saved before cities = Dresden
}

export const CITIES = ["dresden", "leipzig", "chemnitz", "berlin"] as const;
export type City = (typeof CITIES)[number];
export const CITY_LABELS: Record<City, string> = { dresden: "Dresden", leipzig: "Leipzig", chemnitz: "Chemnitz", berlin: "Berlin" };

/** "none" = no German needed, "basic" = B1–B2, "fluent" = C1 or better. */
export type GermanLevel = "none" | "basic" | "fluent";
export const GERMAN_LABELS: Record<GermanLevel, string> = {
  none: "English OK",
  basic: "German B1–B2",
  fluent: "German C1+",
};

/** Job boards that list other companies' jobs; every other source is the employer itself. */
export const AGGREGATORS = ["Arbeitsagentur", "Arbeitnow"];

export interface SourceStatus {
  ok: boolean;
  count: number;
  skipped?: boolean;
  error?: string;
  rejected?: number; // postings skipped for a link outside the source's allowed hosts
}

export interface JobsFile {
  generatedAt: string | null; // null until the first fetch has run
  count: number;
  sources: Record<string, SourceStatus>;
  jobs: Job[];
}

export const TYPE_LABELS: Record<JobType, string> = {
  werkstudent: "Werkstudent",
  internship: "Internship",
  thesis: "Thesis",
};

export const FIELD_LABELS: Record<Field, string> = {
  ai: "AI / ML",
  data: "Data",
  software: "Software",
  hardware: "Embedded / HW",
  other: "Other CS",
};

export const ALL_TYPES = Object.keys(TYPE_LABELS) as JobType[];
export const ALL_FIELDS = Object.keys(FIELD_LABELS) as Field[];
