########################
# CLOUDWATCH LOG GROUP #
########################

resource "aws_cloudwatch_log_group" "log_group" {
  name              = "/${lower(var.naming_prefix)}/ecs-task"
  retention_in_days = 7
}

resource "aws_cloudwatch_event_rule" "efs_sync_schedule" {
  name                = "${var.naming_prefix}-efs-sync-schedule"
  schedule_expression = "rate(12 hours)"
}

resource "aws_cloudwatch_event_target" "efs_sync_schedule_target" {
  rule     = aws_cloudwatch_event_rule.efs_sync_schedule.name
  arn      = var.cluster_arn
  role_arn = aws_iam_role.eventbridge_invoke_ecs.arn

  ecs_target {
    launch_type         = "FARGATE"
    platform_version    = "1.4.0"
    task_definition_arn = var.efs_sync_task_arn
    network_configuration {
      subnets         = var.private_subnet_ids
      security_groups = var.ecs_container_instance
    }
  }
}

resource "aws_iam_role" "eventbridge_invoke_ecs" {
  name = "${var.naming_prefix}-eventbridge-ecs-invoke"

  assume_role_policy = data.aws_iam_policy_document.eventbridge_invoke_ecs_assume.json
}

data "aws_iam_policy_document" "eventbridge_invoke_ecs_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["events.amazonaws.com"]
    }
  }
}

resource "aws_iam_role_policy_attachment" "eventbridge_invoke_ecs_policy" {
  role       = aws_iam_role.eventbridge_invoke_ecs.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceEventsRole"
}