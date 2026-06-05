import type { Metadata } from "next";
import Link from "next/link";
import {
  ArrowRight,
  AlertTriangle,
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
  title: "ElecBidSpec AI | Pre-RFP opportunity intelligence for power infrastructure",
  description:
    "Pre-RFP pursuit intelligence for cable suppliers, utility sales teams, and electrical infrastructure contractors tracking grid, IOU, data-center, and high-voltage power opportunities before procurement opens.",
};

const heroStats = [
  { value: "44", label: "official source targets tracked" },
  { value: "Pre-RFP", label: "primary intelligence stage" },
  { value: "$5M+", label: "high-value pursuit threshold" },
];

const sourceStats = [
  { value: "RTO/ISO", label: "transmission queues, upgrade plans, and interconnection signals" },
  { value: "PUC", label: "utility dockets, rate cases, and large-load filings" },
  { value: "Land use", label: "data-center, substation, zoning, and permit indicators" },
  { value: "Bid handoff", label: "active solicitations monitored once procurement opens" },
];

const workflow = [
  {
    icon: Radar,
    title: "Detect demand before the RFP",
    copy: "Monitor fragmented public signals where electrical demand forms first: PUC dockets, RTO/ISO queues, utility plans, land-use filings, data-center load requests, and capital programs.",
  },
  {
    icon: Search,
    title: "Rank what is worth pursuing",
    copy: "Classify each signal by owner, stage, likely value, scope, voltage, cable relevance, data-center/load evidence, and fit against company capabilities.",
  },
  {
    icon: ClipboardCheck,
    title: "Turn signals into pursuit action",
    copy: "Generate a short why-now narrative, evidence excerpt, recommended next step, partner outreach angle, and bid-readiness package when the opportunity matures.",
  },
];

const missReasons = [
  {
    icon: Radar,
    title: "The buying signal appears months before procurement",
    copy: "Grid and data-center power scope can surface first in dockets, interconnection queues, transmission plans, site approvals, and utility filings long before a bid title says cable.",
  },
  {
    icon: AlertTriangle,
    title: "Internal teams already monitor pieces of this, not the whole picture",
    copy: "Large suppliers usually have BD, utility sales, proposal, and strategy teams. The gap is a shared, ranked view that connects early evidence to action.",
  },
  {
    icon: FileText,
    title: "Late discovery weakens supplier positioning",
    copy: "If a team first sees the project at RFP release, it may already be late for AVL work, EPC relationships, owner education, partner selection, and bid/no-bid strategy.",
  },
];

const pursuitPhases = [
  {
    phase: "PHASE 1",
    title: "Signal",
    timing: "Before formal procurement",
    copy: "Find public evidence of future high-voltage cable, substation, transmission, distribution, data-center power, and large-load infrastructure demand.",
  },
  {
    phase: "PHASE 2",
    title: "Position",
    timing: "Owner, AVL, EPC, and partner window",
    copy: "Score each opportunity, explain why it matters now, and recommend whether to monitor, engage, prequalify, partner, or prepare for bid release.",
  },
  {
    phase: "PHASE 3",
    title: "Capture",
    timing: "When the RFP appears",
    copy: "Carry forward the evidence trail into bid summaries, scope checklists, missing-information lists, risk flags, compliance matrices, DOCX/PDF drafts, and partner emails.",
  },
];

const outcomes = [
  "Stop waiting for bid boards to tell you about projects that were visible upstream.",
  "Give BD and utility sales a weekly ranked shortlist of high-value grid and data-center power signals.",
  "Connect each signal to evidence, owner context, likely scope, why-now timing, and the next commercial action.",
  "Keep proposal prep attached to the early intelligence so context is not lost when procurement opens.",
];

const proofStats = [
  { value: "44", label: "official source targets across federal, state, utility, RTO/ISO, regulatory, land-use, authority, education, transit, airport, and local procurement" },
  { value: "Pre-RFP", label: "early signal, pre-RFP, active bid, and award fields keep pursuit timing explicit instead of mixing everything into one bid feed" },
  { value: "Evidence", label: "each opportunity is built around source links, excerpts, why-now notes, and fit explanations rather than unqualified lead titles" },
  { value: "DOCX/PDF", label: "proposal-prep artifacts are generated from opportunity details, technical specs, and company capability context when a pursuit becomes actionable" },
];

const platform = [
  {
    icon: Building2,
    title: "Company-fit and owner-fit scoring",
    copy: "Score opportunities against geography, bonding capacity, cable types, installation capabilities, labor model, owner type, voltage evidence, and project history.",
  },
  {
    icon: Cable,
    title: "Cable and power-scope extraction",
    copy: "Extract underground cable, overhead line, distribution, transmission, medium voltage, high voltage, conduit, transformer, substation, fiber, and repair terms.",
  },
  {
    icon: ShieldCheck,
    title: "Evidence-backed why-now narratives",
    copy: "Show why each signal matters now, where the evidence came from, and what action the pursuit team should take before a formal RFP exists.",
  },
  {
    icon: Bell,
    title: "Saved searches and opportunity alerts",
    copy: "Track high-fit searches for data-center power, AI load, IOU upgrades, substations, transmission lines, and utility replacement programs.",
  },
  {
    icon: FileText,
    title: "Bid-readiness artifacts",
    copy: "Generate executive summaries, compliance matrices, bid/no-bid memos, checklists, DOCX drafts, and PDF exports once the opportunity moves toward procurement.",
  },
  {
    icon: Mail,
    title: "Partner and EPC outreach",
    copy: "Draft early outreach to installers, EPCs, suppliers, distributors, and utility-facing partners with signal context already included.",
  },
];

