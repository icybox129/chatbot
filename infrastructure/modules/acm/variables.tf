variable "naming_prefix" {
  type = string
}

variable "domain_name" {
  type = string
}

variable "additional_domains" {
  type        = list(string)
  default     = []
}

variable "cloudflare_zone_id" {
  type = string
}

variable "cloudflare_api_token" {
  type = string
}