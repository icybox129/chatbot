variable "naming_prefix" {
  type = string
}

variable "private_subnet_ids" {
    type = set(string)
}

variable "cluster_arn" {
  type = string
}

variable "efs_sync_task_arn" {
  type = string
}

variable "ecs_container_instance" {
  type = list(string)
}