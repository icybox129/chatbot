output "efs_sync_task_arn" {
    value = aws_ecs_task_definition.efs_sync_task.arn
}

output "cluster_arn" {
    value = aws_ecs_cluster.cluster.arn
}

output "backend_image_digest" {
  value = data.aws_ecr_image.backend.image_digest
}

output "frontend_image_digest" {
  value = data.aws_ecr_image.frontend.image_digest
}