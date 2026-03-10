terraform {
  required_version = ">= 1.5"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

locals {
  bucket_name = var.gcs_bucket_name != "" ? var.gcs_bucket_name : "${var.project_id}-overdue-staging"
}

# ----------------------------------------------------------------------
# BigQuery Dataset
# ----------------------------------------------------------------------

resource "google_bigquery_dataset" "overdue" {
  dataset_id    = var.dataset_id
  friendly_name = "Overdue - What the Internet Actually Reads"
  description   = "Book analytics: Reddit discussions, Open Library reading logs, ratings, and enriched book metadata."
  location      = var.region

  labels = {
    project = "overdue"
    env     = "dev"
  }
}

# ----------------------------------------------------------------------
# Table: reddit_book_mentions
# ----------------------------------------------------------------------

resource "google_bigquery_table" "reddit_book_mentions" {
  dataset_id          = google_bigquery_dataset.overdue.dataset_id
  table_id            = "reddit_book_mentions"
  description         = "Book mentions extracted from Reddit posts and comments across book subreddits."
  deletion_protection = false

  schema = jsonencode([
    { name = "mention_id",     type = "STRING",    mode = "REQUIRED", description = "UUID for this mention event" },
    { name = "post_id",        type = "STRING",    mode = "REQUIRED", description = "Reddit post/comment ID" },
    { name = "subreddit",      type = "STRING",    mode = "REQUIRED" },
    { name = "book_title",     type = "STRING",    mode = "REQUIRED", description = "Extracted book title" },
    { name = "book_work_key",  type = "STRING",    mode = "NULLABLE", description = "Open Library work key (e.g. OL12345W)" },
    { name = "author_name",    type = "STRING",    mode = "NULLABLE" },
    { name = "score",          type = "INTEGER",   mode = "NULLABLE", description = "Reddit score (upvotes - downvotes)" },
    { name = "sentiment",      type = "STRING",    mode = "NULLABLE", description = "positive / negative / neutral" },
    { name = "body_snippet",   type = "STRING",    mode = "NULLABLE", description = "Truncated context around the mention" },
    { name = "created_at",     type = "TIMESTAMP", mode = "REQUIRED", description = "Original Reddit post timestamp" },
    { name = "processed_at",   type = "TIMESTAMP", mode = "REQUIRED", description = "When the stream processor handled this" },
  ])

  time_partitioning {
    type  = "MONTH"
    field = "created_at"
  }

  clustering = ["subreddit", "book_work_key"]
}

# ----------------------------------------------------------------------
# Table: ol_reading_logs
# ----------------------------------------------------------------------

resource "google_bigquery_table" "ol_reading_logs" {
  dataset_id          = google_bigquery_dataset.overdue.dataset_id
  table_id            = "ol_reading_logs"
  description         = "Open Library reading log events: want-to-read, currently-reading, already-read."
  deletion_protection = false

  schema = jsonencode([
    { name = "work_key",    type = "STRING",    mode = "REQUIRED", description = "Open Library work key" },
    { name = "edition_key", type = "STRING",    mode = "NULLABLE", description = "Open Library edition key" },
    { name = "shelf",       type = "STRING",    mode = "REQUIRED", description = "want-to-read / currently-reading / already-read" },
    { name = "logged_at",   type = "TIMESTAMP", mode = "REQUIRED", description = "When the user added to this shelf" },
  ])

  time_partitioning {
    type  = "MONTH"
    field = "logged_at"
  }

  clustering = ["shelf", "work_key"]
}

# ----------------------------------------------------------------------
# Table: ol_ratings
# ----------------------------------------------------------------------

resource "google_bigquery_table" "ol_ratings" {
  dataset_id          = google_bigquery_dataset.overdue.dataset_id
  table_id            = "ol_ratings"
  description         = "Open Library user ratings (1-5 stars)."
  deletion_protection = false

  schema = jsonencode([
    { name = "work_key",    type = "STRING",    mode = "REQUIRED", description = "Open Library work key" },
    { name = "edition_key", type = "STRING",    mode = "NULLABLE", description = "Open Library edition key" },
    { name = "rating",      type = "INTEGER",   mode = "REQUIRED", description = "1-5 star rating" },
    { name = "rated_at",    type = "TIMESTAMP", mode = "REQUIRED", description = "When the rating was submitted" },
  ])

  time_partitioning {
    type  = "MONTH"
    field = "rated_at"
  }

  clustering = ["work_key"]
}

# ----------------------------------------------------------------------
# Table: books (enriched dimension table)
# ----------------------------------------------------------------------

resource "google_bigquery_table" "books" {
  dataset_id          = google_bigquery_dataset.overdue.dataset_id
  table_id            = "books"
  description         = "Enriched book dimension table: metadata, genres, readability scores."
  deletion_protection = false

  schema = jsonencode([
    { name = "work_key",             type = "STRING",  mode = "REQUIRED", description = "Open Library work key (primary identifier)" },
    { name = "title",                type = "STRING",  mode = "REQUIRED" },
    { name = "author",               type = "STRING",  mode = "NULLABLE" },
    { name = "subjects",             type = "STRING",  mode = "REPEATED", description = "Subject/genre tags" },
    { name = "genre",                type = "STRING",  mode = "NULLABLE", description = "Primary genre classification" },
    { name = "publish_year",         type = "INTEGER", mode = "NULLABLE" },
    { name = "page_count",           type = "INTEGER", mode = "NULLABLE" },
    { name = "cover_url",            type = "STRING",  mode = "NULLABLE", description = "Open Library cover image URL" },
    { name = "isbn",                 type = "STRING",  mode = "NULLABLE" },
    { name = "gutenberg_id",         type = "INTEGER", mode = "NULLABLE", description = "Project Gutenberg ID if available" },
    { name = "flesch_kincaid_grade", type = "FLOAT",   mode = "NULLABLE", description = "Flesch-Kincaid grade level" },
    { name = "flesch_reading_ease",  type = "FLOAT",   mode = "NULLABLE", description = "Flesch reading ease score (0-100)" },
    { name = "updated_at",           type = "TIMESTAMP", mode = "REQUIRED", description = "Last enrichment timestamp" },
  ])

  clustering = ["genre", "work_key"]
}

# ----------------------------------------------------------------------
# GCS Bucket: staging area for raw data dumps
# ----------------------------------------------------------------------

resource "google_storage_bucket" "staging" {
  name          = local.bucket_name
  location      = var.region
  force_destroy = true
  storage_class = "STANDARD"

  uniform_bucket_level_access = true

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age = 30
    }
  }

  labels = {
    project = "overdue"
    env     = "dev"
  }
}

# ----------------------------------------------------------------------
# Service Account for pipeline workloads
# ----------------------------------------------------------------------

resource "google_service_account" "pipeline" {
  account_id   = "overdue-pipeline"
  display_name = "Overdue Pipeline Service Account"
  description  = "Used by producer, stream processor, and API to access BigQuery and GCS."
}

resource "google_project_iam_member" "pipeline_bq_editor" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.pipeline.email}"
}

resource "google_project_iam_member" "pipeline_bq_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.pipeline.email}"
}

resource "google_project_iam_member" "pipeline_gcs_admin" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.pipeline.email}"
}
