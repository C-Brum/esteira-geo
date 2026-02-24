# Three OBS buckets: bronze, silver, gold (Huawei equivalent of S3)
resource "huaweicloud_obs_bucket" "bronze" {
  bucket = "${var.project}-bronze-${random_id.bucket_suffix.hex}"
  acl    = "private"
}

resource "huaweicloud_obs_bucket" "silver" {
  bucket = "${var.project}-silver-${random_id.bucket_suffix.hex}"
  acl    = "private"
}

resource "huaweicloud_obs_bucket" "gold" {
  bucket = "${var.project}-gold-${random_id.bucket_suffix.hex}"
  acl    = "private"
}

resource "random_id" "bucket_suffix" {
  byte_length = 4
}
