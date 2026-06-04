"use client";

import { FormEvent, type ReactNode, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Bell, CheckCircle2, DatabaseZap, Download, Filter, Lock, RefreshCw, Save, Search } from "lucide-react";
import { apiFetch, apiUrl, authHeaders, sourceLabel, whyNowNarrative } from "@/lib/api";
import type { AccountStatus, AlertPreference, AlertRun, IngestionRefreshResult, IngestionSummary, Opportunity, SavedSearch, SearchResult } from "@/lib/types";
import { COVERED_BY_SOURCE_TOOLTIP, FIT_TOOLTIP, InfoTooltip, PORTAL_GATED_TOOLTIP, VALUE_MATCH_TOOLTIP } from "@/components/InfoTooltip";
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

const projectStages = ["early_signal", "pre_rfp", "active_bid", "awarded"];

const ownerTypes = ["investor_owned_utility", "public_power_or_utility", "public_agency", "private_developer"];

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
  "houston_water",
  "pjm_project_construction",
  "caiso_interconnection_queue",
  "ercot_capacity_changes",
  "iso_ne_interconnection_queue",
  "miso_eras_interconnection",
  "nyiso_interconnection_queue",
  "spp_gi_active_requests",
  "texas_puc_dockets",
  "virginia_scc_transmission_cases",
  "georgia_psc_data_center",
  "loudoun_land_applications"
];

type Filters = {
  due_before: string;
  state: string;
  project_type: string;
  project_stage: string;
  owner_type: string;
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
  project_stage: "",
  owner_type: "",
  min_fit_score: "",
  min_value: "",
  minimum_value_match: "true",
  source_type: "",
  bid_status: "",
  source: "",
  open_only: "",
  real_only: "true",
  saved_only: "",
  watched_only: "",
  include_hidden: ""
};

const defaultAlertForm = {
  email_to: "",
  min_fit_score: "70",
  due_within_days: "30",
  enabled: true,
  include_source_failures: true
};

function SourceStatusText({ status }: { status: string }) {
  if (status === "portal_gated") {
    return <InfoTooltip tooltip={PORTAL_GATED_TOOLTIP}>Manual Review</InfoTooltip>;
  }
  if (status === "covered_by_source") {
    return <InfoTooltip tooltip={COVERED_BY_SOURCE_TOOLTIP}>Covered By Source</InfoTooltip>;
  }
  return status.replaceAll("_", " ");
}

function taihanScore(opportunity: Opportunity) {
  return opportunity.extracted_specs?.taihan_intelligence?.score ?? 0;
}

function isHighTaihanPriority(opportunity: Opportunity) {
  return opportunity.extracted_specs?.taihan_intelligence?.tier === "high";
}

function taihanTierRank(opportunity: Opportunity) {
  const tier = opportunity.extracted_specs?.taihan_intelligence?.tier;
  if (tier === "high") {
    return 3;
  }
  if (tier === "medium") {
    return 2;
  }
  if (tier === "low") {
    return 1;
  }
  return 0;
}

function stageRank(opportunity: Opportunity) {
  if (opportunity.project_stage === "early_signal" || opportunity.project_stage === "pre_rfp") {
    return 2;
  }
  if (opportunity.project_stage === "active_bid") {
    return 1;
  }
  return 0;
}

function sortPipeline(records: Opportunity[]) {
  return [...records].sort(
    (first, second) =>
      taihanTierRank(second) - taihanTierRank(first) ||
      taihanScore(second) - taihanScore(first) ||
      (second.fit_score ?? 0) - (first.fit_score ?? 0) ||
      stageRank(second) - stageRank(first)
  );
}

