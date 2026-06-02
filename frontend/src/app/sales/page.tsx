import type { Metadata } from "next";
import Link from "next/link";
import {
  ArrowRight,
  Bell,
  Building2,
  Cable,
  ClipboardCheck,
  FileText,
  Mail,
  Radar,
  Search,
  ShieldCheck,
} from "lucide-react";

export const metadata: Metadata = {
  title: "ElecBidSpec AI | Public bid intelligence for electrical contractors",
  description:
    "A sales-ready bid intelligence and proposal-prep workspace for electrical contractors, GCs, and cable suppliers chasing $5M+ public infrastructure work.",
};

const heroStats = [
  { value: "33", label: "official sources tracked" },
  { value: "$5M+", label: "priority opportunity threshold" },
  { value: "85+", label: "strong-fit bid signal" },
];

const sourceStats = [
  { value: "Federal", label: "SAM.gov and public federal opportunities" },
  { value: "State DOT", label: "transportation infrastructure and bid-item feeds" },
  { value: "Utilities", label: "public power, energy, water, and authority sources" },
  { value: "Local", label: "cities, schools, airports, transit, and universities" },
];

const workflow = [
  {
    icon: Radar,
    title: "Monitor the right public sources",
    copy: "Track fragmented federal, state, utility, education, transit, airport, and municipal bid sources from one workspace instead of checking portals by hand.",
  },
  {
    icon: Search,
    title: "Find the jobs that match your edge",
    copy: "Search in plain English for conduit, underground, pole line, substation, data center, emergency repair, and cable-supply opportunities.",
  },
  {
    icon: ClipboardCheck,
    title: "Move straight into bid prep",
    copy: "Turn each posting into a bid summary, scope checklist, missing-info list, required-document checklist, risk flags, and partner email.",
  },
];

const outcomes = [
  "Stop losing hours to portal hopping, PDF skimming, and low-value public notices.",
  "Prioritize bids by fit score, geography, project type, deadline, source, and likely value.",
  "Spot cable supply plus installation opportunities before competitors build the same shortlist.",
  "Create DOCX and PDF proposal prep outputs your estimating, BD, and partner teams can act on.",
];

const platform = [
  {
    icon: Building2,
    title: "Contractor and GC fit scoring",
    copy: "Score opportunities against states served, bonding capacity, cable types, installation capabilities, labor model, and project history.",
  },
  {
    icon: Cable,
    title: "Electrical scope extraction",
    copy: "Extract underground cable, overhead line, distribution, transmission, conduit, trenching, transformer, substation, fiber, and repair terms.",
  },
  {
    icon: ShieldCheck,
    title: "Bid-readiness guardrails",
    copy: "Surface due dates, bonding and insurance language, submission instructions, missing attachments, and risk flags.",
  },
  {
    icon: Bell,
    title: "Saved searches and alerts",
    copy: "Save high-fit searches and generate daily digests for open opportunities, due-soon work, and source updates.",
  },
  {
    icon: FileText,
    title: "Proposal artifacts",
    copy: "Generate executive summaries, compliance matrices, bid/no-bid memos, checklist packages, DOCX drafts, and PDF exports.",
  },
  {
    icon: Mail,
    title: "Partner outreach",
    copy: "Draft emails to installer, supplier, EPC, and joint-venture partners with the bid context already included.",
  },
];

const pilotPlans = [
  {
    title: "Free beta access",
    copy: "Use the live workspace to test real public-bid discovery and proposal prep without a credit card.",
    items: ["Nationwide source dashboard", "Manual RFP upload", "Fit scoring and filters"],
  },
  {
    title: "Paid pilot",
    copy: "A focused pilot for a BD or estimating team that needs higher-confidence coverage and repeatable proposal prep.",
    items: ["Saved searches and daily digests", "DOCX/PDF proposal outputs", "Company-specific capability profile"],
    featured: true,
  },
  {
    title: "Coverage expansion",
    copy: "Add priority portals and agency-specific adapters around your region, trade focus, and customer list.",
    items: ["State and local source adapters", "Attachment ingestion improvements", "Role-based access controls"],
  },
];

