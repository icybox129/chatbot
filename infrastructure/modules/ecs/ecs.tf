###############
# ECS CLUSTER #
###############

resource "aws_ecs_cluster" "cluster" {
  name = "${var.naming_prefix}-ecs-cluster"

  tags = {
    Name = "${var.naming_prefix}-ecs-cluster"
  }
}

###########
# ECS IAM #
###########

# IAM Role for ECS Task Execution

resource "aws_iam_role" "ecs_task_execution_role" {
  name               = "${var.naming_prefix}-ecs-task-execution-role"
  assume_role_policy = data.aws_iam_policy_document.task_assune_role_policy.json
}

data "aws_iam_policy_document" "task_assume_role_policy" {
  statement {
    actions = ["stst:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_role_policy" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"

}

# IAM Role for ECS Task

resource "aws_iam_role" "ecs_task_role" {
  name               = "${var.naming_prefix}-ecs-task-role"
  assume_role_policy = data.aws_iam_policy_document.task_assume_role_policy.json
}

###############
# ECS Service #
###############

resource "aws_ecs_service" "service" {
  name                               = "${var.naming_prefix}-ecs-service"
  cluster                            = aws_ecs_cluster.cluster.id
  task_definition                    = aws_ecs_task_definition.task_definition.arn
  desired_count                      = 1
  deployment_minimum_healthy_percent = 50
  deployment_maximum_percent         = 100
  launch_type                        = "FARGATE"

  load_balancer {
    target_group_arn = aws_alb_target_group.service_target_group.arn
    container_name   = "app"
    container_port   = 8080
  }

  network_configuration {
    security_groups  = [var.ecs_container_instance.id]
    subnets          = var.private_subnet_ids
    assign_public_ip = false
  }

}