function hasSignalText(opportunity: Opportunity, terms: string[]) {
  const text = [
    opportunity.title,
    opportunity.agency,
    opportunity.description,
    opportunity.project_type,
    opportunity.signal_type,
    opportunity.source_type,
    ...(opportunity.extracted_specs?.keywords ?? []),
    ...(opportunity.extracted_specs?.required_materials ?? [])
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
  return terms.some((term) => text.includes(term));
}

function KpiCard({ label, value, helper, tone }: { label: ReactNode; value: ReactNode; helper: string; tone?: "primary" | "success" | "warning" }) {
  return (
    <div className={`kpi-card ${tone ? `kpi-${tone}` : ""}`}>
      <span className="field-label">{label}</span>
      <strong>{value}</strong>
      <span className="kpi-helper">{helper}</span>
    </div>
  );
}

export function Dashboard() {
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [upstreamSignals, setUpstreamSignals] = useState<Opportunity[]>([]);
  const [searchResults, setSearchResults] = useState<SearchResult[] | null>(null);
  const [filters, setFilters] = useState<Filters>(emptyFilters);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshingSources, setRefreshingSources] = useState(false);
  const [ingestionSummary, setIngestionSummary] = useState<IngestionSummary | null>(null);
  const [accountStatus, setAccountStatus] = useState<AccountStatus | null>(null);
  const [alertPreference, setAlertPreference] = useState<AlertPreference | null>(null);
  const [alertRun, setAlertRun] = useState<AlertRun | null>(null);
  const [savedSearches, setSavedSearches] = useState<SavedSearch[]>([]);
  const [savedSearchName, setSavedSearchName] = useState("");
  const [alertForm, setAlertForm] = useState(defaultAlertForm);
  const [alertLoading, setAlertLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sourceMessage, setSourceMessage] = useState<string | null>(null);
  const [alertMessage, setAlertMessage] = useState<string | null>(null);

  const visibleCount = searchResults ? searchResults.length : opportunities.length;
  const latestPublicRefresh = ingestionSummary?.latest_jobs.find((job) => job.adapter !== "sam_gov");
  const sourceHealth = ingestionSummary?.source_health ?? [];
  const publicSourceCount = sourceHealth.length || ingestionSummary?.sources.filter((source) => source.source !== "seed" && source.source !== "manual_upload").length || 0;
  const liveImportingSourceCount = sourceHealth.filter((source) => source.status === "healthy").length;
  const gatedSourceCount = sourceHealth.filter((source) => source.status === "portal_gated").length;
  const coveredSourceCount = sourceHealth.filter((source) => source.status === "covered_by_source").length;
  const noCurrentMatchSourceCount = sourceHealth.filter((source) => source.status === "no_current_matches" || source.status === "no_records").length;
  const needsAttentionSourceCount = sourceHealth.filter((source) => ["failed", "missing_config", "needs_adapter"].includes(source.status)).length;
  const availableSourceOptions = useMemo(() => {
    const dynamicSources = [
      ...sourceHealth.map((source) => source.source),
      ...opportunities.map((opportunity) => opportunity.source)
    ].filter(Boolean);

    return Array.from(new Set([...sourceFilterOptions, ...dynamicSources])).sort((first, second) => sourceLabel(first).localeCompare(sourceLabel(second)));
  }, [opportunities, sourceHealth]);
  const canAdminRefresh = accountStatus?.feature_flags.admin_refresh ?? false;
  const canUseAlerts = accountStatus?.feature_flags.saved_search_alerts ?? false;
  const alertCounts = alertRun?.digest.counts;
  const onboardingSteps = [
    { label: "Sign in to a pilot workspace", complete: accountStatus?.authenticated ?? false },
    { label: "Confirm company capability profile", complete: accountStatus?.onboarding.has_profile ?? false },
    { label: "Load official source coverage", complete: accountStatus?.onboarding.source_summary_loaded ?? false },
    { label: "Save at least one pursuit search", complete: (accountStatus?.onboarding.saved_search_count ?? savedSearches.length) > 0 },
    { label: "Turn on daily bid alerts", complete: accountStatus?.onboarding.alert_configured ?? false }
  ];
  const averageFit = useMemo(() => {
    const scores = opportunities.map((item) => item.fit_score).filter((score): score is number => score !== null);
    if (!scores.length) {
      return "--";
    }
    return Math.round(scores.reduce((sum, score) => sum + score, 0) / scores.length);
  }, [opportunities]);
  const earlySignalCount = useMemo(
    () => opportunities.filter((item) => item.project_stage === "early_signal" || item.project_stage === "pre_rfp").length,
    [opportunities]
  );
  const activeBidCount = useMemo(() => opportunities.filter((item) => item.project_stage === "active_bid" && item.bid_status === "open").length, [opportunities]);
  const highTaihanSignalCount = useMemo(() => upstreamSignals.filter(isHighTaihanPriority).length, [upstreamSignals]);
  const watchlistTaihanSignalCount = useMemo(() => upstreamSignals.filter((item) => ["high", "medium"].includes(item.extracted_specs?.taihan_intelligence?.tier ?? "")).length, [upstreamSignals]);
  const dataCenterSignalCount = useMemo(
    () => upstreamSignals.filter((item) => hasSignalText(item, ["data center", "datacenter", "hyperscale", "ai infrastructure", "large load", "gpu"])).length,
    [upstreamSignals]
  );
  const iouSignalCount = useMemo(
    () => upstreamSignals.filter((item) => item.owner_type === "investor_owned_utility" || item.source_type === "regulatory" || item.source_type === "utility").length,
    [upstreamSignals]
  );
  const topUpstreamSignals = useMemo(
    () => sortPipeline(upstreamSignals).slice(0, 8),
    [upstreamSignals]
  );

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
      let [loadedOpportunities, loadedSummary, loadedUpstreamSignals] = await Promise.all([
        apiFetch<Opportunity[]>(opportunityPath(activeFilters)),
        apiFetch<IngestionSummary>("/ingestion/summary"),
        apiFetch<Opportunity[]>("/opportunities?real_only=true&minimum_value_match=true")
      ]);
      if (activeFilters.real_only && !loadedOpportunities.length && loadedSummary.real_opportunity_count === 0) {
        activeFilters = { ...activeFilters, real_only: "" };
        loadedOpportunities = await apiFetch<Opportunity[]>(opportunityPath(activeFilters));
        setFilters(activeFilters);
      }
      setOpportunities(sortPipeline(loadedOpportunities));
      setUpstreamSignals(sortPipeline(loadedUpstreamSignals.filter((item) => item.project_stage === "early_signal" || item.project_stage === "pre_rfp")));
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
      setSavedSearches(await apiFetch<SavedSearch[]>("/saved-searches"));
    } catch {
      setAlertPreference(null);
    }
  }

  function clearAccountOwnedState() {
    setAlertPreference(null);
    setAlertRun(null);
    setSavedSearches([]);
    setSavedSearchName("");
    setAlertForm(defaultAlertForm);
  }

  async function loadAccountStatus() {
    try {
      const status = await apiFetch<AccountStatus>("/account/status");
      setAccountStatus(status);
      return status;
    } catch {
      setAccountStatus(null);
      return null;
    }
  }

  async function refreshAccountState() {
    const status = await loadAccountStatus();
    if (status?.feature_flags.saved_search_alerts) {
      await loadAlerts();
    } else {
      clearAccountOwnedState();
    }
  }

  useEffect(() => {
    function handleAuthChange() {
      void refreshAccountState();
    }

    void loadOpportunities(emptyFilters);
    void refreshAccountState();
    window.addEventListener("elecbidspec-auth-changed", handleAuthChange);
    return () => window.removeEventListener("elecbidspec-auth-changed", handleAuthChange);
  }, []);

  async function handleFilter(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await loadOpportunities(filters);
  }

  async function runSearch(searchQuery: string) {
    if (!searchQuery.trim()) {
      await loadOpportunities(filters);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      setSearchResults(
        await apiFetch<SearchResult[]>("/search", {
          method: "POST",
          body: JSON.stringify({ query: searchQuery })
        })
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setLoading(false);
    }
  }

  async function handleSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await runSearch(query);
  }

  async function refreshPublicSources() {
    setRefreshingSources(true);
    setError(null);
    setSourceMessage(null);
    try {
      if (!canAdminRefresh) {
        throw new Error("Admin login required to refresh public sources.");
      }
      const result = await apiFetch<IngestionRefreshResult>("/ingestion/refresh-defaults", { method: "POST" });
      const imported = result.jobs.reduce((sum, job) => sum + Number(job.result.imported ?? 0), 0);
      const updated = result.jobs.reduce((sum, job) => sum + Number(job.result.updated ?? 0), 0);
      const queued = result.jobs.reduce((sum, job) => sum + Number(job.result.queued ?? 0), 0);
      const failed = result.jobs.filter((job) => job.status === "failed").length;
      const skipped = result.jobs.filter((job) => job.status === "skipped").length;
      setSourceMessage(`Public sources refreshed: ${imported} imported, ${updated} updated${queued ? `, ${queued} queued` : ""}${failed ? `, ${failed} failed` : ""}${skipped ? `, ${skipped} skipped` : ""}.`);
      await loadOpportunities(filters);
      await refreshAccountState();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to refresh public sources");
    } finally {
      setRefreshingSources(false);
    }
  }

  function applyUpstreamPreset(preset: Partial<Filters>) {
    const nextFilters = {
      ...emptyFilters,
      real_only: "true",
      minimum_value_match: "true",
      bid_status: "",
      open_only: "",
      ...preset
    };
    setFilters(nextFilters);
    setSearchResults(null);
    void loadOpportunities(nextFilters);
  }

  function applyPipelinePreset(preset: Partial<Filters>) {
    const nextFilters = {
      ...emptyFilters,
      real_only: "true",
      minimum_value_match: "true",
      ...preset
    };
    setFilters(nextFilters);
    setSearchResults(null);
    void loadOpportunities(nextFilters);
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
      await refreshAccountState();
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
      await refreshAccountState();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to generate alert digest");
    } finally {
      setAlertLoading(false);
    }
  }

  async function saveCurrentSearch() {
    setAlertLoading(true);
    setAlertMessage(null);
    setError(null);
    try {
      const fallbackName = query.trim() || `${filters.state || "Nationwide"} ${filters.project_type || filters.source_type || "opportunities"}`;
      const saved = await apiFetch<SavedSearch>("/saved-searches", {
        method: "POST",
        body: JSON.stringify({
          name: (savedSearchName || fallbackName).trim(),
          query: query.trim() || null,
          filters,
          enabled: true,
          email_digest: true
        })
      });
      setSavedSearchName("");
      setSavedSearches((current) => [saved, ...current.filter((item) => item.id !== saved.id)]);
      setAlertMessage("Saved search added to daily digest.");
      await refreshAccountState();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save search");
    } finally {
      setAlertLoading(false);
    }
  }

  async function downloadWeeklyReport() {
    if (!accountStatus?.feature_flags.proposal_exports) {
      setError("Pilot login required to export weekly intelligence reports.");
      return;
    }
    const response = await fetch(apiUrl("/intelligence/weekly-report.pdf"), {
      headers: authHeaders()
    });
    if (!response.ok) {
      throw new Error(await response.text());
    }
    const blob = await response.blob();
    const objectUrl = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = objectUrl;
    link.download = "taihan-weekly-intelligence-report.pdf";
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(objectUrl);
  }

  async function deleteSavedSearch(savedSearchId: number) {
    setAlertLoading(true);
    setAlertMessage(null);
    setError(null);
    try {
      await apiFetch<unknown>(`/saved-searches/${savedSearchId}`, { method: "DELETE" });
      setSavedSearches((current) => current.filter((item) => item.id !== savedSearchId));
      setAlertMessage("Saved search removed.");
      await refreshAccountState();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to delete saved search");
    } finally {
      setAlertLoading(false);
    }
  }

  function applySavedSearch(savedSearch: SavedSearch) {
    const nextFilters = { ...emptyFilters, ...(savedSearch.filters as Partial<Filters>) };
    setFilters(nextFilters);
    setQuery(savedSearch.query ?? "");
    void loadOpportunities(nextFilters);
  }

  return (
    <div className="page-stack">
      <section className="page-header">
        <div>
          <p className="eyebrow">Pre-RFP opportunity intelligence</p>
          <h1>Grid, utility, and data-center power signals before they become bids.</h1>
          <p className="page-subheading">
            ElecBidSpec AI monitors 44 official sources nationwide, ranks early public signals against your capabilities, and keeps active bid handoff ready when procurement opens.
          </p>
          <div className="header-actions">
            <button className="primary-button" type="button" onClick={() => void downloadWeeklyReport().catch((err) => setError(err instanceof Error ? err.message : "Weekly report download failed"))}>
              <Download size={17} />
              Weekly intelligence PDF
            </button>
          </div>
        </div>
        <div className="summary-strip">
          <KpiCard label="Pipeline records" value={opportunities.length} helper="Value-matched records in view" tone="primary" />
          <KpiCard label="Shown" value={visibleCount} helper={searchResults ? "Ranked search results" : "Current filtered list"} />
          <KpiCard label={<InfoTooltip tooltip={FIT_TOOLTIP}>Avg fit</InfoTooltip>} value={averageFit} helper="Capability alignment" />
          <KpiCard label="Active bids" value={activeBidCount} helper="Formal open bid handoff" tone="warning" />
          <KpiCard label="Pre-RFP" value={earlySignalCount} helper="Early signals to position" tone="success" />
        </div>
      </section>

      <form className="search-row" onSubmit={handleSearch}>
        <label className="wide-control">
          <span>Natural-language search</span>
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder={"Try it: \"Show conduit bids over $5M in Texas due in the next 30 days\""}
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

      <section className="pilot-readiness-panel">
        <div className="pilot-readiness-copy">
          <span className="field-label">Pilot workspace</span>
          <strong>{accountStatus?.plan_label ?? "Loading workspace"}</strong>
          <p className="compact-copy">
            {accountStatus?.authenticated
              ? `Signed in as ${accountStatus.user?.email ?? "pilot user"} for tenant ${accountStatus.tenant_id}.`
              : "Demo preview shows live product behavior. Sign in to save pursuits, generate alert digests, and export proposal packages for a real company profile."}
          </p>
        </div>
        <div className="pilot-feature-grid" aria-label="Pilot feature access">
          <div>
            <span className="field-label">Proposal exports</span>
            <strong>{accountStatus?.feature_flags.proposal_exports ? "Enabled" : "Pilot login"}</strong>
          </div>
          <div>
            <span className="field-label">Daily alerts</span>
            <strong>{accountStatus?.feature_flags.saved_search_alerts ? "Enabled" : "Pilot login"}</strong>
          </div>
          <div>
            <span className="field-label">Admin refresh</span>
            <strong>{canAdminRefresh ? "Enabled" : "Admin only"}</strong>
          </div>
        </div>
        <div className="onboarding-list" aria-label="Pilot onboarding checklist">
          {onboardingSteps.map((step) => (
            <span className={step.complete ? "onboarding-step complete" : "onboarding-step"} key={step.label}>
              {step.complete ? <CheckCircle2 size={15} /> : <Lock size={15} />}
              {step.label}
            </span>
          ))}
        </div>
      </section>

      <section className="upstream-intel-panel" aria-label="Upstream intelligence">
        <div className="panel-title-row">
          <div>
            <span className="field-label">Upstream Intelligence</span>
            <h2>Pre-RFP grid, IOU, and data-center power signals</h2>
          </div>
          <div className="card-meta">
            <span>{upstreamSignals.length} qualified early signals</span>
            <span>{highTaihanSignalCount} high-priority for Taihan</span>
          </div>
        </div>
        <div className="upstream-metric-grid">
          <div>
            <span className="field-label">Taihan high-priority</span>
            <strong>{highTaihanSignalCount}</strong>
          </div>
          <div>
            <span className="field-label">Taihan watchlist</span>
            <strong>{watchlistTaihanSignalCount}</strong>
          </div>
          <div>
            <span className="field-label">Data center / AI</span>
            <strong>{dataCenterSignalCount}</strong>
          </div>
          <div>
            <span className="field-label">IOU / regulatory</span>
            <strong>{iouSignalCount}</strong>
          </div>
          <div>
            <span className="field-label">RTO / ISO queue</span>
            <strong>{upstreamSignals.filter((item) => item.source_type === "rto_iso").length}</strong>
          </div>
        </div>
        <p className="compact-copy">
          Pre-RFP records are public planning, queue, docket, or permitting signals. They are not formal bids yet; they are where Taihan can start owner, AVL, EPC, and partner positioning before a solicitation is posted.
        </p>
        <div className="upstream-actions" aria-label="Upstream intelligence filters">
          <button type="button" className="secondary-button" onClick={() => applyUpstreamPreset({ project_stage: "early_signal" })}>
            Pre-RFP signals
          </button>
          <button type="button" className="secondary-button" onClick={() => applyUpstreamPreset({ source_type: "rto_iso", project_stage: "early_signal" })}>
            RTO/ISO queues
          </button>
          <button type="button" className="secondary-button" onClick={() => applyUpstreamPreset({ source_type: "regulatory", project_stage: "early_signal" })}>
            PUC dockets
          </button>
          <button type="button" className="secondary-button" onClick={() => applyUpstreamPreset({ owner_type: "investor_owned_utility", project_stage: "early_signal" })}>
            IOU signals
          </button>
          <button
            type="button"
            className="secondary-button"
            onClick={() => {
              const nextQuery = "data center AI infrastructure large load high voltage substation signals";
              setQuery(nextQuery);
              void runSearch(nextQuery);
            }}
          >
            Data center / AI
          </button>
        </div>
        {topUpstreamSignals.length ? (
          <div className="upstream-signal-list">
            {topUpstreamSignals.map((item) => {
              const intel = item.extracted_specs?.taihan_intelligence;
              return (
                <Link href={`/opportunities?id=${item.id}`} className="upstream-signal-row" key={item.id}>
                  <strong>{intel ? `Taihan ${intel.score}` : item.fit_score ?? "--"}</strong>
                  <span>
                    <b>{item.title}</b>
                    <small>{whyNowNarrative(item)}</small>
                  </span>
                  <em>{sourceLabel(item.source)}</em>
                </Link>
              );
            })}
          </div>
        ) : null}
      </section>

      <section className="toolbar-band">
        <div className="source-health">
          <div className="source-card">
            <span className="field-label">Official sources</span>
            <strong>{publicSourceCount || "--"}</strong>
          </div>
          <div className="source-card">
            <span className="field-label">Live importing sources</span>
            <strong>{sourceHealth.length ? `${liveImportingSourceCount}/${sourceHealth.length}` : "--"}</strong>
          </div>
          <div className="source-card">
            <span className="field-label">Manual-review sources</span>
            <strong>{sourceHealth.length ? gatedSourceCount : "--"}</strong>
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
          {canAdminRefresh ? (
            <button className="secondary-button" type="button" onClick={() => void refreshPublicSources()} disabled={refreshingSources}>
              <DatabaseZap size={17} />
              {refreshingSources ? "Refreshing" : "Admin refresh"}
            </button>
          ) : (
            <div className="source-card source-admin-card">
              <span className="field-label">Refresh controls</span>
              <strong>Admin only</strong>
            </div>
          )}
        </div>
        <div className="coverage-trust-grid" aria-label="Source coverage trust">
          <div>
            <span className="field-label">Live importing</span>
            <strong>{liveImportingSourceCount}</strong>
            <p className="compact-copy">Recent official records are flowing into ranked opportunity cards.</p>
          </div>
          <div>
            <span className="field-label">Manual review</span>
            <strong>{gatedSourceCount}</strong>
            <p className="compact-copy">Tracked sources that need approved portal access before they can become live imports.</p>
          </div>
          <div>
            <span className="field-label">Covered by source</span>
            <strong>{coveredSourceCount}</strong>
            <p className="compact-copy">Duplicate agency coverage is included through another connected feed.</p>
          </div>
          <div>
            <span className="field-label">No current matches</span>
            <strong>{noCurrentMatchSourceCount}</strong>
            <p className="compact-copy">Connected or tracked sources with no current $5M+ electrical matches.</p>
          </div>
          <div>
            <span className="field-label">Needs attention</span>
            <strong>{needsAttentionSourceCount}</strong>
            <p className="compact-copy">Adapters or credentials that need admin follow-up before production use.</p>
          </div>
        </div>
        {sourceHealth.length ? (
          <div className="source-health-list" aria-label="Official source health">
            {sourceHealth.map((source) => (
              <span
                className={`source-pill ${source.status === "healthy" ? "live" : source.status === "missing_config" ? "sample" : source.status === "needs_adapter" || source.status === "directory_only" || source.status === "covered_by_source" || source.status === "no_current_matches" ? "pending" : source.status === "portal_gated" ? "gated" : ""}`}
                key={source.source}
                title={`${source.coverage}${source.access_note ? ` - ${source.access_note}` : ""}${source.last_job_error ? ` - ${source.last_job_error}` : ""}`}
              >
                {sourceLabel(source.source)}: {source.count} · <SourceStatusText status={source.status} />
              </span>
            ))}
          </div>
        ) : null}
        {sourceMessage ? <div className="success">{sourceMessage}</div> : null}

        <section className="alert-digest-panel">
          <div className="alert-digest-header">
            <div>
              <span className="field-label">Opportunity alerts</span>
              <strong>
                {alertRun ? (
                  <>
                    {alertCounts?.high_fit ?? 0} <InfoTooltip tooltip={FIT_TOOLTIP}>high fit</InfoTooltip> · {alertCounts?.due_soon ?? 0} due soon
                  </>
                ) : (
                  "No digest yet"
                )}
              </strong>
            </div>
            <div className="card-meta">
              <span>{alertPreference ? `tenant ${alertPreference.tenant_id}` : "default settings"}</span>
              {alertRun ? <span>last run {new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }).format(new Date(alertRun.created_at))}</span> : null}
            </div>
          </div>
          {!canUseAlerts ? <p className="compact-copy">Sign in to a pilot workspace to save searches and generate daily pursuit digests.</p> : null}
          <div className="alert-controls">
            <label>
              <span>
                <InfoTooltip tooltip={FIT_TOOLTIP}>Min fit</InfoTooltip>
              </span>
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
            <button className="secondary-button" type="button" onClick={() => void saveAlertPreferences()} disabled={alertLoading || !canUseAlerts}>
              <Save size={17} />
              Save alerts
            </button>
            <button className="primary-button" type="button" onClick={() => void runAlertDigest()} disabled={alertLoading || !canUseAlerts}>
              <Bell size={17} />
              {alertLoading ? "Working" : "Generate digest"}
            </button>
          </div>
          <div className="saved-search-panel">
            <div className="saved-search-form">
              <label className="wide-control">
                <span>Saved search name</span>
                <input value={savedSearchName} onChange={(event) => setSavedSearchName(event.target.value)} placeholder="Underground cable due soon" />
              </label>
              <button className="secondary-button" type="button" onClick={() => void saveCurrentSearch()} disabled={alertLoading || !canUseAlerts}>
                <Save size={17} />
                Save current search
              </button>
            </div>
            {savedSearches.length ? (
              <div className="saved-search-list">
                {savedSearches.slice(0, 5).map((savedSearch) => (
                  <div className="saved-search-item" key={savedSearch.id}>
                    <button type="button" className="text-link" onClick={() => applySavedSearch(savedSearch)}>
                      {savedSearch.name}
                    </button>
                    <span>{savedSearch.query || "filter search"}</span>
                    <button type="button" className="text-link danger-link" onClick={() => void deleteSavedSearch(savedSearch.id)} disabled={alertLoading || !canUseAlerts}>
                      Remove
                    </button>
                  </div>
                ))}
              </div>
            ) : null}
          </div>
          {alertRun?.digest.high_fit?.length ? (
            <div className="digest-list">
              {alertRun.digest.high_fit.slice(0, 3).map((item) => (
                <Link href={`/opportunities?id=${item.id}`} key={item.id} className="digest-link">
                  <strong>
                    {item.fit_score ?? "--"} <InfoTooltip tooltip={FIT_TOOLTIP}>fit</InfoTooltip>
                  </strong>
                  <span>{item.title}</span>
                </Link>
              ))}
            </div>
          ) : null}
          {alertMessage ? <div className="success">{alertMessage}</div> : null}
        </section>

        <div className="pipeline-preset-row" aria-label="Pipeline presets">
          <button type="button" className="secondary-button" onClick={() => applyPipelinePreset({})}>
            Recommended pipeline
          </button>
          <button type="button" className="secondary-button" onClick={() => applyPipelinePreset({ bid_status: "open", open_only: "true", project_stage: "active_bid" })}>
            Active bids only
          </button>
          <button type="button" className="secondary-button" onClick={() => applyPipelinePreset({ project_stage: "early_signal", bid_status: "", open_only: "" })}>
            Pre-RFP signals
          </button>
          <button type="button" className="secondary-button" onClick={() => applyPipelinePreset({ min_fit_score: "85", bid_status: "", open_only: "" })}>
            Strong Taihan fit
          </button>
        </div>

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
              disabled={!accountStatus?.authenticated}
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
            <span>Stage</span>
            <select value={filters.project_stage} onChange={(event) => setFilters({ ...filters, project_stage: event.target.value })}>
              <option value="">Any</option>
              {projectStages.map((stage) => (
                <option key={stage} value={stage}>
                  {stage.replaceAll("_", " ")}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Owner</span>
            <select value={filters.owner_type} onChange={(event) => setFilters({ ...filters, owner_type: event.target.value })}>
              <option value="">Any</option>
              {ownerTypes.map((ownerType) => (
                <option key={ownerType} value={ownerType}>
                  {ownerType.replaceAll("_", " ")}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>
              <InfoTooltip tooltip={FIT_TOOLTIP}>Min fit</InfoTooltip>
            </span>
            <input type="number" min="0" max="100" value={filters.min_fit_score} onChange={(event) => setFilters({ ...filters, min_fit_score: event.target.value })} placeholder="70" />
          </label>
          <label>
            <span>Min value</span>
            <input type="number" min="0" value={filters.min_value} onChange={(event) => setFilters({ ...filters, min_value: event.target.value })} placeholder="10000000" />
          </label>
          <label>
            <span>
              <InfoTooltip tooltip={VALUE_MATCH_TOOLTIP}>Value match</InfoTooltip>
            </span>
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
              <option value="investor_owned_utility">Investor-owned utility</option>
              <option value="regulatory">Regulatory</option>
              <option value="rto_iso">RTO/ISO</option>
              <option value="land_use">Land use</option>
              <option value="private_developer">Private developer</option>
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
              <option value="">Any</option>
              <option value="open">Open</option>
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
              {availableSourceOptions.map((source) => (
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

      {error ? (
        <div className="alert">
          <strong>Unable to load workspace</strong>
          <span>{error}</span>
        </div>
      ) : null}
      {loading ? (
        <div className="empty-state loading-state">
          <strong>Loading opportunity intelligence</strong>
          <span>Refreshing source coverage, fit scoring, and signal ranking.</span>
        </div>
      ) : null}

      {!loading && searchResults ? (
        <section className="results-section" aria-label="Search results">
          <div className="results-header">
            <div>
              <span className="field-label">Ranked results</span>
              <h2>{searchResults.length ? `${searchResults.length} matching opportunities` : "No ranked matches"}</h2>
            </div>
            <p className="compact-copy">Search results are ranked by relevance, fit, value, and electrical scope context.</p>
          </div>
          <div className="card-list">
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
            <div className="empty-state">
              <strong>No ranked matches</strong>
              <span>Try broadening the query, clearing a filter, or searching for a source type such as RTO/ISO, PUC, data center, or substation.</span>
            </div>
          )}
          </div>
        </section>
      ) : null}

      {!loading && !searchResults ? (
        <section className="results-section" aria-label="Opportunities">
          <div className="results-header">
            <div>
              <span className="field-label">Opportunity pipeline</span>
              <h2>{opportunities.length ? `${opportunities.length} prioritized records` : "No opportunities found"}</h2>
            </div>
            <p className="compact-copy">Default view emphasizes pre-RFP and early public signals before formal bid release.</p>
          </div>
          <div className="card-list">
            {opportunities.length ? (
              opportunities.map((opportunity) => <OpportunityCard key={opportunity.id} opportunity={opportunity} />)
            ) : (
              <div className="empty-state">
                <strong>No opportunities found</strong>
                <span>Adjust filters or switch from active bids to pre-RFP signals to expand the pipeline.</span>
              </div>
            )}
          </div>
        </section>
      ) : null}
    </div>
  );
}
