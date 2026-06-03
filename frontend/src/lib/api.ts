import type { Opportunity } from "@/lib/types";

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
    const rawMessage = await response.text();
    let message = rawMessage;
    try {
      const parsed = JSON.parse(rawMessage) as { detail?: unknown };
      if (typeof parsed.detail === "string") {
        message = parsed.detail;
      }
    } catch {
      message = rawMessage;
    }
    throw new Error(message || `Request failed with ${response.status}`);
  }
  if (response.status === 204) {
    return undefined as T;
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
    return "Ohio DOT";
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
  if (source === "pjm_project_construction") {
    return "PJM Construction";
  }
  if (source === "caiso_interconnection_queue") {
    return "CAISO Queue";
  }
  if (source === "ercot_capacity_changes") {
    return "ERCOT Planned Capacity";
  }
  if (source === "iso_ne_interconnection_queue") {
    return "ISO-NE Queue";
  }
  if (source === "miso_eras_interconnection") {
    return "MISO ERAS";
  }
  if (source === "nyiso_interconnection_queue") {
    return "NYISO Queue";
  }
  if (source === "spp_gi_active_requests") {
    return "SPP GI Active";
  }
  if (source === "virginia_scc_transmission_cases") {
    return "Virginia SCC";
  }
  if (source === "georgia_psc_data_center") {
    return "Georgia PSC";
  }
  if (source === "texas_puc_dockets") {
    return "Texas PUCT";
  }
  if (source === "loudoun_land_applications") {
    return "Loudoun Land Use";
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

export function whyThisBidMatters(opportunity: Opportunity): string {
  const reasons: string[] = [];
  if (opportunity.project_stage === "early_signal") {
    reasons.push("early signal before RFP");
  } else if (opportunity.project_stage === "pre_rfp") {
    reasons.push("pre-RFP pursuit window");
  }
  if (opportunity.owner_type === "investor_owned_utility") {
    reasons.push("investor-owned utility / AVL timing");
  }
  if (opportunity.signal_type) {
    reasons.push(labelize(opportunity.signal_type));
  }
  if (opportunity.minimum_value_match) {
    reasons.push(opportunity.estimated_value ? `${formatCurrency(opportunity.estimated_value)} posted or inferred` : "$5M+ target likely");
  }
  if ((opportunity.fit_score ?? 0) >= 75) {
    reasons.push(`${opportunity.fit_score} fit for company capabilities`);
  } else if ((opportunity.fit_score ?? 0) >= 55) {
    reasons.push("worth review against profile gaps");
  }
  if (opportunity.project_type && opportunity.project_type !== "general_electrical") {
    reasons.push(labelize(opportunity.project_type));
  }
  const keywords = opportunity.extracted_specs?.keywords ?? [];
  const strategicKeyword = keywords.find((keyword) =>
    [
      "underground cable",
      "medium voltage",
      "high voltage",
      "substation",
      "data center",
      "hyperscale",
      "ai infrastructure",
      "critical power",
      "gpu",
      "ups",
      "switchgear",
      "transmission",
      "distribution",
      "transformer"
    ].includes(keyword)
  );
  if (strategicKeyword) {
    reasons.push(`${strategicKeyword} scope`);
  }
  if (opportunity.source !== "seed") {
    reasons.push(`official ${labelize(opportunity.source_type)} source`);
  }
  if (!reasons.length && opportunity.fit_explanation) {
    return opportunity.fit_explanation;
  }
  return reasons.length ? reasons.slice(0, 5).join(" · ") : "Needs review: value, scope, and fit are not fully established yet.";
}
