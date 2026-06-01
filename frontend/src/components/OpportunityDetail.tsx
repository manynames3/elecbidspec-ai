"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, CalendarDays, ExternalLink, FileText, RefreshCw } from "lucide-react";
import { apiFetch, formatCurrency, formatDate, labelize } from "@/lib/api";
import type { Opportunity, Proposal } from "@/lib/types";

function ListBlock({ title, items }: { title: string; items: string[] }) {
  return (
    <section className="panel">
      <h2>{title}</h2>
      <ul className="check-list">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </section>
  );
}

export function OpportunityDetail() {
  const searchParams = useSearchParams();
  const id = searchParams.get("id");
  const [opportunity, setOpportunity] = useState<Opportunity | null>(null);
  const [proposal, setProposal] = useState<Proposal | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    setError(null);
    if (!id) {
      setError("Missing opportunity id.");
      setLoading(false);
      return;
    }
    try {
      const [nextOpportunity, nextProposal] = await Promise.all([
        apiFetch<Opportunity>(`/opportunities/${id}`),
        apiFetch<Proposal>(`/opportunities/${id}/proposal`)
      ]);
      setOpportunity(nextOpportunity);
      setProposal(nextProposal);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load opportunity");
    } finally {
      setLoading(false);
    }
  }

  async function rescore() {
    if (!opportunity) {
      return;
    }
    setOpportunity(await apiFetch<Opportunity>(`/opportunities/${opportunity.id}/rescore`, { method: "POST" }));
    setProposal(await apiFetch<Proposal>(`/opportunities/${opportunity.id}/proposal`));
  }

  useEffect(() => {
    void load();
  }, [id]);

  if (loading) {
    return <div className="empty-state">Loading opportunity...</div>;
  }
  if (error || !opportunity) {
    return <div className="alert">{error ?? "Opportunity not found"}</div>;
  }

  const specs = opportunity.extracted_specs ?? {};

  return (
    <div className="page-stack">
      <div className="detail-nav">
        <Link href="/" className="text-link">
          <ArrowLeft size={16} />
          Dashboard
        </Link>
        <button className="secondary-button" onClick={() => void rescore()} type="button">
          <RefreshCw size={16} />
          Rescore
        </button>
      </div>

      <section className="detail-header">
        <div>
          <p className="eyebrow">{opportunity.agency ?? "Agency not posted"}</p>
          <h1>{opportunity.title}</h1>
          <div className="card-meta">
            <span>
              <CalendarDays size={14} />
              {formatDate(opportunity.due_date)}
            </span>
            <span>{opportunity.location ?? opportunity.state ?? "Location TBD"}</span>
            <span>{labelize(opportunity.project_type)}</span>
          </div>
        </div>
        <div className="score-panel">
          <span className="field-label">Fit score</span>
          <strong>{opportunity.fit_score ?? "--"}</strong>
          <span>{formatCurrency(opportunity.estimated_value)}</span>
        </div>
      </section>

      <section className="panel-grid">
        <section className="panel">
          <h2>Bid Summary</h2>
          <p>{proposal?.bid_summary}</p>
          <p className="compact-copy">{opportunity.description}</p>
          {opportunity.source_url ? (
            <a className="text-link" href={opportunity.source_url} target="_blank" rel="noreferrer">
              <ExternalLink size={16} />
              Source posting
            </a>
          ) : null}
        </section>
        <section className="panel">
          <h2>Classification</h2>
          <div className="metric-row">
            <div>
              <span className="field-label">Project type</span>
              <strong>{labelize(opportunity.project_type)}</strong>
            </div>
            <div>
              <span className="field-label">Confidence</span>
              <strong>{Math.round(opportunity.confidence_score * 100)}%</strong>
            </div>
          </div>
          <p>{opportunity.classification_explanation}</p>
          <p className="compact-copy">{opportunity.fit_explanation}</p>
        </section>
      </section>

      <section className="panel">
        <h2>Extracted Specs</h2>
        <div className="spec-grid">
          <div>
            <span className="field-label">Keywords</span>
            <div className="tag-row">
              {(specs.keywords ?? []).map((keyword) => (
                <span className="tag" key={keyword}>
                  {keyword}
                </span>
              ))}
            </div>
          </div>
          <div>
            <span className="field-label">Required materials</span>
            <div className="tag-row">
              {(specs.required_materials ?? []).map((material) => (
                <span className="tag" key={material}>
                  {material}
                </span>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="panel-grid">
        {proposal ? (
          <>
            <ListBlock title="Scope Checklist" items={proposal.scope_checklist} />
            <ListBlock title="Missing Information" items={proposal.missing_information_checklist} />
            <ListBlock title="Required Documents" items={proposal.required_documents_checklist} />
            <ListBlock title="Risk Flags" items={proposal.risk_flags.length ? proposal.risk_flags : ["No major automated risk flags."]} />
          </>
        ) : null}
      </section>

      {proposal ? (
        <section className="panel-grid">
          <section className="panel">
            <h2>Draft Executive Summary</h2>
            <p>{proposal.draft_executive_summary}</p>
          </section>
          <section className="panel">
            <h2>Partner Email</h2>
            <pre className="email-box">{proposal.partner_email_template}</pre>
          </section>
        </section>
      ) : null}

      {opportunity.attachments.length ? (
        <section className="panel">
          <h2>Attachments</h2>
          <ul className="check-list">
            {opportunity.attachments.map((attachment, index) => (
              <li key={`${attachment.name}-${index}`}>
                <FileText size={15} />
                {String(attachment.name ?? attachment.url ?? attachment.stored_path ?? "Attachment")}
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}
