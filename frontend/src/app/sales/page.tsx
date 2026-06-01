import type { Metadata } from "next";
import Link from "next/link";
import {
  ArrowRight,
  FileText,
  Radar,
  Search,
} from "lucide-react";

export const metadata: Metadata = {
  title: "ElecBidSpec AI for Taihan | U.S. Public Bid Intelligence",
  description:
    "A U.S. public bid intelligence and proposal-prep workspace tuned for Taihan Cable & Solution's power cable, EHV, HVDC, overhead, distribution, and submarine cable capabilities.",
};

const sourceStats = [
  { value: "33", label: "U.S. public source targets" },
  { value: "$5M+", label: "infrastructure bid threshold" },
  { value: "EHV", label: "HVDC, XLPE, overhead, MV/LV fit" },
  { value: "DOCX", label: "proposal-ready outputs" },
];

const taihanFacts = [
  {
    value: "1941",
    label: "Korea's first electric wire company",
    href: "https://www.taihan.com/en/company/overview",
  },
  {
    value: "100+",
    label: "countries entered with a global network",
    href: "https://www.taihan.com/en/company/overview",
  },
  {
    value: "EHV/HVDC",
    label: "transmission cable and accessory portfolio",
    href: "https://www.taihan.com/en/business/product/electricity",
  },
  {
    value: "CLV",
    label: "submarine and offshore-wind value chain",
    href: "https://www.taihan.com/en/business/solutionDetail?idx=10",
  },
];

const outcomes = [
  "Find U.S. public power-grid, utility, DOT, airport, data-center, renewable, and authority opportunities without living in portal tabs.",
  "Separate real cable scope from procurement noise: EHV, HVDC, overhead line, MV/LV distribution, submarine/offshore wind, accessories, substations, and installation partner needs.",
  "Turn promising notices into a Taihan-ready bid/no-bid memo, compliance matrix, missing-info checklist, partner email, and executive summary.",
];

const workflow = [
  {
    icon: Radar,
    title: "Monitor U.S. public demand",
    copy: "SAM.gov-ready ingestion plus state, utility, DOT, airport, transit, city, authority, and Bonfire-style public source adapters.",
  },
  {
    icon: Search,
    title: "Rank against Taihan capability",
    copy: "Fit scoring prioritizes geography, value, cable type, underground/overhead/substation scope, and partner-installation needs.",
  },
  {
    icon: FileText,
    title: "Prepare the pursuit package",
    copy: "Each opportunity becomes a scope checklist, risk readout, compliance matrix, executive summary, and partner outreach email.",
  },
];

const proof = [
  "EHV/HVDC cable scope detection",
  "Overhead line, MV/LV distribution, conduit, transformer, and substation keywords",
  "Submarine, offshore-wind, and port authority opportunity language",
  "Partner installer and EPC outreach templates",
  "Portal-gated source monitoring with health status",
  "Taihan-specific proposal language from the company profile",
];

