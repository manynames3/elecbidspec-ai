"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { Filter, RefreshCw, Search } from "lucide-react";
import { apiFetch } from "@/lib/api";
import type { Opportunity, SearchResult } from "@/lib/types";
import { OpportunityCard } from "@/components/OpportunityCard";

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
  source: string;
};

const emptyFilters: Filters = {
  due_before: "",
  state: "",
  project_type: "",
  min_fit_score: "",
  min_value: "",
  source: ""
};

export function Dashboard() {
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [searchResults, setSearchResults] = useState<SearchResult[] | null>(null);
  const [filters, setFilters] = useState<Filters>(emptyFilters);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const visibleCount = searchResults ? searchResults.length : opportunities.length;
  const averageFit = useMemo(() => {
    const scores = opportunities.map((item) => item.fit_score).filter((score): score is number => score !== null);
    if (!scores.length) {
      return "--";
    }
    return Math.round(scores.reduce((sum, score) => sum + score, 0) / scores.length);
  }, [opportunities]);

  async function loadOpportunities(nextFilters = filters) {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      Object.entries(nextFilters).forEach(([key, value]) => {
        if (value) {
          params.set(key, value);
        }
      });
      const path = params.size ? `/opportunities?${params.toString()}` : "/opportunities";
      setOpportunities(await apiFetch<Opportunity[]>(path));
      setSearchResults(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load opportunities");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadOpportunities(emptyFilters);
  }, []);

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

  return (
    <div className="page-stack">
      <section className="page-header">
        <div>
          <p className="eyebrow">Bid intelligence workspace</p>
          <h1>Opportunity dashboard</h1>
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
        <form className="search-row" onSubmit={handleSearch}>
          <label className="wide-control">
            <span>Natural-language search</span>
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Which bids require underground cable installation in the next 30 days?"
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
            <span>Source</span>
            <select value={filters.source} onChange={(event) => setFilters({ ...filters, source: event.target.value })}>
              <option value="">Any</option>
              <option value="seed">Seed</option>
              <option value="manual_upload">Manual upload</option>
              <option value="sam_gov">SAM.gov</option>
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

