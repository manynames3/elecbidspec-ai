data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

locals {
  lambda_zip_hash = filesha256(var.lambda_zip_path)

  common_environment = {
    ENVIRONMENT               = "production"
    DATABASE_URL              = var.database_url
    DATABASE_DISABLE_POOL     = "true"
    FRONTEND_ORIGIN           = var.frontend_origin
    UPLOAD_BUCKET             = aws_s3_bucket.uploads.bucket
    UPLOAD_PREFIX             = var.upload_prefix
    BEDROCK_MODEL_ID          = var.bedrock_model_id
    BEDROCK_REGION            = var.aws_region
    BEDROCK_MAX_TOKENS        = tostring(var.bedrock_max_tokens)
    BEDROCK_TEMPERATURE       = tostring(var.bedrock_temperature)
    SAM_GOV_API_KEY           = var.sam_gov_api_key
    ADMIN_API_TOKEN           = var.admin_api_token
    AUTH_REQUIRED             = tostring(var.auth_required)
    AUTH_SESSION_TTL_HOURS    = tostring(var.auth_session_ttl_hours)
    AUTH_ADMIN_EMAIL          = var.auth_admin_email
    AUTH_ADMIN_PASSWORD       = var.auth_admin_password
    AUTH_USER_EMAIL           = var.auth_user_email
    AUTH_USER_PASSWORD        = var.auth_user_password
    NYPA_API_SUBSCRIPTION_KEY = var.nypa_api_subscription_key
  }
}

resource "aws_s3_bucket" "artifacts" {
  bucket        = "${var.app_name}-lambda-artifacts-${data.aws_caller_identity.current.account_id}-${data.aws_region.current.region}"
  force_destroy = var.force_destroy_artifact_bucket
}

resource "aws_s3_bucket_public_access_block" "artifacts" {
  bucket                  = aws_s3_bucket.artifacts.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "artifacts" {
  bucket = aws_s3_bucket.artifacts.id

  rule {
    id     = "expire-old-lambda-artifacts"
    status = "Enabled"

    filter {
      prefix = "lambda/"
    }

    expiration {
      days = var.artifact_expiration_days
    }
  }
}

resource "aws_s3_object" "lambda_zip" {
  bucket      = aws_s3_bucket.artifacts.id
  key         = "lambda/${var.app_name}-backend-${local.lambda_zip_hash}.zip"
  source      = var.lambda_zip_path
  source_hash = local.lambda_zip_hash
}

resource "aws_s3_bucket" "uploads" {
  bucket        = "${var.app_name}-uploads-${data.aws_caller_identity.current.account_id}-${data.aws_region.current.region}"
  force_destroy = var.force_destroy_upload_bucket
}

resource "aws_s3_bucket_public_access_block" "uploads" {
  bucket                  = aws_s3_bucket.uploads.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "uploads" {
  bucket = aws_s3_bucket.uploads.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

data "aws_iam_policy_document" "lambda_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "backend" {
  name               = "${var.app_name}-lambda-role"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume_role.json
}

resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.backend.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

data "aws_iam_policy_document" "backend_access" {
  statement {
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject"
    ]
    resources = ["${aws_s3_bucket.uploads.arn}/*"]
  }

  statement {
    actions = [
      "bedrock:InvokeModel",
      "bedrock:InvokeModelWithResponseStream"
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "backend_access" {
  name   = "${var.app_name}-backend-access"
  role   = aws_iam_role.backend.id
  policy = data.aws_iam_policy_document.backend_access.json
}

resource "aws_lambda_function" "api" {
  function_name    = "${var.app_name}-api"
  role             = aws_iam_role.backend.arn
  runtime          = "python3.12"
  handler          = "app.lambda_handler.handler"
  s3_bucket        = aws_s3_bucket.artifacts.id
  s3_key           = aws_s3_object.lambda_zip.key
  source_code_hash = filebase64sha256(var.lambda_zip_path)
  memory_size      = var.api_memory_size
  timeout          = var.api_timeout_seconds
  architectures    = ["x86_64"]

  environment {
    variables = merge(local.common_environment, {
      BOOTSTRAP_DATABASE_ON_STARTUP = tostring(var.bootstrap_database_on_startup)
      RUN_MIGRATIONS_ON_STARTUP     = tostring(var.run_migrations_on_startup)
      SEED_DATABASE_ON_STARTUP      = tostring(var.seed_database_on_startup)
      BEDROCK_PROPOSALS_ENABLED     = tostring(var.bedrock_proposals_enabled)
    })
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_basic_execution,
    aws_iam_role_policy.backend_access
  ]
}

resource "aws_lambda_function_url" "api" {
  function_name      = aws_lambda_function.api.function_name
  authorization_type = "NONE"
}

resource "aws_lambda_permission" "api_function_url_public" {
  statement_id           = "AllowPublicFunctionUrlInvoke"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = aws_lambda_function.api.function_name
  principal              = "*"
  function_url_auth_type = "NONE"
}

resource "aws_lambda_function" "worker" {
  function_name    = "${var.app_name}-worker"
  role             = aws_iam_role.backend.arn
  runtime          = "python3.12"
  handler          = "app.worker_lambda.handler"
  s3_bucket        = aws_s3_bucket.artifacts.id
  s3_key           = aws_s3_object.lambda_zip.key
  source_code_hash = filebase64sha256(var.lambda_zip_path)
  memory_size      = var.worker_memory_size
  timeout          = var.worker_timeout_seconds
  architectures    = ["x86_64"]

  environment {
    variables = merge(local.common_environment, {
      BOOTSTRAP_DATABASE_ON_STARTUP = "false"
      BEDROCK_PROPOSALS_ENABLED     = tostring(var.bedrock_proposals_enabled)
      WORKER_MAX_JOBS_PER_RUN       = tostring(var.worker_max_jobs_per_run)
    })
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_basic_execution,
    aws_iam_role_policy.backend_access
  ]
}

resource "aws_cloudwatch_event_rule" "worker_schedule" {
  name                = "${var.app_name}-worker-schedule"
  schedule_expression = var.worker_schedule_expression
}

resource "aws_cloudwatch_event_target" "worker" {
  rule = aws_cloudwatch_event_rule.worker_schedule.name
  arn  = aws_lambda_function.worker.arn
}

resource "aws_lambda_permission" "worker_eventbridge" {
  statement_id  = "AllowEventBridgeWorkerInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.worker.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.worker_schedule.arn
}
