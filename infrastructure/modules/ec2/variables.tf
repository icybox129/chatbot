variable "naming_prefix" {
  type = string
}

variable "ec2_sg_id" {
  type = set(string)
}

variable "subnet_id" {
  type = string
}