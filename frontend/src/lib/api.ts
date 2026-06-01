export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";
export const AUTH_TOKEN_STORAGE_KEY = "elecbidspec_auth_token";

export function getAuthToken(): string {
  if (typeof window === "undefined") {
    return "";
  }
  return window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY) ?? "";
}

export function setAuthToken(token: string): void {
  window.localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, token);
}

export function clearAuthToken(): void {
  window.localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
}

export function authHeaders(): Record<string, string> {
  const token = getAuthToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function requestHeaders(init: RequestInit | undefined, isFormData: boolean): Headers {
  const headers = new Headers(init?.headers);
  Object.entries(authHeaders()).forEach(([key, value]) => headers.set(key, value));
  if (!isFormData && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  return headers;
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const isFormData = init?.body instanceof FormData;
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: requestHeaders(init, isFormData),
    cache: "no-store"
  });
  if (!response.ok) {
    if (response.status === 401 && typeof window !== "undefined") {
      clearAuthToken();
    }
    const message = await response.text();
    throw new Error(message || `Request failed with ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function apiUrl(path: string): string {
  return `${API_URL}${path}`;
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

export function sourceLabel(source: string): string {
  if (source === "txdot_bid_items") {
    return "TxDOT";
  }
  if (source === "nypa") {
    return "NY Power Authority";
  }
  if (source === "pa_emarketplace") {
    return "PA eMarketplace";
  }
  if (source === "ca_dot") {
    return "Caltrans";
  }
  if (source === "fl_dot") {
    return "FDOT";
  }
  if (source === "ny_dot") {
    return "NYSDOT";
  }
  if (source === "ga_dot") {
    return "GDOT";
  }
  if (source === "il_dot") {
    return "IDOT";
  }
  if (source === "oh_dot") {
    return "ODOT";
  }
  if (source === "nc_evp") {
    return "NC eVP";
  }
  if (source === "va_dot") {
    return "VDOT";
  }
  if (source === "az_dot") {
    return "ADOT";
  }
  if (source === "tva_procurement") {
    return "TVA";
  }
  if (source === "bpa_procurement") {
    return "BPA";
  }
  if (source === "ladwp") {
    return "LADWP";
  }
  if (source === "austin_energy") {
    return "Austin Energy";
  }
  if (source === "cps_energy") {
    return "CPS Energy";
  }
  if (source === "jea") {
    return "JEA";
  }
  if (source === "srp") {
    return "SRP";
  }
  if (source === "port_authority_ny_nj") {
    return "Port Authority NY/NJ";
  }
  if (source === "la_metro") {
    return "LA Metro";
  }
  if (source === "septa") {
    return "SEPTA";
  }
  if (source === "ny_mta") {
    return "MTA";
  }
  if (source === "dfw_airport") {
    return "DFW Airport";
  }
  if (source === "uc_procurement") {
    return "University of California";
  }
  if (source === "houston_water") {
    return "Houston Public Works";
  }
  if (source === "chicago_solicitations") {
    return "Chicago/CTA";
  }
  if (source === "la_ramp") {
    return "Los Angeles RAMP";
  }
  if (source === "montgomery_md_solicitations") {
    return "Montgomery County";
  }
  if (source === "nyc_city_record") {
    return "NYC City Record";
  }
  if (source === "nyc_school_construction_authority") {
    return "NYC School Construction";
  }
  if (source === "sf_open_bids") {
    return "San Francisco";
  }
  if (source === "sam_gov") {
    return "SAM.gov";
  }
  if (source === "seed") {
    return "Sample";
  }
  return labelize(source);
}
