# RDS PostgreSQL instance
resource "aws_db_subnet_group" "default" {
  name       = "${var.project}-db-subnet-group"
  subnet_ids = [aws_subnet.public.id]
  tags = { Name = "${var.project}-db-subnet-group" }
}

resource "aws_db_instance" "postgres" {
  identifier             = "${var.project}-postgres"
  engine                 = "postgres"
  engine_version         = "13"
  instance_class         = var.db_instance_class
  db_name                = var.db_name
  username               = var.db_username
  password               = var.db_password
  allocated_storage      = 20
  publicly_accessible    = false
  skip_final_snapshot    = true
  vpc_security_group_ids = [aws_security_group.db_sg.id]
  db_subnet_group_name   = aws_db_subnet_group.default.name
  tags = { Name = "${var.project}-postgres" }
}

# O RDS é compartilhado entre o pipeline e o Airflow (metadata DB).
# Após o deploy, habilite PostGIS:
#   psql -h <rds_endpoint> -U esteira_user -d esteira_geo
#   CREATE EXTENSION IF NOT EXISTS postgis;
