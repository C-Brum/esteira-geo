variable "project" {
  type = string
}

variable "region" {
  type = string
}

variable "instance_type" {
  type    = string
  default = "t3.micro"
}

variable "db_instance_class" {
  type    = string
  default = "db.t3.micro"
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

variable "vpc_cidr" {
  type    = string
  default = "10.0.0.0/16"
}

variable "public_cidr" {
  type    = string
  default = "10.0.1.0/24"
}

variable "ssh_public_key_path" {
  type    = string
  default = "~/.ssh/id_rsa.pub"
}