export default function SalesPage() {
  return (
    <main className="sales-page">
      <section className="sales-hero">
        <div className="sales-nav">
          <Link href="/sales" className="sales-brand" aria-label="ElecBidSpec AI sales page">
            <span className="sales-brand-mark" aria-hidden="true">EB</span>
            <span>ElecBidSpec AI for 대한전선</span>
          </Link>
          <nav aria-label="Sales page navigation">
            <a href="#coverage">Coverage</a>
            <a href="#workflow">Workflow</a>
            <a href="#pilot">Pilot</a>
            <Link href="/">Open app</Link>
          </nav>
        </div>

        <img
          className="sales-hero-visual"
          src="/assets/elecbidspec-console-preview-dark.svg"
          alt="ElecBidSpec AI platform preview showing source health, ranked opportunities, fit scoring, and proposal outputs"
        />
        <div className="sales-hero-overlay" aria-hidden="true"></div>

        <div className="sales-hero-content">
          <p className="sales-kicker">Built for Taihan Cable & Solution's U.S. opportunity motion</p>
          <h1>ElecBidSpec <em>AI</em> for 대한전선</h1>
          <p className="sales-hero-copy">
            A U.S. public bid radar and proposal-prep workspace tuned to Taihan's power cable, EHV, HVDC, overhead, distribution, and submarine cable strengths.
          </p>
          <div className="sales-actions">
            <Link href="/" className="sales-primary">
              Open the live tool
              <ArrowRight size={18} />
            </Link>
            <a href="#pilot" className="sales-secondary">
              See pilot fit
            </a>
          </div>
          <dl className="sales-hero-stats" aria-label="Platform highlights">
            <div>
              <dt>U.S.</dt>
              <dd>public bid radar</dd>
            </div>
            <div>
              <dt>$5M+</dt>
              <dd>target projects</dd>
            </div>
            <div>
              <dt>Taihan</dt>
              <dd>capability context</dd>
            </div>
          </dl>
        </div>
      </section>

      <section className="sales-lineage sales-section-pad">
        <div className="sales-section-inner sales-two-column">
          <p className="sales-kicker">Taihan-ready positioning</p>
          <h2>Designed around a global cable leader entering U.S. public infrastructure pursuits.</h2>
          <p>
            Taihan's official story is not just product supply. It is global power infrastructure, total cable solutions, EHV/HVDC cable systems, overhead and distribution products, and expanding submarine cable execution. The pilot turns that capability context into a U.S. bid-screening system.
          </p>
        </div>
      </section>

      <section className="sales-section-pad sales-source-band">
        <div className="sales-section-inner">
          <div className="sales-section-heading">
            <p className="sales-kicker">Capability basis</p>
            <h2>Position the tool around what Taihan already sells, builds, and proves publicly.</h2>
            <p>
              The landing page and proposal assistant should reference Taihan's public capability profile: power transmission and distribution, EHV/HVDC, overhead line, MV/LV distribution, cable accessories, offshore wind, submarine cables, and global delivery.
            </p>
          </div>
          <div className="sales-fact-grid">
            {taihanFacts.map((fact) => (
              <a className="sales-fact-card" href={fact.href} key={fact.label} target="_blank" rel="noreferrer">
                <strong>{fact.value}</strong>
                <span>{fact.label}</span>
              </a>
            ))}
          </div>
        </div>
      </section>

      <section className="sales-section-pad sales-muted-band" id="coverage">
        <div className="sales-section-inner">
          <div className="sales-section-heading">
            <p className="sales-kicker">Live U.S. market read</p>
            <h2>Nationwide opportunities filtered for Taihan-relevant cable and grid scope.</h2>
            <p>
              The product does not hide weak coverage. It shows where adapters are live, where a public portal needs a better access path, where no matching records were found, and which sources deserve the next adapter build.
            </p>
          </div>
          <div className="sales-stat-grid">
            {sourceStats.map((item) => (
              <div className="sales-stat" key={item.label}>
                <strong>{item.value}</strong>
                <span>{item.label}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="sales-section-pad" id="workflow">
        <div className="sales-section-inner">
          <div className="sales-section-heading">
            <p className="sales-kicker">From notice to Taihan pursuit</p>
            <h2>A workflow for cable supply, partner installation, and proposal readiness.</h2>
            <p>
              The same workspace handles discovery, technical scope extraction, fit scoring, saved searches, partner outreach, and proposal artifacts.
            </p>
          </div>
          <div className="sales-workflow-grid">
            {workflow.map((item) => {
              const Icon = item.icon;
              return (
                <article className="sales-workflow-card" key={item.title}>
                  <Icon size={22} />
                  <h3>{item.title}</h3>
                  <p>{item.copy}</p>
                </article>
              );
            })}
          </div>
        </div>
      </section>

      <section className="sales-section-pad sales-muted-band">
        <div className="sales-section-inner sales-code-layout">
          <div className="sales-code-copy">
            <p className="sales-kicker">Why Taihan should care</p>
            <h2>Less portal chasing. More qualified U.S. pipeline intelligence.</h2>
            <p>
              A Taihan business-development or sales team should see value in the first session: ranked U.S. public bids, why each bid matters, source health, saved searches, and proposal artifacts that can move quickly to a partner installer, EPC, distributor, or internal pursuit lead.
            </p>
            <ul className="sales-feature-list">
              {outcomes.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
          <div className="sales-code-panel" aria-label="Example bid intelligence record">
            <div className="sales-tabs">
              <span>Opportunity</span>
              <span>Fit</span>
              <span>Proposal</span>
            </div>
            <pre className="sales-code-block"><code>{`{
  "source": "JEA",
  "project": "Transformer package",
  "companyContext": "Taihan Cable & Solution",
  "fitScore": 71,
  "capabilitySignals": ["EHV", "MV/LV", "substation"],
  "whyItMatters": [
    "official utility source",
    "$5M+ target likely",
    "transformer / distribution scope",
    "partner installer outreach ready"
  ]
}`}</code></pre>
          </div>
        </div>
      </section>

      <section className="sales-section-pad" id="platform">
        <div className="sales-section-inner">
          <div className="sales-section-heading compact">
            <p className="sales-kicker">Pilot platform</p>
            <h2>Built for a focused Taihan U.S. market pilot.</h2>
          </div>
          <div className="sales-platform-grid">
            {proof.map((item) => (
              <article className="sales-platform-item" key={item}>
                <h3>{item}</h3>
                <p>Designed to make a Taihan pilot feel concrete, verifiable, and useful without a heavy platform bill.</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="sales-section-pad sales-muted-band" id="pilot">
        <div className="sales-section-inner">
          <div className="sales-section-heading">
            <p className="sales-kicker">Pilot packaging</p>
            <h2>A practical path from Taihan U.S. bid radar to pursuit operations.</h2>
            <p>
              Start with a low-traffic pilot for U.S. public opportunities, then add deeper source adapters, private user accounts, and managed proposal workflows as usage proves out.
            </p>
          </div>
          <div className="sales-plan-grid">
            <article className="sales-plan">
              <h3>Taihan discovery pilot</h3>
              <p>For validating U.S. public opportunity coverage and bid/no-bid workflow with one team.</p>
              <ul>
                <li>Live dashboard and source health</li>
                <li>Manual uploads and extraction</li>
                <li>Saved searches and digest runs</li>
              </ul>
            </article>
            <article className="sales-plan featured">
              <h3>Sales pursuit pilot</h3>
              <p>For Taihan sales, BD, and partner teams testing proposal-prep value.</p>
              <ul>
                <li>Taihan-specific company context</li>
                <li>DOCX proposal drafts</li>
                <li>Daily saved-search alerts</li>
              </ul>
            </article>
            <article className="sales-plan">
              <h3>Coverage expansion</h3>
              <p>For adding the U.S. portals, utilities, DOTs, and local authorities that matter most to Taihan.</p>
              <ul>
                <li>More DOTs and utilities</li>
                <li>Attachment fetching per source</li>
                <li>Admin controls and tenant separation</li>
              </ul>
            </article>
          </div>
        </div>
      </section>

      <section className="sales-cta-band">
        <div className="sales-section-inner sales-cta-content">
          <div>
            <p className="sales-kicker">Ready for Taihan review</p>
            <h2>Show 대한전선 a live U.S. bid workspace, not a generic SaaS demo.</h2>
          </div>
          <div className="sales-cta-actions">
            <Link href="/" className="sales-primary">
              Launch app
              <ArrowRight size={18} />
            </Link>
            <a href="#coverage" className="sales-secondary on-dark">
              Review coverage
            </a>
          </div>
        </div>
      </section>

      <footer className="sales-footer">
        <span>©2026 ElecBidSpec AI</span>
        <span>U.S. bid intelligence and proposal prep tuned for Taihan Cable & Solution.</span>
      </footer>
    </main>
  );
}
