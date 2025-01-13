output "efs_sync_task_arn" {
    value = aws_ecs_task_definition.efs_sync_task.arn
}

output "cluster_arn" {
    value = aws_ecs_cluster.cluster.arn
}