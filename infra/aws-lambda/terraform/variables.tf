variable "aws_region" {
  description = "AWS region for the low-idle backend."
  type        = string
  default     = "us-east-1"
}

variable "app_name" {
  description = "Name prefix for AWS resources."
  type        = string
  default     = "elecbidspec-ai"
}

variable "lambda_zip_path" {
  description = "Absolute path to the packaged backend Lambda zip."
  type        = string
}

variable "database_url" {
  description = "Postgres connection URL. For Lambda, use a pooled Neon URL when possible."
  type        = string
  sensitive   = true
}

variable "frontend_origin" {
  description = "Primary frontend origin allowed by CORS."
  type        = string
  default     = "https://elecbidspec-ai.pages.dev"
}

variable "cors_allowed_origins" {
  description = "Origins allowed by the Lambda Function URL CORS layer."
  type        = list(string)
  default = [
    "https://elecbidspec-ai.pages.dev",
    "http://localhost:3000",
    "http://127.0.0.1:3000"
  ]
}

variable "bootstrap_database_on_startup" {
  description = "Run Alembic migrations and seed data on API Lambda cold start."
  type        = bool
  default     = true
}

variable "run_migrations_on_startup" {
  description = "Run Alembic migrations when bootstrap_database_on_startup is true."
  type        = bool
  default     = true
}

variable "seed_database_on_startup" {
  description = "Seed sample opportunities and Taihan profile when bootstrap_database_on_startup is true."
  type        = bool
  default     = true
}

variable "worker_schedule_expression" {
  description = "EventBridge schedule for queued ingestion jobs."
  type        = string
  default     = "rate(15 minutes)"
}

variable "worker_max_jobs_per_run" {
  description = "Maximum queued ingestion jobs processed per scheduled worker invocation."
  type        = number
  default     = 10
}

variable "upload_prefix" {
  description = "S3 key prefix for uploaded RFP/spec files."
  type        = string
  default     = "uploads"
}

variable "api_memory_size" {
  description = "API Lambda memory in MB."
  type        = number
  default     = 1024
}

variable "worker_memory_size" {
  description = "Worker Lambda memory in MB."
  type        = number
  default     = 1024
}

variable "api_timeout_seconds" {
  description = "API Lambda timeout in seconds."
  type        = number
  default     = 30
}

variable "worker_timeout_seconds" {
  description = "Worker Lambda timeout in seconds."
  type        = number
  default     = 300
}

variable "bedrock_proposals_enabled" {
  description = "Enable Bedrock-backed proposal drafting. Deterministic fallback remains in code."
  type        = bool
  default     = false
}

variable "bedrock_model_id" {
  description = "Bedrock model for proposal drafting. Default favors low pilot cost."
  type        = string
  default     = "anthropic.claude-3-haiku-20240307-v1:0"
}

variable "bedrock_max_tokens" {
  description = "Maximum output tokens for Bedrock proposal generation."
  type        = number
  default     = 2500
}

variable "bedrock_temperature" {
  description = "Bedrock proposal generation temperature."
  type        = number
  default     = 0.2
}

variable "sam_gov_api_key" {
  description = "Optional SAM.gov API key."
  type        = string
  default     = ""
  sensitive   = true
}

variable "sam_gov_api_key_secret_arn" {
  description = "Optional AWS Secrets Manager ARN containing SAM_GOV_API_KEY or SAM_API_KEY. Preferred for deployed Lambda."
  type        = string
  default     = ""
}

variable "admin_api_token" {
  description = "Bearer token required for admin ingestion refresh and job endpoints."
  type        = string
  default     = ""
  sensitive   = true
}

variable "auth_required" {
  description = "Require login for tenant-specific app endpoints."
  type        = bool
  default     = false
}

variable "auth_session_ttl_hours" {
  description = "Login session lifetime in hours."
  type        = number
  default     = 168
}

variable "auth_admin_email" {
  description = "Optional seeded admin email."
  type        = string
  default     = ""
}

variable "auth_admin_password" {
  description = "Optional seeded admin password."
  type        = string
  default     = ""
  sensitive   = true
}

variable "auth_user_email" {
  description = "Optional seeded standard user email."
  type        = string
  default     = ""
}

variable "auth_user_password" {
  description = "Optional seeded standard user password."
  type        = string
  default     = ""
  sensitive   = true
}

variable "nypa_api_subscription_key" {
  description = "Optional NYPA public RFQ API subscription key."
  type        = string
  default     = ""
  sensitive   = true
}

variable "smtp_host" {
  description = "Optional SMTP host for daily alert email delivery."
  type        = string
  default     = ""
}

variable "smtp_port" {
  description = "SMTP port for daily alert email delivery."
  type        = number
  default     = 587
}

variable "smtp_username" {
  description = "Optional SMTP username."
  type        = string
  default     = ""
  sensitive   = true
}

variable "smtp_password" {
  description = "Optional SMTP password."
  type        = string
  default     = ""
  sensitive   = true
}

variable "smtp_use_tls" {
  description = "Use STARTTLS for SMTP alert delivery."
  type        = bool
  default     = true
}

variable "alert_email_from" {
  description = "From address for daily alert email delivery."
  type        = string
  default     = ""
}

variable "alert_send_cooldown_hours" {
  description = "Minimum hours between scheduled alert sends for a tenant."
  type        = number
  default     = 20
}

variable "artifact_expiration_days" {
  description = "Days to retain uploaded Lambda deployment zips."
  type        = number
  default     = 30
}

variable "force_destroy_artifact_bucket" {
  description = "Allow Terraform destroy to delete packaged Lambda artifacts."
  type        = bool
  default     = true
}

variable "force_destroy_upload_bucket" {
  description = "Allow Terraform destroy to delete user-uploaded RFP/spec files."
  type        = bool
  default     = false
}

variable "tags" {
  description = "Tags applied to AWS resources."
  type        = map(string)
  default = {
    App         = "ElecBidSpec AI"
    Environment = "pilot"
    ManagedBy   = "terraform"
  }
}
