# RDS PostgreSQL for Huawei Cloud
resource "huaweicloud_rds_instance" "postgres" {
  name              = "${var.project}-postgres"
  flavor            = var.db_instance_class
  availability_zone = [data.huaweicloud_availability_zones.zones.names[0]]
  vpc_id            = huaweicloud_vpc.main.id
  subnet_id         = huaweicloud_vpc_subnet.main.id
  security_group_id = huaweicloud_networking_secgroup.db_sg.id

  db {
    type     = "PostgreSQL"
    version  = "13"
    password = var.db_password
  }

  volume {
    type = "CLOUDSSD"
    size = 40
  }

  backup_strategy {
    start_time = "02:00-03:00"
    keep_days  = 7
  }

  tags = { Name = "${var.project}-postgres" }
}

# O RDS é compartilhado entre o pipeline e o Airflow (metadata DB).
# Após o deploy, habilite PostGIS e crie o usuário:
#   psql -h <rds_endpoint> -U root -d postgres
#   CREATE USER esteira_user WITH PASSWORD 'esteira_pass';
#   CREATE DATABASE esteira_geo OWNER esteira_user;
#   \c esteira_geo
#   CREATE EXTENSION IF NOT EXISTS postgis;
