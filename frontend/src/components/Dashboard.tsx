"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { DatabaseZap, Filter, RefreshCw, Search } from "lucide-react";
import { apiFetch, sourceLabel } from "@/lib/api";
import type { IngestionRefreshResult, IngestionSummary, Opportunity, SearchResult } from "@/lib/types";
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
  real_only: "true"
};

export function Dashboard() {
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [searchResults, setSearchResults] = useState<SearchResult[] | null>(null);
  const [filters, setFilters] = useState<Filters>(emptyFilters);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshingSources, setRefreshingSources] = useState(false);
  const [ingestionSummary, setIngestionSummary] = useState<IngestionSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sourceMessage, setSourceMessage] = useState<string | null>(null);
  const [adminToken, setAdminToken] = useState("");

  const visibleCount = searchResults ? searchResults.length : opportunities.length;
  const latestPublicRefresh = ingestionSummary?.latest_jobs.find((job) => job.adapter !== "sam_gov");
  const sourceHealth = ingestionSummary?.source_health ?? [];
  const publicSourceCount = sourceHealth.length || ingestionSummary?.sources.filter((source) => source.source !== "seed" && source.source !== "manual_upload").length || 0;
  const healthySourceCount = sourceHealth.filter((source) => source.status === "healthy").length;
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

  useEffect(() => {
    setAdminToken(window.localStorage.getItem(adminTokenStorageKey) ?? "");
    void loadOpportunities(emptyFilters);
  }, []);

  function adminHeaders() {
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
      const failed = result.jobs.filter((job) => job.status === "failed").length;
      const skipped = result.jobs.filter((job) => job.status === "skipped").length;
      setSourceMessage(`Public sources refreshed: ${imported} imported, ${updated} updated${failed ? `, ${failed} failed` : ""}${skipped ? `, ${skipped} skipped` : ""}.`);
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
              <span className={`source-pill ${source.status === "healthy" ? "live" : source.status === "missing_config" ? "sample" : ""}`} key={source.source} title={source.coverage}>
                {sourceLabel(source.source)}: {source.count} · {source.status.replaceAll("_", " ")}
              </span>
            ))}
          </div>
        ) : null}
        {sourceMessage ? <div className="success">{sourceMessage}</div> : null}

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
              <option value="seed">Seed</option>
              <option value="manual_upload">Manual upload</option>
              <option value="sam_gov">SAM.gov</option>
              <option value="chicago_solicitations">Chicago/CTA</option>
              <option value="la_ramp">Los Angeles RAMP</option>
              <option value="montgomery_md_solicitations">Montgomery County</option>
              <option value="nypa">NY Power Authority</option>
              <option value="nyc_city_record">NYC City Record</option>
              <option value="nyc_school_construction_authority">NYC School Construction</option>
              <option value="sf_open_bids">San Francisco</option>
              <option value="txdot_bid_items">TxDOT</option>
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
