output "openai_api_key_arn" {
  value = aws_secretsmanager_secret.openai_api_key.arn
}