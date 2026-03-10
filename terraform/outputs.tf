output "dataset_id" {
  description = "BigQuery dataset ID"
  value       = google_bigquery_dataset.overdue.dataset_id
}

output "staging_bucket" {
  description = "GCS staging bucket name"
  value       = google_storage_bucket.staging.name
}

output "service_account_email" {
  description = "Pipeline service account email"
  value       = google_service_account.pipeline.email
}

output "tables" {
  description = "BigQuery table IDs"
  value = {
    reddit_book_mentions = google_bigquery_table.reddit_book_mentions.table_id
    ol_reading_logs      = google_bigquery_table.ol_reading_logs.table_id
    ol_ratings           = google_bigquery_table.ol_ratings.table_id
    books                = google_bigquery_table.books.table_id
  }
}
