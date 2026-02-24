output "obs_buckets" {
  value = [
    huaweicloud_obs_bucket.bronze.bucket,
    huaweicloud_obs_bucket.silver.bucket,
    huaweicloud_obs_bucket.gold.bucket,
  ]
}

output "processing_instance_id" {
  value = huaweicloud_compute_instance.processing.id
}

output "presentation_instance_id" {
  value = huaweicloud_compute_instance.presentation.id
}

output "presentation_eip" {
  value = huaweicloud_compute_eip.presentation.address
}

output "rds_endpoint" {
  value = huaweicloud_rds_instance.postgres.endpoints[0].address
}

output "rds_hostname" {
  value = huaweicloud_rds_instance.postgres.endpoints[0].address
}

output "rds_port" {
  value = 5432
}
