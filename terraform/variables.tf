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

variable "gcs_bucket_name" {
  description = "GCS bucket for staging raw data dumps"
  type        = string
  default     = ""
}
