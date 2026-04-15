variable "project" {
  type = string
}

variable "region" {
  type    = string
  default = "sa-brazil-1"
}

variable "vpc_cidr" {
  type    = string
  default = "10.0.0.0/16"
}

variable "subnet_cidr" {
  type    = string
  default = "10.0.1.0/24"
}

variable "instance_flavor" {
  type    = string
  default = "s3.medium.2"
}

variable "db_instance_class" {
  type    = string
  default = "db.xlarge.2"
}

variable "db_username" {
  type    = string
  default = "esteira_user"
}

variable "db_password" {
  type      = string
  default   = "esteira_pass"
  sensitive = true
}

variable "db_name" {
  type    = string
  default = "esteira_geo"
}

variable "ssh_public_key" {
  type    = string
  default = ""
}