const faqs = [
  {
    question: "How is this different from a bid board?",
    answer: "A bid board starts when procurement opens. ElecBidSpec AI is focused on pre-RFP opportunity intelligence: public signals, owner context, evidence, fit scoring, why-now timing, and pursuit actions before the RFP clock starts.",
  },
  {
    question: "Does this replace an internal BD or utility sales team?",
    answer: "No. It gives those teams a better radar. Large suppliers already have people watching customers and markets; the product creates a shared, ranked, evidence-backed view so teams do not miss fragmented signals.",
  },
  {
    question: "What opportunities does the product prioritize?",
    answer: "The workspace prioritizes high-value grid, IOU, data-center, AI infrastructure, MV/HV cable, underground conduit, substation, transmission, utility replacement, and public infrastructure opportunities.",
  },
  {
    question: "Is this software or a consulting service?",
    answer: "The strongest pilot is both: a live workspace plus a managed weekly opportunity desk. The software handles monitoring, scoring, search, and artifacts; analyst review turns the top signals into commercial recommendations.",
  },
];

const pilotPlans = [
  {
    title: "Signal scan",
    copy: "A fast first pass to prove whether the system can surface relevant pre-RFP grid and data-center opportunities your team is not already tracking.",
    items: ["Two-week source scan", "Ranked opportunity sample", "Evidence links and why-now notes"],
  },
  {
    title: "Managed opportunity desk",
    copy: "A paid pilot for BD, utility sales, or strategy teams that want weekly pre-RFP intelligence plus access to the live workspace.",
    items: ["Weekly ranked signal brief", "Dashboard access and saved searches", "Monthly pursuit review call"],
    featured: true,
  },
  {
    title: "Coverage expansion",
    copy: "Add priority utilities, PUCs, ISOs/RTOs, data-center markets, EPC targets, and private/public portals around the customer's North America strategy.",
    items: ["Source-specific adapters", "Custom fit model", "Proposal and partner-outreach templates"],
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
            <a href="#coverage">Signals</a>
            <a href="#workflow">Workflow</a>
            <a href="#outputs">Outputs</a>
            <a href="#pilot">Pilot</a>
            <Link href="/">Open app</Link>
          </nav>
        </div>

        <img
          className="sales-hero-visual"
          src="/assets/elecbidspec-console-preview-dark.svg"
          alt="ElecBidSpec AI dashboard preview showing pre-RFP signals, source status, fit score, opportunity cards, and proposal outputs"
        />
        <div className="sales-hero-overlay" aria-hidden="true"></div>

        <div className="sales-hero-content">
          <p className="sales-kicker">Pre-RFP opportunity intelligence for power infrastructure</p>
          <h1>Find grid and data-center power projects before they become bids.</h1>
          <p className="sales-hero-copy">
            ElecBidSpec AI monitors fragmented public signals nationwide, ranks early-stage grid and data-center power opportunities against your capabilities, and gives BD teams the evidence and next action before procurement opens.
          </p>
          <div className="sales-actions">
            <Link href="/" className="sales-primary">
              Open live workspace
              <ArrowRight size={18} />
            </Link>
            <a href="#pilot" className="sales-secondary">
              See pilot model
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
          <p className="sales-kicker">Not another bid board</p>
          <h2>Large electrical suppliers do not need more raw notices. They need earlier pursuit timing.</h2>
          <p>
            Public RFPs are the late-stage artifact. The opportunity often starts in a utility filing, interconnection queue, data-center site plan, capital program, or transmission upgrade notice. ElecBidSpec AI turns those scattered signals into a ranked pursuit pipeline for cable suppliers, utility sales teams, and electrical infrastructure contractors.
          </p>
        </div>
      </section>

      <section className="sales-section-pad sales-muted-band">
        <div className="sales-section-inner">
          <div className="sales-section-heading">
            <p className="sales-kicker">Why teams miss winnable work</p>
            <h2>The project is usually public before it is purchasable.</h2>
            <p>
              The commercial advantage is not finding a bid title faster. It is knowing which future projects deserve relationship-building, AVL work, partner outreach, and proposal preparation before competitors see the same solicitation.
            </p>
          </div>
          <div className="sales-workflow-grid">
            {missReasons.map((item) => {
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

      <section className="sales-section-pad sales-muted-band" id="coverage">
        <div className="sales-section-inner">
          <div className="sales-section-heading">
            <p className="sales-kicker">Nationwide pre-RFP radar</p>
            <h2>Track the public signals that create future cable demand.</h2>
            <p>
              ElecBidSpec AI watches fragmented sources that matter before the bid: RTO/ISO queues, PUC dockets, utility and public-power signals, land-use filings, data-center and AI load indicators, transportation authorities, schools, universities, airports, cities, counties, state DOTs, and formal bids once procurement opens.
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
            <p className="sales-kicker">From early signal to pursuit decision</p>
            <h2>Find, qualify, and act before the bid clock starts.</h2>
            <p>
              The platform compresses the first pass of business development, utility sales, market strategy, prequalification, partner outreach, and proposal readiness into a repeatable workflow.
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
        <div className="sales-section-inner">
          <div className="sales-section-heading">
            <p className="sales-kicker">From demand signal to bid handoff</p>
            <h2>Keep context alive from first public evidence through proposal prep.</h2>
            <p>
              Early intelligence only matters if it changes action. ElecBidSpec AI keeps the signal, evidence, fit score, owner context, and pursuit recommendation attached as the opportunity moves toward procurement.
            </p>
          </div>
          <div className="sales-plan-grid">
            {pursuitPhases.map((item) => (
              <article className="sales-plan" key={item.title}>
                <span className="sales-phase-label">{item.phase}</span>
                <h3>{item.title}</h3>
                <p className="sales-phase-time">{item.timing}</p>
                <p>{item.copy}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="sales-section-pad sales-muted-band" id="outputs">
        <div className="sales-section-inner sales-code-layout">
          <div className="sales-code-copy">
            <p className="sales-kicker">What changes for your team</p>
            <h2>A ranked weekly opportunity desk, not a pile of links.</h2>
            <p>
              Every signal is translated into practical pursuit context: why it matters, what evidence supports it, who owns it, what scope is likely, and what your team should do next.
            </p>
            <ul className="sales-feature-list">
              {outcomes.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
          <div className="sales-code-panel" aria-label="Example pre-RFP opportunity intelligence record">
            <div className="sales-tabs">
              <span>Signal</span>
              <span>Fit</span>
              <span>Action</span>
            </div>
            <pre className="sales-code-block"><code>{`{
  "query": "data center load and 230 kV substation signals",
  "stage": "early_signal",
  "source_type": "rto_iso",
  "owner_type": "investor_owned_utility",
  "opportunity": "230 kV transmission line and substation upgrade",
  "taihan_priority": "high",
  "why_now": [
    "public queue signal before gated RFP",
    "named utility and voltage evidence",
    "large-load / data-center indicators",
    "AVL and EPC positioning window is open"
  ],
  "next_action": "monitor, map EPCs, prepare utility-owner outreach",
  "handoff_outputs": ["brief", "evidence", "partner email", "DOCX", "PDF"]
}`}</code></pre>
          </div>
        </div>
      </section>

      <section className="sales-section-pad">
        <div className="sales-section-inner">
          <div className="sales-section-heading">
            <p className="sales-kicker">The proof that matters</p>
            <h2>Coverage is only valuable when it produces a better pursuit decision.</h2>
          </div>
          <div className="sales-stat-grid">
            {proofStats.map((item) => (
              <div className="sales-stat" key={item.label}>
                <strong>{item.value}</strong>
                <span>{item.label}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="sales-section-pad" id="platform">
        <div className="sales-section-inner">
          <div className="sales-section-heading compact">
            <p className="sales-kicker">Platform capabilities</p>
            <h2>The pre-RFP intelligence layer your CRM and bid tools do not have.</h2>
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

      <section className="sales-section-pad" id="faq">
        <div className="sales-section-inner">
          <div className="sales-section-heading compact">
            <p className="sales-kicker">Common questions</p>
            <h2>Built for early pursuit intelligence, not generic bid aggregation.</h2>
          </div>
          <div className="sales-platform-grid">
            {faqs.map((item) => (
              <article className="sales-platform-item" key={item.question}>
                <h3>{item.question}</h3>
                <p>{item.answer}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="sales-section-pad sales-muted-band" id="pilot">
        <div className="sales-section-inner">
          <div className="sales-section-heading">
            <p className="sales-kicker">Pilot path</p>
            <h2>Sell the first pilot as an opportunity desk, then productize the workflow.</h2>
            <p>
              The best first buyer is a BD, utility sales, or strategy leader who wants proof that earlier signal coverage can create real commercial action. The pilot combines live software with reviewed weekly intelligence.
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
            <p className="sales-kicker">Pre-RFP intelligence pilot</p>
            <h2>Give your BD team the first look at future grid and data-center power demand.</h2>
          </div>
          <div className="sales-cta-actions">
            <Link href="/" className="sales-primary">
              Open live workspace
              <ArrowRight size={18} />
            </Link>
            <a href="#coverage" className="sales-secondary on-dark">
              Review signals
            </a>
          </div>
        </div>
      </section>

      <footer className="sales-footer">
        <span>©2026 SUPREME AI VENTURES LLC</span>
        <span>Pre-RFP opportunity intelligence for grid, utility, data-center, and electrical infrastructure pursuits.</span>
      </footer>
    </main>
  );
}
