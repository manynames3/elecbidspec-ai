"use client";

import Link from "next/link";
import { CalendarDays, ExternalLink, MapPin, TrendingUp } from "lucide-react";
import { formatCurrency, formatDate, labelize, sourceLabel, taihanEvidenceLabels, whyThisBidMatters } from "@/lib/api";
import { FIT_TOOLTIP, InfoTooltip } from "@/components/InfoTooltip";
import type { Opportunity } from "@/lib/types";

type OpportunityCardProps = {
  opportunity: Opportunity;
  explanation?: string;
  rankScore?: number;
};

function fitClass(score: number | null) {
  if (score === null) {
    return "muted";
  }
  if (score >= 75) {
    return "good";
  }
  if (score >= 55) {
    return "watch";
  }
  return "poor";
}

function attachmentEvidenceExcerpt(opportunity: Opportunity): string | null {
  const specExcerpt = opportunity.extracted_specs?.evidence_excerpts?.find(Boolean);
  if (specExcerpt) {
    return specExcerpt;
  }
  const attachment = opportunity.attachments.find((item) => typeof item.excerpt === "string" && item.excerpt.trim().length > 0);
  return typeof attachment?.excerpt === "string" ? attachment.excerpt : null;
}

export function OpportunityCard({ opportunity, explanation, rankScore }: OpportunityCardProps) {
  const keywords = opportunity.extracted_specs?.keywords ?? [];
  const taihanIntel = opportunity.extracted_specs?.taihan_intelligence;
  const taihanEvidence = taihanEvidenceLabels(opportunity);
  const rationale = whyThisBidMatters(opportunity);
  const evidenceExcerpt = attachmentEvidenceExcerpt(opportunity);
  const timingLabel = opportunity.due_date
    ? formatDate(opportunity.due_date)
    : opportunity.forecast_rfp_date
      ? `Forecast RFP ${formatDate(opportunity.forecast_rfp_date)}`
      : "No posted deadline";
  return (
    <article className="opportunity-card">
      <div className="card-topline">
        <span className={`score-pill ${fitClass(opportunity.fit_score)}`}>
          <TrendingUp size={14} />
          {opportunity.fit_score ?? "--"} <InfoTooltip tooltip={FIT_TOOLTIP}>fit</InfoTooltip>
        </span>
        <span className="source-pill">{opportunity.bid_status}</span>
        <span className={opportunity.project_stage === "early_signal" || opportunity.project_stage === "pre_rfp" ? "source-pill pending" : "source-pill"}>
          {labelize(opportunity.project_stage)}
        </span>
        <span className={`source-pill ${opportunity.source === "seed" ? "sample" : "live"}`}>{sourceLabel(opportunity.source)}</span>
        {taihanIntel ? <span className={`source-pill taihan-${taihanIntel.tier}`}>Taihan {taihanIntel.score}</span> : null}
        {opportunity.owner_type === "investor_owned_utility" ? <span className="source-pill live">IOU</span> : null}
        <span className="source-pill">{opportunity.source_type.replaceAll("_", " ")}</span>
        {rankScore ? <span className="source-pill">rank {rankScore}</span> : null}
      </div>
      <Link href={`/opportunities?id=${opportunity.id}`} className="card-title">
        {opportunity.title}
      </Link>
      <div className="card-meta">
        <span>
          <MapPin size={14} />
          {opportunity.location ?? opportunity.state ?? "Location TBD"}
        </span>
        <span>
          <CalendarDays size={14} />
          {timingLabel}
        </span>
      </div>
      <div className="card-grid">
        <div>
          <span className="field-label">Agency</span>
          <strong>{opportunity.agency ?? "Not posted"}</strong>
        </div>
        <div>
          <span className="field-label">Project type</span>
          <strong>{labelize(opportunity.project_type)}</strong>
        </div>
        <div>
          <span className="field-label">Estimated value</span>
          <strong>{formatCurrency(opportunity.estimated_value)}</strong>
        </div>
        <div>
          <span className="field-label">Stage</span>
          <strong>{labelize(opportunity.project_stage)}</strong>
        </div>
        <div>
          <span className="field-label">Owner</span>
          <strong>{labelize(opportunity.owner_type)}</strong>
        </div>
        <div>
          <span className="field-label">Forecast RFP</span>
          <strong>{formatDate(opportunity.forecast_rfp_date)}</strong>
        </div>
        <div>
          <span className="field-label">Value read</span>
          <strong>{opportunity.value_confidence.replaceAll("_", " ")}</strong>
        </div>
      </div>
      <p className="bid-rationale">
        <span>Why it matters</span>
        {rationale}
      </p>
      {evidenceExcerpt ? (
        <p className="evidence-excerpt">
          <span>Source evidence</span>
          {evidenceExcerpt}
        </p>
      ) : null}
      {opportunity.value_explanation ? <p className="compact-copy">{opportunity.value_explanation}</p> : null}
      {taihanIntel ? (
        <div className="taihan-intel-block">
          <div className="taihan-intel-row">
            <span className="field-label">Taihan angle</span>
            <strong>{taihanIntel.taihan_angle.length ? taihanIntel.taihan_angle.slice(0, 2).join(" · ") : `${taihanIntel.cable_relevance} cable relevance`}</strong>
          </div>
          <p className="compact-copy">{taihanIntel.recommended_action}</p>
          {taihanEvidence.length ? (
            <div className="tag-row">
              {taihanEvidence.map((label) => (
                <span className="tag" key={label}>
                  {label}
                </span>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}
      {keywords.length ? (
        <div className="tag-row">
          {keywords.slice(0, 6).map((keyword) => (
            <span key={keyword} className="tag">
              {keyword}
            </span>
          ))}
        </div>
      ) : null}
      {explanation || opportunity.fit_explanation ? (
        <p className="compact-copy">{explanation ?? opportunity.fit_explanation}</p>
      ) : null}
      <div className="card-actions">
        <Link className="text-link" href={`/opportunities?id=${opportunity.id}`}>
          Open detail
        </Link>
        {opportunity.source_url ? (
          <a className="icon-link" href={opportunity.source_url} target="_blank" rel="noreferrer" aria-label="Open source posting">
            <ExternalLink size={16} />
          </a>
        ) : null}
      </div>
    </article>
  );
}
