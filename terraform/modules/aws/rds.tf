# RDS PostgreSQL instance
resource "aws_db_subnet_group" "default" {
  name       = "${var.project}-db-subnet-group"
  subnet_ids = [aws_subnet.public.id]
  tags = { Name = "${var.project}-db-subnet-group" }
}

resource "aws_db_instance" "postgres" {
  identifier = "${var.project}-postgres"
  engine = "postgres"
  engine_version = "13.7"
  instance_class = var.db_instance_class
  name = var.project
  username = var.db_username
  password = var.db_password
  allocated_storage = 20
  publicly_accessible = true
  skip_final_snapshot = true
  vpc_security_group_ids = [aws_security_group.db_sg.id]
  db_subnet_group_name = aws_db_subnet_group.default.name
  tags = { Name = "${var.project}-postgres" }
}

# PostGIS extension can be created after DB is available. We provide an example using the postgres provider
# The postgres provider requires network access during terraform apply. Uncomment and configure if you
# want Terraform to create the extension automatically.

# provider "postgresql" {
#   host     = aws_db_instance.postgres.address
#   port     = aws_db_instance.postgres.port
#   database = var.project
#   username = aws_db_instance.postgres.username
#   password = var.db_password
#   sslmode  = "require"
# }
#
#resource "postgresql_extension" "postgis" {
#  name = "postgis"
#}
