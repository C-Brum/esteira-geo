output "s3_buckets" {
  value = [
    aws_s3_bucket.bronze.bucket,
    aws_s3_bucket.silver.bucket,
    aws_s3_bucket.gold.bucket,
  ]
}

output "processing_public_ip" {
  value = aws_instance.processing.public_ip
}

output "presentation_public_ip" {
  value = aws_eip.presentation_eip.public_ip
}

output "rds_endpoint" {
  value = aws_db_instance.postgres.address
}
