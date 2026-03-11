output "dataset_id" {
  description = "BigQuery dataset ID"
  value       = google_bigquery_dataset.overdue.dataset_id
}

output "tables" {
  description = "BigQuery table IDs"
  value = {
    books      = google_bigquery_table.books.table_id
    book_arcs  = google_bigquery_table.book_arcs.table_id
    characters = google_bigquery_table.characters.table_id
  }
}