export default function SalesPage() {
  return (
    <main className="sales-page product-sales-page" lang="en">
      <section className="sales-hero">
        <div className="sales-nav">
          <Link href="/sales" className="sales-brand" aria-label="ElecBidSpec AI sales page">
            <span>ElecBidSpec AI</span>
          </Link>
          <nav aria-label="Sales page navigation">
            <a href="#coverage">Coverage</a>
            <a href="#workflow">Workflow</a>
            <a href="#outputs">Outputs</a>
            <a href="#pilot">Pilot</a>
            <Link href="/">Open app</Link>
          </nav>
        </div>

        <img
          className="sales-hero-visual"
          src="/assets/elecbidspec-console-preview-dark.svg"
          alt="ElecBidSpec AI dashboard preview showing source status, fit score, bid cards, and proposal outputs"
        />
        <div className="sales-hero-overlay" aria-hidden="true"></div>

        <div className="sales-hero-content">
          <p className="sales-kicker">Public bid intelligence for electrical work</p>
          <h1>Your next big electrical contract is already posted. Find it first.</h1>
          <p className="sales-hero-copy">
            ElecBidSpec AI monitors fragmented public bid sources nationwide, filters for high-value electrical infrastructure work, scores each bid against your capabilities, and prepares the proposal package before your team starts reading.
          </p>
          <div className="sales-actions">
            <Link href="/" className="sales-primary">
              Start free access
              <ArrowRight size={18} />
            </Link>
            <a href="#workflow" className="sales-secondary">
              See workflow
            </a>
          </div>
          <dl className="sales-hero-stats" aria-label="ElecBidSpec AI proof points">
            {heroStats.map((item) => (
              <div key={item.label}>
                <dt>{item.value}</dt>
                <dd>{item.label}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      <section className="sales-lineage sales-section-pad">
        <div className="sales-section-inner sales-two-column">
          <p className="sales-kicker">Built for bid teams under pressure</p>
          <h2>Public work is visible. The hard part is knowing what is worth chasing.</h2>
          <p>
            Electrical contractors, GCs, and cable suppliers do not need another spreadsheet of public notices. They need a bid radar that understands scope, value, deadline, source credibility, partner needs, and company fit before the opportunity reaches the estimating desk.
          </p>
        </div>
      </section>

      <section className="sales-section-pad sales-muted-band" id="coverage">
        <div className="sales-section-inner">
          <div className="sales-section-heading">
            <p className="sales-kicker">Nationwide opportunity radar</p>
            <h2>One workspace for high-value public electrical opportunities.</h2>
            <p>
              ElecBidSpec AI tracks the fragmented sources that matter for public infrastructure: federal opportunities, state DOTs, utilities, public power, transit, airport authorities, universities, schools, cities, and county procurement sites.
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
            <p className="sales-kicker">From posted bid to bid/no-bid decision</p>
            <h2>Find, qualify, and prepare public electrical bids in one flow.</h2>
            <p>
              The platform compresses the first pass of business development, estimating, and proposal prep into a repeatable review workflow your team can trust.
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

      <section className="sales-section-pad sales-muted-band" id="outputs">
        <div className="sales-section-inner sales-code-layout">
          <div className="sales-code-copy">
            <p className="sales-kicker">What changes for your team</p>
            <h2>Less searching. Better shortlists. Faster proposal starts.</h2>
            <p>
              Every opportunity is translated from posting language into practical pursuit context: why it matters, what the scope requires, what is missing, and what your team should do next.
            </p>
            <ul className="sales-feature-list">
              {outcomes.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
          <div className="sales-code-panel" aria-label="Example bid intelligence record">
            <div className="sales-tabs">
              <span>Bid</span>
              <span>Fit</span>
              <span>Proposal</span>
            </div>
            <pre className="sales-code-block"><code>{`{
  "query": "Show conduit bids over $5M in Texas",
  "opportunity": "Substation duct bank and MV feeder upgrade",
  "fit_score": 87,
  "why_it_matters": [
    "Open public source",
    "$5M+ likely value",
    "Underground conduit and medium-voltage cable scope",
    "Partner installer outreach draft ready"
  ],
  "outputs": ["checklist", "risk flags", "DOCX", "PDF"]
}`}</code></pre>
          </div>
        </div>
      </section>

      <section className="sales-section-pad" id="platform">
        <div className="sales-section-inner">
          <div className="sales-section-heading compact">
            <p className="sales-kicker">Platform capabilities</p>
            <h2>The bid intelligence layer your CRM and estimators do not have.</h2>
          </div>
          <div className="sales-platform-grid">
            {platform.map((item) => {
              const Icon = item.icon;
              return (
                <article className="sales-platform-item" key={item.title}>
                  <Icon size={22} />
                  <h3>{item.title}</h3>
                  <p>{item.copy}</p>
                </article>
              );
            })}
          </div>
        </div>
      </section>

      <section className="sales-section-pad sales-muted-band" id="pilot">
        <div className="sales-section-inner">
          <div className="sales-section-heading">
            <p className="sales-kicker">Pilot path</p>
            <h2>Start with live bid discovery. Expand when coverage proves value.</h2>
            <p>
              The MVP is designed for low-volume pilots: real public data, manual uploads, company capability scoring, and proposal artifacts without heavyweight infrastructure or long onboarding.
            </p>
          </div>
          <div className="sales-plan-grid">
            {pilotPlans.map((plan) => (
              <article className={`sales-plan ${plan.featured ? "featured" : ""}`} key={plan.title}>
                <h3>{plan.title}</h3>
                <p>{plan.copy}</p>
                <ul>
                  {plan.items.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="sales-cta-band">
        <div className="sales-section-inner sales-cta-content">
          <div>
            <p className="sales-kicker">Free during beta</p>
            <h2>Give your bid team a smarter first look at public electrical work.</h2>
          </div>
          <div className="sales-cta-actions">
            <Link href="/" className="sales-primary">
              Open live workspace
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
        <span>Public bid intelligence and proposal prep for electrical contractors, GCs, and cable suppliers.</span>
      </footer>
    </main>
  );
}
