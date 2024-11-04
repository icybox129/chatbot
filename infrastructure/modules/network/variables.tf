variable "naming_prefix" {
  type = string
}

variable "vpc_cidr_block" {
  type        = string
  description = "Base CIDR Block for the VPC"
  default     = "10.0.0.0/16"
}