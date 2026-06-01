export type MoneyValue = number | string | null;

export type Opportunity = {
  id: number;
  title: string;
  agency: string | null;
  location: string | null;
  state: string | null;
  due_date: string | null;
  naics_code: string | null;
  description: string | null;
  source: string;
  source_type: string;
  source_url: string | null;
  bid_status: string;
  estimated_value: MoneyValue;
  value_confidence: string;
  value_explanation: string | null;
  minimum_value_match: boolean;
  attachments: Array<Record<string, unknown>>;
  extracted_specs: {
    keywords?: string[];
    required_materials?: string[];
    installation_scope?: string[];
    deadlines?: string[];
    bonding_insurance_requirements?: string[];
    submission_instructions?: string[];
    source_text_preview?: string;
  };
  project_type: string;
  confidence_score: number;
  classification_explanation: string | null;
  fit_score: number | null;
  fit_explanation: string | null;
  created_at: string;
  updated_at: string;
};

export type SearchResult = {
  opportunity: Opportunity;
  rank_score: number;
  search_explanation: string;
};

export type Proposal = {
  bid_summary: string;
  scope_checklist: string[];
  missing_information_checklist: string[];
  required_documents_checklist: string[];
  risk_flags: string[];
  draft_executive_summary: string;
  partner_email_template: string;
};

export type CompanyProfile = {
  id: number;
  name: string;
  states_served: string[];
  bonding_capacity: MoneyValue;
  cable_types_supplied: string[];
  installation_capabilities: string[];
  labor_type: string | null;
  experience: Record<string, boolean>;
};

export type IngestionJobStatus = {
  id: number;
  adapter: string;
  status: string;
  result: Record<string, number>;
  error: string | null;
  updated_at: string;
};

export type SourceHealth = {
  source: string;
  label: string;
  category: string;
  coverage: string;
  adapter: string;
  requires_setting?: string;
  status: "healthy" | "stale" | "failed" | "no_records" | "missing_config" | string;
  count: number;
  target_matches: number;
  last_seen_at: string | null;
  last_job_status: string | null;
  last_job_error: string | null;
  last_job_at: string | null;
};

export type IngestionSummary = {
  real_opportunity_count: number;
  sample_opportunity_count: number;
  real_target_match_count: number;
  sources: Array<{
    source: string;
    source_type: string;
    count: number;
    target_matches: number;
    last_seen_at: string | null;
  }>;
  latest_jobs: IngestionJobStatus[];
  source_health: SourceHealth[];
};

export type IngestionRefreshResult = {
  jobs: IngestionJobStatus[];
};
