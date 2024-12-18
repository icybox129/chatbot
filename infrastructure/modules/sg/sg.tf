###################
# SECURITY GROUPS #
###################

resource "aws_security_group" "sg" {
  name   = "${var.naming_prefix}-sg"
  vpc_id = var.vpc_id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["20.223.228.255/32"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["20.223.228.255/32"]
  }

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["20.223.228.255/32"]
  }

  ingress {
    from_port   = 5000
    to_port     = 5000
    protocol    = "tcp"
    cidr_blocks = ["20.223.228.255/32"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "ecs_container_instance" {
  name        = "${var.naming_prefix}-ecs-container-instance-sg"
  description = "Security group for ECS container instances"
  vpc_id      = var.vpc_id

  ingress {
    description     = "Allow ingress traffic from ALB on HTTP only"
    from_port       = 8080
    to_port         = 8080
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    description = "Allow all egress traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.naming_prefix}-ecs-container-instance-sg"
  }
}

resource "aws_security_group" "alb" {
  name        = "${var.naming_prefix}-alb-sg"
  description = "Security group for ALB"
  vpc_id      = var.vpc_id

  egress {
    description = "Allow all egress traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.naming_prefix}-alb-sg"
  }
}