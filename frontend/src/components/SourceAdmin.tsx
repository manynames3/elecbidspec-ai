"use client";

import { useEffect, useMemo, useState } from "react";
import { ExternalLink, ShieldCheck } from "lucide-react";
import { apiFetch, formatDate, sourceLabel } from "@/lib/api";
import type { AccountStatus, IngestionSummary, SourceHealth } from "@/lib/types";
import { COVERED_BY_SOURCE_TOOLTIP, InfoTooltip, PORTAL_GATED_TOOLTIP } from "@/components/InfoTooltip";

function sourceStatusLabel(source: SourceHealth) {
  if (source.status === "portal_gated") {
    return <InfoTooltip tooltip={PORTAL_GATED_TOOLTIP}>Portal Gated</InfoTooltip>;
  }
  if (source.status === "covered_by_source") {
    return <InfoTooltip tooltip={COVERED_BY_SOURCE_TOOLTIP}>Covered By Source</InfoTooltip>;
  }
  return source.status.replaceAll("_", " ");
}

export function SourceAdmin() {
  const [accountStatus, setAccountStatus] = useState<AccountStatus | null>(null);
  const [summary, setSummary] = useState<IngestionSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const nextAccountStatus = await apiFetch<AccountStatus>("/account/status");
        setAccountStatus(nextAccountStatus);
        if (nextAccountStatus.feature_flags.admin_refresh) {
          setSummary(await apiFetch<IngestionSummary>("/ingestion/summary"));
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unable to load source coverage.");
      }
    }
    void load();
  }, []);

  const counts = useMemo(() => {
    const health = summary?.source_health ?? [];
    return {
      live: health.filter((source) => source.status === "healthy").length,
      gated: health.filter((source) => source.status === "portal_gated").length,
      covered: health.filter((source) => source.status === "covered_by_source").length,
      attention: health.filter((source) => ["failed", "missing_config", "needs_adapter"].includes(source.status)).length,
      total: health.length
    };
  }, [summary]);

  if (error) {
    return <div className="alert">{error}</div>;
  }

  const canUseAdminView = accountStatus?.feature_flags.admin_refresh ?? false;

  if (accountStatus && !canUseAdminView) {
    return (
      <div className="page-stack">
        <section className="page-header">
          <div>
            <p className="eyebrow">Source operations</p>
            <h1>Coverage and ingestion health</h1>
            <p className="page-subheading">Detailed source operations are limited to admin users.</p>
          </div>
        </section>
        <div className="pilot-gate-banner">
          <ShieldCheck size={17} />
          <span>Admin login required for source operations. Public users can still see summarized coverage on the dashboard.</span>
        </div>
      </div>
    );
  }

  return (
    <div className="page-stack">
      <section className="page-header">
        <div>
          <p className="eyebrow">Source operations</p>
          <h1>Coverage and ingestion health</h1>
          <p className="page-subheading">
            Audit which official sources are importing records, which are gated, and which need adapter or credential follow-up.
          </p>
        </div>
        <div className="summary-strip">
          <div>
            <span className="field-label">Live</span>
            <strong>{counts.total ? `${counts.live}/${counts.total}` : "--"}</strong>
          </div>
          <div>
            <span className="field-label">Gated</span>
            <strong>{counts.total ? counts.gated : "--"}</strong>
          </div>
          <div>
            <span className="field-label">Attention</span>
            <strong>{counts.total ? counts.attention : "--"}</strong>
          </div>
        </div>
      </section>

      {!accountStatus ? (
        <div className="pilot-gate-banner">
          <ShieldCheck size={17} />
          <span>Checking admin access...</span>
        </div>
      ) : null}

      <section className="panel">
        <div className="metric-row">
          <div>
            <span className="field-label">Real records</span>
            <strong>{summary?.real_opportunity_count ?? "--"}</strong>
          </div>
          <div>
            <span className="field-label">Real target matches</span>
            <strong>{summary?.real_target_match_count ?? "--"}</strong>
          </div>
          <div>
            <span className="field-label">Covered duplicate sources</span>
            <strong>{counts.total ? counts.covered : "--"}</strong>
          </div>
        </div>
      </section>

      <section className="panel">
        <h2>Tracked Sources</h2>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Source</th>
                <th>Status</th>
                <th>Records</th>
                <th>$5M+ matches</th>
                <th>Last job</th>
                <th>Access note</th>
              </tr>
            </thead>
            <tbody>
              {(summary?.source_health ?? []).map((source) => (
                <tr key={source.source}>
                  <td>
                    <strong>{sourceLabel(source.source)}</strong>
                    {source.source_url ? (
                      <a className="text-link" href={source.source_url} target="_blank" rel="noreferrer">
                        <ExternalLink size={14} />
                        Portal
                      </a>
                    ) : null}
                  </td>
                  <td>{sourceStatusLabel(source)}</td>
                  <td>{source.count}</td>
                  <td>{source.target_matches}</td>
                  <td>{source.last_job_at ? formatDate(source.last_job_at.slice(0, 10)) : source.last_job_status ?? "--"}</td>
                  <td>{source.access_note || source.last_job_error || source.coverage || "--"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
