data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]
  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }
}

resource "aws_key_pair" "default" {
  key_name   = "${var.project}-key"
  public_key = file(var.ssh_public_key_path)
}

resource "aws_instance" "processing" {
  ami           = data.aws_ami.amazon_linux.id
  instance_type = var.instance_type
  subnet_id     = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.processing_sg.id]
  key_name      = aws_key_pair.default.key_name
  tags = { Name = "${var.project}-processing" }
}

resource "aws_instance" "presentation" {
  ami           = data.aws_ami.amazon_linux.id
  instance_type = var.instance_type
  subnet_id     = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.presentation_sg.id]
  key_name      = aws_key_pair.default.key_name
  associate_public_ip_address = true
  tags = { Name = "${var.project}-presentation" }
}

resource "aws_eip" "presentation_eip" {
  instance = aws_instance.presentation.id
  vpc      = true
}
