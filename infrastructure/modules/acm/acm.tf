terraform {
  required_providers {
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 3.0"
    }
  }
}

resource "aws_acm_certificate" "chatbot_cert" {
  domain_name       = var.domain_name
  validation_method = "DNS"

  subject_alternative_names = var.additional_domains

  tags = {
    Name = "${var.naming_prefix}-acm-cert"
  }
}

resource "cloudflare_record" "cert_validation" {
  for_each = {
    for d in aws_acm_certificate.chatbot_cert.domain_validation_options :
    d.resource_record_name => d
  }

  zone_id = var.cloudflare_zone_id
  name    = each.value.resource_record_name
  type    = each.value.resource_record_type
  value   = each.value.resource_record_value
  ttl     = 120
}

resource "aws_acm_certificate_validation" "cert_validation" {
  certificate_arn         = aws_acm_certificate.chatbot_cert.arn
  validation_record_fqdns = [for record in cloudflare_record.cert_validation : record.hostname]
}

resource "cloudflare_record" "root_domain" {
  zone_id = var.cloudflare_zone_id
  name    = "@"
  type    = "CNAME"
  value   = var.alb_dns_name
  proxied = true

  depends_on = [aws_acm_certificate_validation.cert_validation]
}

resource "cloudflare_record" "www_domain" {
  zone_id = var.cloudflare_zone_id
  name    = "www"
  type    = "CNAME"
  value   = "icybox.co.uk"
  proxied = true

  depends_on = [aws_acm_certificate_validation.cert_validation]
}

