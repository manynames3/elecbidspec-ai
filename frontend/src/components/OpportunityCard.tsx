"use client";

import Link from "next/link";
import { CalendarDays, ExternalLink, MapPin, TrendingUp } from "lucide-react";
import { formatCurrency, formatDate, labelize, sourceLabel, whyThisBidMatters } from "@/lib/api";
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

export function OpportunityCard({ opportunity, explanation, rankScore }: OpportunityCardProps) {
  const keywords = opportunity.extracted_specs?.keywords ?? [];
  const rationale = whyThisBidMatters(opportunity);
  return (
    <article className="opportunity-card">
      <div className="card-topline">
        <span className={`score-pill ${fitClass(opportunity.fit_score)}`}>
          <TrendingUp size={14} />
          {opportunity.fit_score ?? "--"} <InfoTooltip tooltip={FIT_TOOLTIP}>fit</InfoTooltip>
        </span>
        <span className="source-pill">{opportunity.bid_status}</span>
        <span className={`source-pill ${opportunity.source === "seed" ? "sample" : "live"}`}>{sourceLabel(opportunity.source)}</span>
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
          {formatDate(opportunity.due_date)}
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
          <span className="field-label">Value read</span>
          <strong>{opportunity.value_confidence.replaceAll("_", " ")}</strong>
        </div>
      </div>
      <p className="bid-rationale">
        <span>Why it matters</span>
        {rationale}
      </p>
      {opportunity.value_explanation ? <p className="compact-copy">{opportunity.value_explanation}</p> : null}
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
