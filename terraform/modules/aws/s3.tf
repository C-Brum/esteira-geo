# Create three buckets: bronze, silver, gold
resource "aws_s3_bucket" "bronze" {
  bucket        = "${var.project}-bronze-${random_id.bucket_suffix.hex}"
  force_destroy = true
}

resource "aws_s3_bucket" "silver" {
  bucket        = "${var.project}-silver-${random_id.bucket_suffix.hex}"
  force_destroy = true
}

resource "aws_s3_bucket" "gold" {
  bucket        = "${var.project}-gold-${random_id.bucket_suffix.hex}"
  force_destroy = true
}

resource "aws_s3_bucket_ownership_controls" "bronze" {
  bucket = aws_s3_bucket.bronze.id
  rule { object_ownership = "BucketOwnerEnforced" }
}

resource "aws_s3_bucket_ownership_controls" "silver" {
  bucket = aws_s3_bucket.silver.id
  rule { object_ownership = "BucketOwnerEnforced" }
}

resource "aws_s3_bucket_ownership_controls" "gold" {
  bucket = aws_s3_bucket.gold.id
  rule { object_ownership = "BucketOwnerEnforced" }
}

resource "random_id" "bucket_suffix" {
  byte_length = 4
}
