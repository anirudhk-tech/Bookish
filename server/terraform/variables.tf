variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region for resources"
  type        = string
  default     = "US"
}

variable "dataset_id" {
  description = "BigQuery dataset ID"
  type        = string
  default     = "overdue"
}

variable "enable_billing_resources" {
  description = "Set to true to create GCS bucket + service account (requires billing). Set to false for BigQuery sandbox mode."
  type        = bool
  default     = false
}

variable "gcs_bucket_name" {
  description = "GCS bucket for staging raw data dumps (only used when enable_billing_resources = true)"
  type        = string
  default     = ""
}
