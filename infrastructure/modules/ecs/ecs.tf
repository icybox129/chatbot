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
    target_group_arn = var.alb_target_group_arn
    container_name   = "app"
    container_port   = 8080
  }

  network_configuration {
    security_groups  = var.ecs_container_instance
    subnets          = var.private_subnet_ids
    assign_public_ip = false
  }

}

###########################
# ECS SERVICE AUTOSCALING #
###########################

# Define Target Tracking on ECS Cluster Task level

resource "aws_appautoscaling_target" "ecs_target" {
  max_capacity       = 2
  min_capacity       = 1
  resource_id        = "service/${aws_ecs_cluster.cluster.name}/${aws_ecs_service.service.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

# Policy for CPU tracking

resource "aws_appautoscaling_policy" "ecs_cpu_policy" {
  name               = "${var.naming_prefix}-cpu-target-tracking"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ecs_target.resource_id
  scalable_dimension = aws_appautoscaling_target.ecs_target.scalable_dimension
  service_namespace  = aws_appautoscaling_target.ecs_target.service_namespace

  target_tracking_scaling_policy_configuration {
    target_value = 70

    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
  }
}

# Policy for Memory tracking

resource "aws_appautoscaling_policy" "ecs_memory_policy" {
  name               = "${var.naming_prefix}-memory-target-tracking"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ecs_target.resource_id
  scalable_dimension = aws_appautoscaling_target.ecs_target.scalable_dimension
  service_namespace  = aws_appautoscaling_target.ecs_target.service_namespace

  target_tracking_scaling_policy_configuration {
    target_value = 80

    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageMemoryUtilization"
    }
  }
}

#######################
# ECS TAsK DEFINITION #
#######################

resource "aws_ecs_task_definition" "task_definition" {
  family                   = "${var.naming_prefix}-ecs-task"
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 256
  memory                   = 512

  container_definitions = jsonencode([
    # Backend Container Definition
    {
      name      = "backend"
      image     = "${aws_ecr_repository.ecr.repository_url}:backend-latest"
      cpu       = 256
      memory    = 512
      essential = true
      portMappings = [
        {
          containerPort = 8080
          protocol      = "tcp"
        }
      ],
      secrets = [
        {
          name      = "OPENAI_API_KEY" # The environment variable name in the container
          valueFrom = aws_secretsmanager_secret.openai_api_key.arn
        }
      ],
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = "${var.log_group_name}"
          awslogs-region        = "eu-west-2"
          awslogs-stream-prefix = "${var.naming_prefix}-backend-log-stream"
        }
      }
    },
    # Frontend Container Definition
    {
      name      = "frontend"
      image     = "${aws_ecr_repository.ecr.repository_url}:frontend-latest"
      cpu       = 256
      memory    = 512
      essential = true
      portMappings = [
        {
          containerPort = 80
          protocol      = "tcp"
        }
      ],
      environment = [
        { name = "BACKEND_URL", value = "http://backend:8080" }
      ],
      dependsOn = [
        {
          containerName = "backend"
          condition     = "START"
        }
      ],
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = "${var.log_group_name}"
          awslogs-region        = "eu-west-2"
          awslogs-stream-prefix = "${var.naming_prefix}-frontend-log-stream"
        }
      }
    }
  ])
}
