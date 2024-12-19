variable "environment" {
  type    = string
  default = "dev"
}

variable "project_name" {
  type    = string
  default = "chatbot"
}

variable "openai_api_key" {
  description = "The OpenAI API key to store in Secrets Manager"
  type        = string
}


variable "AWS_ACCESS_KEY" {}

variable "AWS_SECRET_KEY" {}