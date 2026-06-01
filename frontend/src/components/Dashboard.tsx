"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Bell, DatabaseZap, Filter, RefreshCw, Save, Search } from "lucide-react";
import { apiFetch, authHeaders, getAuthToken, sourceLabel } from "@/lib/api";
import type { AlertPreference, AlertRun, IngestionRefreshResult, IngestionSummary, Opportunity, SearchResult } from "@/lib/types";
import { OpportunityCard } from "@/components/OpportunityCard";

const adminTokenStorageKey = "elecbidspec_admin_token";

const projectTypes = [
  "data_center_power",
  "utility_replacement",
  "fire_damage_rebuild",
  "underground_installation",
  "pole_overhead_installation",
  "substation_related",
  "general_electrical"
];

const sourceFilterOptions = [
  "seed",
  "manual_upload",
  "sam_gov",
  "chicago_solicitations",
  "la_ramp",
  "montgomery_md_solicitations",
  "nypa",
  "nyc_city_record",
  "nyc_school_construction_authority",
  "pa_emarketplace",
  "sf_open_bids",
  "txdot_bid_items",
  "ca_dot",
  "fl_dot",
  "ny_dot",
  "ga_dot",
  "il_dot",
  "oh_dot",
  "nc_evp",
  "va_dot",
  "az_dot",
  "tva_procurement",
  "bpa_procurement",
  "ladwp",
  "austin_energy",
  "cps_energy",
  "jea",
  "srp",
  "port_authority_ny_nj",
  "la_metro",
  "septa",
  "ny_mta",
  "dfw_airport",
  "uc_procurement",
  "houston_water"
];

type Filters = {
  due_before: string;
  state: string;
  project_type: string;
  min_fit_score: string;
  min_value: string;
  minimum_value_match: string;
  source_type: string;
  bid_status: string;
  source: string;
  open_only: string;
  real_only: string;
  saved_only: string;
  watched_only: string;
  include_hidden: string;
};

const emptyFilters: Filters = {
  due_before: "",
  state: "",
  project_type: "",
  min_fit_score: "",
  min_value: "",
  minimum_value_match: "true",
  source_type: "",
  bid_status: "open",
  source: "",
  open_only: "true",
  real_only: "true",
  saved_only: "",
  watched_only: "",
  include_hidden: ""
};

