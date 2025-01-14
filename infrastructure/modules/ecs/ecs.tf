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
  assume_role_policy = data.aws_iam_policy_document.task_assume_role_policy.json
}

data "aws_iam_policy_document" "task_assume_role_policy" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

# Attach AmazonECSTaskExecutionRolePolicy
resource "aws_iam_role_policy_attachment" "ecs_task_execution_role_policy" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Attach the AmazonSSMManagedInstanceCore policy to the ECS Task Execution Role
resource "aws_iam_role_policy_attachment" "ecs_task_execution_role_ssm" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# Custom policy for accessing Secrets Manager
resource "aws_iam_policy" "ecs_secrets_access" {
  name        = "${var.naming_prefix}-ecs-secrets-access"
  description = "Allows ECS task to access Secrets Manager"

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Action   = "secretsmanager:GetSecretValue",
        Resource = var.openai_api_key_arn
      }
    ]
  })
}

# Attach custom policy to ECS Task Execution Role
resource "aws_iam_role_policy_attachment" "ecs_task_execution_role_secrets_policy" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = aws_iam_policy.ecs_secrets_access.arn
}

# Task Role for container permissions
resource "aws_iam_role" "ecs_task_role" {
  name = "${var.naming_prefix}-ecs-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
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
  enable_execute_command             = true

  load_balancer {
    target_group_arn = var.alb_target_group_arn
    container_name   = "frontend"
    container_port   = 80
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
# ECS TASK DEFINITION #
#######################

resource "aws_ecs_task_definition" "task_definition" {
  family                   = "${var.naming_prefix}-ecs-task"
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 512
  memory                   = 1024

    volume {
    name = "chroma-efs-volume"
    efs_volume_configuration {
      file_system_id = var.chroma_efs_id
      root_directory = "/"
      transit_encryption = "ENABLED"
    }
  }

  container_definitions = jsonencode([
    # Backend Container Definition
    {
      name      = "backend"
      image     = "${var.ecr_repository_url}:backend-latest"
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
          valueFrom = var.openai_api_key_arn
        }
      ],
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = "${var.log_group_name}"
          awslogs-region        = "eu-west-2"
          awslogs-stream-prefix = "${var.naming_prefix}-backend-log-stream"
        }
      },
      "mountPoints": [
        {
          "sourceVolume"  : "chroma-efs-volume",
          "containerPath" : "/app/data/chroma"
        }
      ]
    },
    # Frontend Container Definition
    {
      name      = "frontend"
      image     = "${var.ecr_repository_url}:frontend-latest"
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
        { name = "BACKEND_URL", value = "http://127.0.0.1:8080" }
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

resource "aws_iam_role_policy" "efs_sync_s3_policy" {
  name   = "${var.naming_prefix}-efs-sync-s3-policy"
  role   = aws_iam_role.ecs_task_role.name
  policy = data.aws_iam_policy_document.efs_sync_s3_policy.json
}

data "aws_iam_policy_document" "efs_sync_s3_policy" {
  statement {
    actions = [
      "s3:GetObject",
      "s3:ListBucket"
    ]
    resources = [
      "arn:aws:s3:::nick-terraform-test-docs",
      "arn:aws:s3:::nick-terraform-test-docs/*"
    ]
  }
}

resource "aws_ecs_task_definition" "efs_sync_task" {
  family                   = "${var.naming_prefix}-efs-sync-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn
  
  volume {
    name = "chroma-efs-volume"
    efs_volume_configuration {
      file_system_id      = var.chroma_efs_id
      root_directory      = "/"
      transit_encryption  = "ENABLED"
    }
  }

  container_definitions = jsonencode([
    {
      "name": "efs-sync",
      "image": "amazon/aws-cli:latest",
      "essential": true,
      "entryPoint": ["sh", "-c"],
      "command": [
        "cd / && echo 'Syncing S3 to EFS...' && aws s3 sync s3://nick-terraform-test-docs/data/chroma /app/data/chroma && echo 'S3 -> EFS Sync completed.'"
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group":         "${var.log_group_name}",
          "awslogs-region":        "eu-west-2",
          "awslogs-stream-prefix": "${var.naming_prefix}-efs-sync"
        }
      },
      "mountPoints": [
        {
          "sourceVolume": "chroma-efs-volume",
          "containerPath": "/app/data/chroma"
        }
      ]
    }
  ])
}