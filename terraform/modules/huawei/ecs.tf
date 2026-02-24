# Look up Ubuntu 20.04 LTS image on Huawei Cloud
data "huaweicloud_images_image" "ubuntu" {
  name        = "Ubuntu 20.04 server 64bit"
  most_recent = true
}

# KeyPair for SSH access
resource "huaweicloud_compute_keypair" "default" {
  name       = "${var.project}-key"
  public_key = var.ssh_public_key
}

# Processing VM
resource "huaweicloud_compute_instance" "processing" {
  name              = "${var.project}-processing"
  image_name        = data.huaweicloud_images_image.ubuntu.name
  flavor_name       = var.instance_flavor
  key_pair          = huaweicloud_compute_keypair.default.name
  security_groups   = [huaweicloud_networking_secgroup.processing_sg.name]
  availability_zone = data.huaweicloud_availability_zones.zones.names[0]

  network {
    uuid = huaweicloud_vpc_subnet.main.id
  }

  tags = {
    Name = "${var.project}-processing"
  }
}

# Presentation VM
resource "huaweicloud_compute_instance" "presentation" {
  name              = "${var.project}-presentation"
  image_name        = data.huaweicloud_images_image.ubuntu.name
  flavor_name       = var.instance_flavor
  key_pair          = huaweicloud_compute_keypair.default.name
  security_groups   = [huaweicloud_networking_secgroup.presentation_sg.name]
  availability_zone = data.huaweicloud_availability_zones.zones.names[0]

  network {
    uuid = huaweicloud_vpc_subnet.main.id
  }

  tags = {
    Name = "${var.project}-presentation"
  }
}

# Elastic IP for presentation VM (internet access)
resource "huaweicloud_compute_eip" "presentation" {
  publicip {
    type = "5_bgp"
  }
  bandwidth {
    name        = "${var.project}-eip"
    size        = 5
    share_type  = "PER"
    charge_mode = "traffic"
  }
}

resource "huaweicloud_compute_eip_associate" "presentation" {
  public_ip      = huaweicloud_compute_eip.presentation.address
  port_id        = huaweicloud_compute_instance.presentation.port[0].id
}
