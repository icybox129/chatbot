output "ecs_container_instance" {
  value = aws_security_group.ecs_container_instance.id
}

output "alb_sg_id" {
  value = aws_security_group.alb.id
}