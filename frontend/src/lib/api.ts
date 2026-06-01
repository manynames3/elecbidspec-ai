export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: init?.body instanceof FormData ? init.headers : { "Content-Type": "application/json", ...init?.headers },
    cache: "no-store"
  });
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed with ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function formatCurrency(value: number | string | null | undefined): string {
  if (value === null || value === undefined || value === "") {
    return "Not posted";
  }
  const numeric = typeof value === "string" ? Number(value) : value;
  if (Number.isNaN(numeric)) {
    return String(value);
  }
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0
  }).format(numeric);
}

export function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "No due date";
  }
  return new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", year: "numeric" }).format(new Date(`${value}T00:00:00`));
}

export function labelize(value: string | null | undefined): string {
  if (!value) {
    return "Unknown";
  }
  return value.replaceAll("_", " ");
}

