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
  count   = length(aws_acm_certificate.chatbot_cert.domain_validation_options)
  zone_id = var.cloudflare_zone_id

  name  = aws_acm_certificate.chatbot_cert.domain_validation_options[count.index].resource_record_name
  type  = aws_acm_certificate.chatbot_cert.domain_validation_options[count.index].resource_record_type
  value = aws_acm_certificate.chatbot_cert.domain_validation_options[count.index].resource_record_value
  ttl   = 120
}

resource "aws_acm_certificate_validation" "cert_validation" {
  certificate_arn         = aws_acm_certificate.chatbot_cert.arn
  validation_record_fqdns = cloudflare_record.cert_validation[*].hostname
}