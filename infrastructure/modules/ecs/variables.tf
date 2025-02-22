variable "naming_prefix" {
  type = string
}

variable "ecs_container_instance" {
  type = list(string)
}

variable "private_subnet_ids" {
  type = set(string)
}

variable "log_group_name" {
  type = string
}

variable "alb_target_group_arn" {
  type = string
}

variable "openai_api_key_arn" {
  type = string
}

variable "ecr_repository_url" {
  type = string
}

variable "chroma_efs_id" {
  type = string
}