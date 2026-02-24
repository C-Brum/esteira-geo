# RDS PostgreSQL for Huawei Cloud
resource "huaweicloud_rds_instance" "postgres" {
  name                = "${var.project}-postgres"
  db_engine           = "postgres"
  db_engine_version   = "13"
  instance_class      = var.db_instance_class
  volume_type         = "COMMON"
  volume_size         = 20
  availability_zone   = [data.huaweicloud_availability_zones.zones.names[0]]
  vpc_id              = huaweicloud_vpc.main.id
  subnet_id           = huaweicloud_vpc_subnet.main.id
  security_group_id   = huaweicloud_networking_secgroup.db_sg.id
  db_user_name        = var.db_username
  db_password         = var.db_password
  publicly_accessible = true
  backup_strategy {
    backup_type = "automated"
    keep_days   = 7
  }

  tags = {
    Name = "${var.project}-postgres"
  }
}

# Note: To enable PostGIS extension, you can:
# 1. Connect to the DB after creation using psql
# 2. Run: CREATE EXTENSION postgis;
# Or use Terraform's null_resource with local-exec if you prefer scripting
