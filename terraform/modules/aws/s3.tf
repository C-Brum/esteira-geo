# Create three buckets: bronze, silver, gold
resource "aws_s3_bucket" "bronze" {
  bucket = "${var.project}-bronze-${random_id.bucket_suffix.hex}"
  acl    = "private"
  force_destroy = true
}

resource "aws_s3_bucket" "silver" {
  bucket = "${var.project}-silver-${random_id.bucket_suffix.hex}"
  acl    = "private"
  force_destroy = true
}

resource "aws_s3_bucket" "gold" {
  bucket = "${var.project}-gold-${random_id.bucket_suffix.hex}"
  acl    = "private"
  force_destroy = true
}

resource "random_id" "bucket_suffix" {
  byte_length = 4
}
