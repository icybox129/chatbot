######################
# CONTAINER REGISTRY #
######################

resource "aws_ecr_repository" "ecr" {
  name         = lower(var.naming_prefix)
  force_delete = true

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name = "${var.naming_prefix}-ecr"
  }

  # lifecycle {
  #   prevent_destroy = true
  # }
}