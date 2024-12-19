######################
# CONTAINER REGISTRY #
######################

resource "aws_ecr_repository" "ecr" {
  name         = "${lower(var.naming_prefix)}-chatbot"
  force_delete = false

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name = "${var.naming_prefix}-ecr"
  }

  lifecycle {
    prevent_destroy = true
  }
}