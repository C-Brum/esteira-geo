# Root-level outputs that read from whichever cloud module is enabled
output "project" {
  value = var.project
}

output "cloud" {
  value = var.cloud
}

output "s3_or_obs_buckets" {
  value = try(module.aws[0].s3_buckets, try(module.huawei[0].obs_buckets, []))
}

output "processing_public_ip" {
  value = try(module.aws[0].processing_public_ip, try(module.huawei[0].processing_instance_id, ""))
}

output "presentation_public_ip" {
  value = try(module.aws[0].presentation_public_ip, try(module.huawei[0].presentation_eip, ""))
}

output "rds_endpoint" {
  value = try(module.aws[0].rds_endpoint, try(module.huawei[0].rds_endpoint, ""))
}
