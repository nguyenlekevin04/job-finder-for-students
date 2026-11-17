// Small one-value settings in localStorage ("done", a date). Every access is in try/catch;
// when storage is blocked the value lives in memory for this page load, so nothing nags twice.
const memory = new Map<string, string>();

export function getPref(key: string): string | null {
  try {
    const v = window.localStorage.getItem(key);
    if (v !== null) return v;
  } catch {
    // blocked storage: fall back to memory
  }
  return memory.get(key) ?? null;
}

export function setPref(key: string, value: string): void {
  memory.set(key, value);
  try {
    window.localStorage.setItem(key, value);
  } catch {
    // kept in memory only
  }
}

/** True when the stored "YYYY-MM-DD" is less than `days` days before today. */
export function within(stored: string | null, days: number, now = new Date()): boolean {
  if (!stored || !/^\d{4}-\d{2}-\d{2}$/.test(stored)) return false;
  const age = (now.getTime() - Date.parse(`${stored}T00:00:00Z`)) / 86_400_000;
  return age >= 0 && age < days;
}
