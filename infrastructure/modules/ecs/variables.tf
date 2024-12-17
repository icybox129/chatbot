variable "naming_prefix" {
  type = string
}

variable "ecs_container_instance" {
  type = list(string)
}

variable "private_subnet_ids" {
  type = set(string)
}