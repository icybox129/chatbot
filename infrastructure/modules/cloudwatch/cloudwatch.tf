########################
# CLOUDWATCH LOG GROUP #
########################

# Create log group for our service

resource "aws_cloudwatch_log_group" "log_group" {
  name              = "/${lower(var.naming_prefix)}/ecs-task"
  retention_in_days = 7
}