variable "environment" {
  type    = string
  default = "prod"
}

variable "aws_region" {
  type    = string
  default = "eu-west-2"
}

variable "project_name" {
  type    = string
  default = "chatbot"
}

variable "openai_api_key" {
  description = "The OpenAI API key to store in Secrets Manager"
  type        = string
}

variable "cloudflare_api_token" {
  description = "Cloudflare API token for authentication"
  type        = string
}
