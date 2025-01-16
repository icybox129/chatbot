variable "naming_prefix" {
  type = string
}

variable "private_subnet_ids" {
  type = list(string)
}

variable "efs_sg" {
  type = string
}