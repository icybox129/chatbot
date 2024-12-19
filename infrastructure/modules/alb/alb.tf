#############################
# APPLICATION LOAD BALANCER #
#############################

# ALB in public subnets

resource "aws_alb" "alb" {
  name            = "${var.naming_prefix}-alb"
  security_groups = [var.alb_sg_id]
  subnets         = var.public_subnet_ids
}

# HTTPS Listener that listens on port 443

resource "aws_alb_listener" "alb_https_listener" {
  load_balancer_arn = aws_alb.alb.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-2016-08"
  # certificate_arn = "test"

  default_action {
    type             = "forward"
    target_group_arn = aws_alb_target_group.service_target_group.arn
  }
}

# HTTP Listener that listens on port 80 and redirects to HTTPS

resource "aws_alb_listener" "alb_http_listener" {
  load_balancer_arn = aws_alb.alb.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type = "redirect"

    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

# Target group for ECS service

resource "aws_alb_target_group" "service_target_group" {
  name                 = "${var.naming_prefix}-alb-tg"
  port                 = 80
  protocol             = "HTTP"
  vpc_id               = var.vpc_id
  deregistration_delay = 5

  health_check {
    healthy_threshold   = 2
    unhealthy_threshold = 2
    interval            = 60
    matcher             = "200"
    path                = "/"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 30
  }

  depends_on = [aws_alb.alb]
}