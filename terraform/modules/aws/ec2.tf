# Ubuntu 22.04 LTS — compatível com Ansible (apt + python3.12 nativo)
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }
  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_key_pair" "default" {
  key_name   = "${var.project}-key"
  public_key = file(var.ssh_public_key_path)
}

resource "aws_instance" "processing" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = var.instance_type
  subnet_id     = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.processing_sg.id]
  key_name      = aws_key_pair.default.key_name
  tags = { Name = "${var.project}-processing" }
}

resource "aws_instance" "presentation" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = var.instance_type
  subnet_id     = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.presentation_sg.id]
  key_name      = aws_key_pair.default.key_name
  associate_public_ip_address = true
  tags = { Name = "${var.project}-presentation" }
}

resource "aws_eip" "presentation_eip" {
  instance = aws_instance.presentation.id
}
