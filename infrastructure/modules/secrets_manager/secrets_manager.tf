###################
# SECRETS MANAGER #
###################

# Create the Secret
resource "aws_secretsmanager_secret" "openai_api_key" {
  name        = "${var.naming_prefix}-openai-api-key-test"
  description = "OpenAI API Key"

  # Set recovery window to 0 for immediate deletion when destroying
  recovery_window_in_days = 0
}

# Add a version to the Secret
resource "aws_secretsmanager_secret_version" "openai_api_key_version" {
  secret_id = aws_secretsmanager_secret.openai_api_key.id
  secret_string = var.openai_api_key
}