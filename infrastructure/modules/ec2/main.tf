data "aws_ssm_parameter" "ubuntu_ami" {
  name = "/aws/service/canonical/ubuntu/server/22.04/stable/current/amd64/hvm/ebs-gp2/ami-id"
}

# resource "aws_launch_template" "ec2" {
#   name_prefix            = "${var.naming_prefix}-ec2"
#   image_id               = nonsensitive(data.aws_ssm_parameter.ubuntu_ami.value)
#   instance_type          = "t2.micro"
# #   user_data              = filebase64("${path.module}/user_data.sh")
#   vpc_security_group_ids = var.ec2_sg_id
# }

resource "aws_instance" "ec2" {
    ami               = nonsensitive(data.aws_ssm_parameter.ubuntu_ami.value)
    instance_type     = "t3.micro"
    key_name          = aws_key_pair.ec2_key_pair.key_name
    vpc_security_group_ids = var.ec2_sg_id
    subnet_id         = var.subnet_id

    tags = {
        Name = "${var.naming_prefix}-ec2"
    }
}

# Generate a new RSA key pair
resource "tls_private_key" "ec2_key_pair" {
  algorithm = "RSA"
  rsa_bits  = 2048
}
 
# Import the public key into AWS
resource "aws_key_pair" "ec2_key_pair" {
  key_name   = "${var.naming_prefix}-ec2-key"
  public_key = tls_private_key.ec2_key_pair.public_key_openssh
}

# Save the private key to a local file
resource "local_file" "private_key" {
  content        = tls_private_key.ec2_key_pair.private_key_pem
#   filename       = "${path.module}/${var.naming_prefix}-ec2-key"
  filename = "../../environment/dev/${var.naming_prefix}-ec2-key.pem"
  file_permission = "0400"
}