export function Dashboard() {
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [searchResults, setSearchResults] = useState<SearchResult[] | null>(null);
  const [filters, setFilters] = useState<Filters>(emptyFilters);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshingSources, setRefreshingSources] = useState(false);
  const [ingestionSummary, setIngestionSummary] = useState<IngestionSummary | null>(null);
  const [alertPreference, setAlertPreference] = useState<AlertPreference | null>(null);
  const [alertRun, setAlertRun] = useState<AlertRun | null>(null);
  const [alertForm, setAlertForm] = useState({ email_to: "", min_fit_score: "70", due_within_days: "30", enabled: true, include_source_failures: true });
  const [alertLoading, setAlertLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sourceMessage, setSourceMessage] = useState<string | null>(null);
  const [alertMessage, setAlertMessage] = useState<string | null>(null);
  const [adminToken, setAdminToken] = useState("");

  const visibleCount = searchResults ? searchResults.length : opportunities.length;
  const latestPublicRefresh = ingestionSummary?.latest_jobs.find((job) => job.adapter !== "sam_gov");
  const sourceHealth = ingestionSummary?.source_health ?? [];
  const publicSourceCount = sourceHealth.length || ingestionSummary?.sources.filter((source) => source.source !== "seed" && source.source !== "manual_upload").length || 0;
  const healthySourceCount = sourceHealth.filter((source) => source.status === "healthy").length;
  const alertCounts = alertRun?.digest.counts;
  const averageFit = useMemo(() => {
    const scores = opportunities.map((item) => item.fit_score).filter((score): score is number => score !== null);
    if (!scores.length) {
      return "--";
    }
    return Math.round(scores.reduce((sum, score) => sum + score, 0) / scores.length);
  }, [opportunities]);

  function opportunityPath(nextFilters: Filters) {
    const params = new URLSearchParams();
    Object.entries(nextFilters).forEach(([key, value]) => {
      if (value) {
        params.set(key, value);
      }
    });
    return params.size ? `/opportunities?${params.toString()}` : "/opportunities";
  }

  async function loadOpportunities(nextFilters = filters) {
    setLoading(true);
    setError(null);
    try {
      let activeFilters = nextFilters;
      let [loadedOpportunities, loadedSummary] = await Promise.all([
        apiFetch<Opportunity[]>(opportunityPath(activeFilters)),
        apiFetch<IngestionSummary>("/ingestion/summary")
      ]);
      if (activeFilters.real_only && !loadedOpportunities.length && loadedSummary.real_opportunity_count === 0) {
        activeFilters = { ...activeFilters, real_only: "" };
        loadedOpportunities = await apiFetch<Opportunity[]>(opportunityPath(activeFilters));
        setFilters(activeFilters);
      }
      setOpportunities(loadedOpportunities);
      setIngestionSummary(loadedSummary);
      setSearchResults(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load opportunities");
    } finally {
      setLoading(false);
    }
  }

  async function loadAlerts() {
    try {
      const preference = await apiFetch<AlertPreference>("/alerts/preferences");
      setAlertPreference(preference);
      setAlertForm({
        email_to: preference.email_to ?? "",
        min_fit_score: String(preference.min_fit_score),
        due_within_days: String(preference.due_within_days),
        enabled: preference.enabled,
        include_source_failures: preference.include_source_failures
      });
      try {
        setAlertRun(await apiFetch<AlertRun>("/alerts/latest"));
      } catch {
        setAlertRun(null);
      }
    } catch {
      setAlertPreference(null);
    }
  }

  useEffect(() => {
    setAdminToken(window.localStorage.getItem(adminTokenStorageKey) ?? "");
    void loadOpportunities(emptyFilters);
    void loadAlerts();
  }, []);

  function adminHeaders() {
    if (getAuthToken()) {
      return authHeaders();
    }
    let token = adminToken || window.localStorage.getItem(adminTokenStorageKey) || "";
    if (!token) {
      token = window.prompt("Enter the admin refresh token")?.trim() ?? "";
    }
    if (token) {
      window.localStorage.setItem(adminTokenStorageKey, token);
      setAdminToken(token);
    }
    return token ? { Authorization: `Bearer ${token}` } : null;
  }

  function forgetAdminToken() {
    window.localStorage.removeItem(adminTokenStorageKey);
    setAdminToken("");
    setSourceMessage("Admin token cleared for this browser.");
  }

  async function handleFilter(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await loadOpportunities(filters);
  }

  async function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!query.trim()) {
      await loadOpportunities(filters);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      setSearchResults(
        await apiFetch<SearchResult[]>("/search", {
          method: "POST",
          body: JSON.stringify({ query })
        })
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setLoading(false);
    }
  }

  async function refreshPublicSources() {
    setRefreshingSources(true);
    setError(null);
    setSourceMessage(null);
    try {
      const headers = adminHeaders();
      if (!headers) {
        throw new Error("Admin token required to refresh public sources.");
      }
      const result = await apiFetch<IngestionRefreshResult>("/ingestion/refresh-defaults", { method: "POST", headers });
      const imported = result.jobs.reduce((sum, job) => sum + Number(job.result.imported ?? 0), 0);
      const updated = result.jobs.reduce((sum, job) => sum + Number(job.result.updated ?? 0), 0);
      const queued = result.jobs.reduce((sum, job) => sum + Number(job.result.queued ?? 0), 0);
      const failed = result.jobs.filter((job) => job.status === "failed").length;
      const skipped = result.jobs.filter((job) => job.status === "skipped").length;
      setSourceMessage(`Public sources refreshed: ${imported} imported, ${updated} updated${queued ? `, ${queued} queued` : ""}${failed ? `, ${failed} failed` : ""}${skipped ? `, ${skipped} skipped` : ""}.`);
      await loadOpportunities(filters);
    } catch (err) {
      if (err instanceof Error && err.message.includes("401")) {
        window.localStorage.removeItem(adminTokenStorageKey);
        setAdminToken("");
      }
      setError(err instanceof Error ? err.message : "Unable to refresh public sources");
    } finally {
      setRefreshingSources(false);
    }
  }

  async function saveAlertPreferences() {
    setAlertLoading(true);
    setAlertMessage(null);
    setError(null);
    try {
      const saved = await apiFetch<AlertPreference>("/alerts/preferences", {
        method: "PUT",
        body: JSON.stringify({
          email_to: alertForm.email_to || null,
          min_fit_score: Number(alertForm.min_fit_score || 70),
          due_within_days: Number(alertForm.due_within_days || 30),
          enabled: alertForm.enabled,
          include_source_failures: alertForm.include_source_failures
        })
      });
      setAlertPreference(saved);
      setAlertMessage("Alert preferences saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save alert preferences");
    } finally {
      setAlertLoading(false);
    }
  }

  async function runAlertDigest() {
    setAlertLoading(true);
    setAlertMessage(null);
    setError(null);
    try {
      setAlertRun(await apiFetch<AlertRun>("/alerts/run", { method: "POST" }));
      setAlertMessage("Alert digest generated.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to generate alert digest");
    } finally {
      setAlertLoading(false);
    }
  }

  return (
    <div className="page-stack">
      <section className="page-header">
        <div>
          <p className="eyebrow">Bid intelligence workspace</p>
          <h1>Open public bids over $5M</h1>
        </div>
        <div className="summary-strip">
          <div>
            <span className="field-label">Loaded bids</span>
            <strong>{opportunities.length}</strong>
          </div>
          <div>
            <span className="field-label">Visible</span>
            <strong>{visibleCount}</strong>
          </div>
          <div>
            <span className="field-label">Avg fit</span>
            <strong>{averageFit}</strong>
          </div>
        </div>
      </section>

      <section className="toolbar-band">
        <div className="source-health">
          <div className="source-card">
            <span className="field-label">Official sources</span>
            <strong>{publicSourceCount || "--"}</strong>
          </div>
          <div className="source-card">
            <span className="field-label">Healthy sources</span>
            <strong>{sourceHealth.length ? `${healthySourceCount}/${sourceHealth.length}` : "--"}</strong>
          </div>
          <div className="source-card">
            <span className="field-label">Real records</span>
            <strong>{ingestionSummary?.real_opportunity_count ?? "--"}</strong>
          </div>
          <div className="source-card">
            <span className="field-label">Real target matches</span>
            <strong>{ingestionSummary?.real_target_match_count ?? "--"}</strong>
          </div>
          <div className="source-card">
            <span className="field-label">Last public refresh</span>
            <strong>{latestPublicRefresh ? new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }).format(new Date(latestPublicRefresh.updated_at)) : "--"}</strong>
          </div>
          <button className="secondary-button" type="button" onClick={() => void refreshPublicSources()} disabled={refreshingSources}>
            <DatabaseZap size={17} />
            {refreshingSources ? "Refreshing" : "Admin refresh"}
          </button>
          {adminToken ? (
            <button className="secondary-button" type="button" onClick={forgetAdminToken}>
              Clear token
            </button>
          ) : null}
        </div>
        {sourceHealth.length ? (
          <div className="source-health-list" aria-label="Official source health">
            {sourceHealth.map((source) => (
              <span
                className={`source-pill ${source.status === "healthy" ? "live" : source.status === "missing_config" ? "sample" : source.status === "needs_adapter" ? "pending" : ""}`}
                key={source.source}
                title={source.source_url ? `${source.coverage} - ${source.source_url}` : source.coverage}
              >
                {sourceLabel(source.source)}: {source.count} · {source.status.replaceAll("_", " ")}
              </span>
            ))}
          </div>
        ) : null}
        {sourceMessage ? <div className="success">{sourceMessage}</div> : null}

        <section className="alert-digest-panel">
          <div className="alert-digest-header">
            <div>
              <span className="field-label">Opportunity alerts</span>
              <strong>{alertRun ? `${alertCounts?.high_fit ?? 0} high fit · ${alertCounts?.due_soon ?? 0} due soon` : "No digest yet"}</strong>
            </div>
            <div className="card-meta">
              <span>{alertPreference ? `tenant ${alertPreference.tenant_id}` : "default settings"}</span>
              {alertRun ? <span>last run {new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }).format(new Date(alertRun.created_at))}</span> : null}
            </div>
          </div>
          <div className="alert-controls">
            <label>
              <span>Min fit</span>
              <input type="number" min="0" max="100" value={alertForm.min_fit_score} onChange={(event) => setAlertForm({ ...alertForm, min_fit_score: event.target.value })} />
            </label>
            <label>
              <span>Due days</span>
              <input type="number" min="1" max="365" value={alertForm.due_within_days} onChange={(event) => setAlertForm({ ...alertForm, due_within_days: event.target.value })} />
            </label>
            <label className="wide-control">
              <span>Email target</span>
              <input value={alertForm.email_to} onChange={(event) => setAlertForm({ ...alertForm, email_to: event.target.value })} placeholder="pilot@example.com" />
            </label>
            <label className="checkbox-label alert-checkbox">
              <input type="checkbox" checked={alertForm.enabled} onChange={(event) => setAlertForm({ ...alertForm, enabled: event.target.checked })} />
              <span>Enabled</span>
            </label>
            <label className="checkbox-label alert-checkbox">
              <input type="checkbox" checked={alertForm.include_source_failures} onChange={(event) => setAlertForm({ ...alertForm, include_source_failures: event.target.checked })} />
              <span>Source failures</span>
            </label>
            <button className="secondary-button" type="button" onClick={() => void saveAlertPreferences()} disabled={alertLoading}>
              <Save size={17} />
              Save alerts
            </button>
            <button className="primary-button" type="button" onClick={() => void runAlertDigest()} disabled={alertLoading}>
              <Bell size={17} />
              {alertLoading ? "Working" : "Generate digest"}
            </button>
          </div>
          {alertRun?.digest.high_fit?.length ? (
            <div className="digest-list">
              {alertRun.digest.high_fit.slice(0, 3).map((item) => (
                <Link href={`/opportunities?id=${item.id}`} key={item.id} className="digest-link">
                  <strong>{item.fit_score ?? "--"} fit</strong>
                  <span>{item.title}</span>
                </Link>
              ))}
            </div>
          ) : null}
          {alertMessage ? <div className="success">{alertMessage}</div> : null}
        </section>

        <form className="search-row" onSubmit={handleSearch}>
          <label className="wide-control">
            <span>Natural-language search</span>
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Show open public electrical bids nationwide above $5M"
            />
          </label>
          <button className="primary-button" type="submit">
            <Search size={17} />
            Search
          </button>
          <button className="secondary-button" type="button" onClick={() => void loadOpportunities(filters)} aria-label="Refresh opportunities">
            <RefreshCw size={17} />
          </button>
        </form>

        <form className="filter-grid" onSubmit={handleFilter}>
          <label>
            <span>Data</span>
            <select
              value={filters.real_only ? "real" : filters.source === "seed" ? "sample" : ""}
              onChange={(event) => {
                const value = event.target.value;
                setFilters({
                  ...filters,
                  real_only: value === "real" ? "true" : "",
                  source: value === "sample" ? "seed" : filters.source === "seed" ? "" : filters.source
                });
              }}
            >
              <option value="">Real + sample</option>
              <option value="real">Official only</option>
              <option value="sample">Sample only</option>
            </select>
          </label>
          <label>
            <span>Workflow</span>
            <select
              value={filters.saved_only ? "saved" : filters.watched_only ? "watched" : filters.include_hidden ? "hidden" : ""}
              onChange={(event) => {
                const value = event.target.value;
                setFilters({
                  ...filters,
                  saved_only: value === "saved" ? "true" : "",
                  watched_only: value === "watched" ? "true" : "",
                  include_hidden: value === "hidden" ? "true" : ""
                });
              }}
            >
              <option value="">All visible</option>
              <option value="saved">Saved</option>
              <option value="watched">Watched</option>
              <option value="hidden">Include hidden</option>
            </select>
          </label>
          <label>
            <span>Due before</span>
            <input type="date" value={filters.due_before} onChange={(event) => setFilters({ ...filters, due_before: event.target.value })} />
          </label>
          <label>
            <span>State</span>
            <input maxLength={2} value={filters.state} onChange={(event) => setFilters({ ...filters, state: event.target.value.toUpperCase() })} placeholder="CA" />
          </label>
          <label>
            <span>Project type</span>
            <select value={filters.project_type} onChange={(event) => setFilters({ ...filters, project_type: event.target.value })}>
              <option value="">Any</option>
              {projectTypes.map((type) => (
                <option key={type} value={type}>
                  {type.replaceAll("_", " ")}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Min fit</span>
            <input type="number" min="0" max="100" value={filters.min_fit_score} onChange={(event) => setFilters({ ...filters, min_fit_score: event.target.value })} placeholder="70" />
          </label>
          <label>
            <span>Min value</span>
            <input type="number" min="0" value={filters.min_value} onChange={(event) => setFilters({ ...filters, min_value: event.target.value })} placeholder="10000000" />
          </label>
          <label>
            <span>Value match</span>
            <select value={filters.minimum_value_match} onChange={(event) => setFilters({ ...filters, minimum_value_match: event.target.value })}>
              <option value="true">Confirmed or likely</option>
              <option value="">Any</option>
              <option value="false">Below or unknown</option>
            </select>
          </label>
          <label>
            <span>Source type</span>
            <select value={filters.source_type} onChange={(event) => setFilters({ ...filters, source_type: event.target.value })}>
              <option value="">Nationwide</option>
              <option value="federal">Federal</option>
              <option value="state_local">State/local</option>
              <option value="utility">Utility</option>
              <option value="education">Education</option>
              <option value="state_dot">State DOT</option>
              <option value="airport_authority">Airport authority</option>
              <option value="transit">Transit</option>
              <option value="university">University</option>
              <option value="water_authority">Water authority</option>
              <option value="manual">Manual</option>
            </select>
          </label>
          <label>
            <span>Status</span>
            <select value={filters.bid_status} onChange={(event) => setFilters({ ...filters, bid_status: event.target.value, open_only: event.target.value === "open" ? "true" : "" })}>
              <option value="open">Open</option>
              <option value="">Any</option>
              <option value="closed">Closed</option>
            </select>
          </label>
          <label>
            <span>Source</span>
            <select
              value={filters.source}
              onChange={(event) =>
                setFilters({
                  ...filters,
                  source: event.target.value,
                  real_only: event.target.value === "seed" ? "" : filters.real_only
                })
              }
            >
              <option value="">Any</option>
              {sourceFilterOptions.map((source) => (
                <option value={source} key={source}>
                  {sourceLabel(source)}
                </option>
              ))}
            </select>
          </label>
          <button className="secondary-button" type="submit">
            <Filter size={17} />
            Apply
          </button>
        </form>
      </section>

      {error ? <div className="alert">{error}</div> : null}
      {loading ? <div className="empty-state">Loading bid intelligence...</div> : null}

      {!loading && searchResults ? (
        <section className="card-list" aria-label="Search results">
          {searchResults.length ? (
            searchResults.map((result) => (
              <OpportunityCard
                key={result.opportunity.id}
                opportunity={result.opportunity}
                explanation={result.search_explanation}
                rankScore={result.rank_score}
              />
            ))
          ) : (
            <div className="empty-state">No ranked matches. Try broadening the query or filters.</div>
          )}
        </section>
      ) : null}

      {!loading && !searchResults ? (
        <section className="card-list" aria-label="Opportunities">
          {opportunities.length ? opportunities.map((opportunity) => <OpportunityCard key={opportunity.id} opportunity={opportunity} />) : <div className="empty-state">No opportunities found.</div>}
        </section>
      ) : null}
    </div>
  );
}
