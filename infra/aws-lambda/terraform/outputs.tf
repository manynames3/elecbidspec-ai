output "backend_base_url" {
  description = "Lambda Function URL base."
  value       = aws_lambda_function_url.api.function_url
}

output "api_base_url" {
  description = "Use this for NEXT_PUBLIC_API_URL in Cloudflare Pages."
  value       = "${aws_lambda_function_url.api.function_url}api"
}

output "upload_bucket_name" {
  description = "Private S3 bucket used for uploaded RFP/spec files."
  value       = aws_s3_bucket.uploads.bucket
}

output "artifact_bucket_name" {
  description = "Private S3 bucket used for Lambda deployment zips."
  value       = aws_s3_bucket.artifacts.bucket
}
