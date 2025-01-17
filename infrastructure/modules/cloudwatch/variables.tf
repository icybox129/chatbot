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

variable "aws_region" {
  type = string
}

variable "ecs_cluster_name" {
  type = string
}

variable "ecs_service_name" {
  type = string
}

variable "alb_name" {
  type = string
}