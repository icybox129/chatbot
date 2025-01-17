output "alb_target_group_arn" {
  value = aws_alb_target_group.service_target_group.arn
}

output "alb_dns_name" {
  value = aws_alb.alb.dns_name
}

output "alb_name" {
  value = aws_alb.alb.name
}