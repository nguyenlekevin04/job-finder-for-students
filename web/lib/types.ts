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
}

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
