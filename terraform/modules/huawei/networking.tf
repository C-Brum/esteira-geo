# VPC and subnet for Huawei Cloud
resource "huaweicloud_vpc" "main" {
  name       = "${var.project}-vpc"
  cidr_block = var.vpc_cidr
}

resource "huaweicloud_vpc_subnet" "main" {
  name              = "${var.project}-subnet"
  vpc_id            = huaweicloud_vpc.main.id
  cidr_block        = var.subnet_cidr
  gateway_ip        = cidrhost(var.subnet_cidr, 1)
  primary_dns       = "8.8.8.8"
  secondary_dns     = "8.8.4.4"
  availability_zone = data.huaweicloud_availability_zones.zones.names[0]
}

data "huaweicloud_availability_zones" "zones" {
  state = "available"
}

# Security group for processing VM
resource "huaweicloud_networking_secgroup" "processing_sg" {
  name = "${var.project}-processing-sg"
}

resource "huaweicloud_networking_secgroup_rule" "processing_ssh" {
  security_group_id = huaweicloud_networking_secgroup.processing_sg.id
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "tcp"
  port_range_min    = 22
  port_range_max    = 22
  remote_ip_prefix  = "0.0.0.0/0"
}

resource "huaweicloud_networking_secgroup_rule" "processing_egress" {
  security_group_id = huaweicloud_networking_secgroup.processing_sg.id
  direction         = "egress"
  ethertype         = "IPv4"
  protocol          = "-1"
  remote_ip_prefix  = "0.0.0.0/0"
}

# Security group for presentation VM
resource "huaweicloud_networking_secgroup" "presentation_sg" {
  name = "${var.project}-presentation-sg"
}

resource "huaweicloud_networking_secgroup_rule" "presentation_http" {
  security_group_id = huaweicloud_networking_secgroup.presentation_sg.id
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "tcp"
  port_range_min    = 80
  port_range_max    = 80
  remote_ip_prefix  = "0.0.0.0/0"
}

resource "huaweicloud_networking_secgroup_rule" "presentation_https" {
  security_group_id = huaweicloud_networking_secgroup.presentation_sg.id
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "tcp"
  port_range_min    = 443
  port_range_max    = 443
  remote_ip_prefix  = "0.0.0.0/0"
}

resource "huaweicloud_networking_secgroup_rule" "presentation_ssh" {
  security_group_id = huaweicloud_networking_secgroup.presentation_sg.id
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "tcp"
  port_range_min    = 22
  port_range_max    = 22
  remote_ip_prefix  = "0.0.0.0/0"
}

resource "huaweicloud_networking_secgroup_rule" "presentation_egress" {
  security_group_id = huaweicloud_networking_secgroup.presentation_sg.id
  direction         = "egress"
  ethertype         = "IPv4"
  protocol          = "-1"
  remote_ip_prefix  = "0.0.0.0/0"
}

# Security group for RDS
resource "huaweicloud_networking_secgroup" "db_sg" {
  name = "${var.project}-db-sg"
}

resource "huaweicloud_networking_secgroup_rule" "db_ingress" {
  security_group_id = huaweicloud_networking_secgroup.db_sg.id
  direction         = "ingress"
  ethertype         = "IPv4"
  protocol          = "tcp"
  port_range_min    = 5432
  port_range_max    = 5432
  remote_ip_prefix  = var.subnet_cidr
}

resource "huaweicloud_networking_secgroup_rule" "db_egress" {
  security_group_id = huaweicloud_networking_secgroup.db_sg.id
  direction         = "egress"
  ethertype         = "IPv4"
  protocol          = "-1"
  remote_ip_prefix  = "0.0.0.0/0"
}
