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
  compliance_matrix: Array<{
    requirement: string;
    status: string;
    evidence: string;
    owner: string;
  }>;
  bid_no_bid_memo: string;
  partner_email_template: string;
};

export type OpportunityWorkflow = {
  id: number;
  opportunity_id: number;
  tenant_id: string;
  saved: boolean;
  watched: boolean;
  hidden: boolean;
  status: string;
  owner: string | null;
  priority: string;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type AttachmentExtraction = {
  id: number;
  opportunity_id: number;
  source_url: string;
  filename: string | null;
  status: string;
  attachment: Record<string, unknown>;
  extracted_specs: Record<string, unknown>;
  error: string | null;
  created_at: string;
  updated_at: string;
};

export type AttachmentIngestionResult = {
  opportunity: Opportunity;
  extractions: AttachmentExtraction[];
};

export type AlertPreference = {
  id: number;
  tenant_id: string;
  email_to: string | null;
  min_fit_score: number;
  due_within_days: number;
  include_source_failures: boolean;
  enabled: boolean;
  created_at: string;
  updated_at: string;
};

export type AlertDigestOpportunity = {
  id: number;
  title: string;
  agency: string | null;
  state: string | null;
  location: string | null;
  due_date: string | null;
  source: string;
  source_type: string;
  source_url: string | null;
  estimated_value: MoneyValue;
  value_confidence: string;
  minimum_value_match: boolean;
  project_type: string;
  fit_score: number | null;
  fit_explanation: string | null;
};

export type AlertRun = {
  id: number;
  tenant_id: string;
  status: string;
  digest: {
    generated_at?: string;
    counts?: {
      high_fit?: number;
      due_soon?: number;
      watched?: number;
      source_failures?: number;
      saved_searches?: number;
      saved_search_matches?: number;
    };
    high_fit?: AlertDigestOpportunity[];
    due_soon?: AlertDigestOpportunity[];
    watched?: AlertDigestOpportunity[];
    saved_searches?: Array<{
      id: number;
      name: string;
      query: string | null;
      filters: Record<string, unknown>;
      matches: Array<{
        opportunity: AlertDigestOpportunity;
        rank_score: number;
        search_explanation: string;
      }>;
    }>;
    source_failures?: Array<Record<string, unknown>>;
  };
  error: string | null;
  sent_to: string | null;
  created_at: string;
  updated_at: string;
};

export type SavedSearch = {
  id: number;
  tenant_id: string;
  name: string;
  query: string | null;
  filters: Record<string, string>;
  enabled: boolean;
  email_digest: boolean;
  created_at: string;
  updated_at: string;
};

export type CompanyProfile = {
  id: number;
  tenant_id: string;
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
  source_url?: string;
  directory_only?: boolean;
  requires_setting?: string;
  portal_gated?: boolean;
  access_note?: string;
  status: "healthy" | "stale" | "failed" | "no_records" | "missing_config" | "needs_adapter" | string;
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

export type AuthUser = {
  id: number;
  email: string;
  role: "admin" | "user" | string;
  tenant_id: string;
  is_active: boolean;
};

export type LoginResponse = {
  token: string;
  user: AuthUser;
  expires_at: string;
};
